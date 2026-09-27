"""把节点拼成状态图。

结构：
    START -> 前置处理 -> 分流
        faq  -> 检索 -> 置信度闸门 -> (生成 | 转人工) -> 收尾
        其它 -> Agent <-> 工具 -> 收尾
                                                  -> END
"""

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.services import llm, tools
from app.services.graph.nodes import (
    confidence_node,
    finalize_node,
    generate_node,
    handoff_node,
    make_agent_node,
    preprocess_node,
    retrieve_node,
)
from app.services.graph.state import GraphState


def _route_after_preprocess(state: GraphState) -> str:
    # 规则类问题走 RAG；订单/售后/闲聊都交给 Agent（要调工具）
    return "retrieve" if state.get("route") == "faq" else "agent"


def _route_after_confidence(state: GraphState) -> str:
    return "generate" if state.get("confident") else "handoff"


def _agent_should_continue(state: GraphState) -> str:
    last = state["messages"][-1]
    return "tools" if getattr(last, "tool_calls", None) else "finalize"


def build_graph(user_id: int):
    tool_list = tools.build_tools(user_id)
    llm_with_tools = llm.get_llm().bind_tools(tool_list)

    builder = StateGraph(GraphState)
    builder.add_node("preprocess", preprocess_node)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("confidence", confidence_node)
    builder.add_node("generate", generate_node)
    builder.add_node("handoff", handoff_node)
    builder.add_node("agent", make_agent_node(llm_with_tools))
    builder.add_node("tools", ToolNode(tool_list))
    builder.add_node("finalize", finalize_node)

    builder.add_edge(START, "preprocess")
    builder.add_conditional_edges(
        "preprocess", _route_after_preprocess, {"retrieve": "retrieve", "agent": "agent"}
    )
    builder.add_edge("retrieve", "confidence")
    builder.add_conditional_edges(
        "confidence", _route_after_confidence, {"generate": "generate", "handoff": "handoff"}
    )
    builder.add_edge("generate", "finalize")
    builder.add_edge("handoff", "finalize")
    builder.add_conditional_edges(
        "agent", _agent_should_continue, {"tools": "tools", "finalize": "finalize"}
    )
    builder.add_edge("tools", "agent")
    builder.add_edge("finalize", END)
    return builder.compile()
