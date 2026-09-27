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
    order_check_node,
    preprocess_node,
    refund_answer_node,
    retrieve_node,
)
from app.services.graph.state import GraphState


def _route_after_preprocess(state: GraphState) -> str:
    route = state.get("route")
    if route == "faq":
        return "retrieve"      # 规则类问题查知识库
    if route == "aftersale":
        return "order_check"   # 售后要先确定订单
    return "agent"             # 订单/闲聊交给 Agent


def _route_after_order_check(state: GraphState) -> str:
    return "refund_answer" if state.get("order_id") else "finalize"


def _route_after_confidence(state: GraphState) -> str:
    return "generate" if state.get("confident") else "handoff"


def _agent_should_continue(state: GraphState) -> str:
    last = state["messages"][-1]
    return "tools" if getattr(last, "tool_calls", None) else "finalize"


def build_graph(user_id: int, checkpointer=None):
    tool_list = tools.build_tools(user_id)
    llm_with_tools = llm.get_llm().bind_tools(tool_list)

    builder = StateGraph(GraphState)
    builder.add_node("preprocess", preprocess_node)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("confidence", confidence_node)
    builder.add_node("generate", generate_node)
    builder.add_node("handoff", handoff_node)
    builder.add_node("order_check", order_check_node)
    builder.add_node("refund_answer", refund_answer_node)
    builder.add_node("agent", make_agent_node(llm_with_tools))
    builder.add_node("tools", ToolNode(tool_list))
    builder.add_node("finalize", finalize_node)

    builder.add_edge(START, "preprocess")
    builder.add_conditional_edges(
        "preprocess",
        _route_after_preprocess,
        {"retrieve": "retrieve", "order_check": "order_check", "agent": "agent"},
    )
    builder.add_edge("retrieve", "confidence")
    builder.add_conditional_edges(
        "confidence", _route_after_confidence, {"generate": "generate", "handoff": "handoff"}
    )
    builder.add_conditional_edges(
        "order_check",
        _route_after_order_check,
        {"refund_answer": "refund_answer", "finalize": "finalize"},
    )
    builder.add_edge("refund_answer", "finalize")
    builder.add_edge("generate", "finalize")
    builder.add_edge("handoff", "finalize")
    builder.add_conditional_edges(
        "agent", _agent_should_continue, {"tools": "tools", "finalize": "finalize"}
    )
    builder.add_edge("tools", "agent")
    builder.add_edge("finalize", END)
    return builder.compile(checkpointer=checkpointer)
