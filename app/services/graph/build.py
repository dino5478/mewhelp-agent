"""把节点拼成状态图。

结构：
    START -> 前置处理 -> 分流
        faq        -> RAG 回答 -> 收尾
        其它       -> Agent <-> 工具 -> 收尾 -> END
"""

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.services import llm, tools
from app.services.graph.nodes import (
    finalize_node,
    make_agent_node,
    preprocess_node,
    rag_node,
)
from app.services.graph.state import GraphState


def _route_after_preprocess(state: GraphState) -> str:
    # 规则类问题走 RAG；订单/售后/闲聊都交给 Agent（要调工具）
    return "rag" if state.get("route") == "faq" else "agent"


def _agent_should_continue(state: GraphState) -> str:
    last = state["messages"][-1]
    return "tools" if getattr(last, "tool_calls", None) else "finalize"


def build_graph(user_id: int):
    tool_list = tools.build_tools(user_id)
    llm_with_tools = llm.get_llm().bind_tools(tool_list)

    builder = StateGraph(GraphState)
    builder.add_node("preprocess", preprocess_node)
    builder.add_node("rag", rag_node)
    builder.add_node("agent", make_agent_node(llm_with_tools))
    builder.add_node("tools", ToolNode(tool_list))
    builder.add_node("finalize", finalize_node)

    builder.add_edge(START, "preprocess")
    builder.add_conditional_edges(
        "preprocess", _route_after_preprocess, {"rag": "rag", "agent": "agent"}
    )
    builder.add_edge("rag", "finalize")
    builder.add_conditional_edges(
        "agent", _agent_should_continue, {"tools": "tools", "finalize": "finalize"}
    )
    builder.add_edge("tools", "agent")
    builder.add_edge("finalize", END)
    return builder.compile()
