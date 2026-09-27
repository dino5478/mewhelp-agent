"""图的各个节点。

每个节点拿到 state，返回要更新的字段（部分更新）。
"""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.types import interrupt

from app.core.config import settings
from app.core.exceptions import AppException
from app.database import SessionLocal
from app.services import confidence, handoff, intent, llm, order_service, retrieval
from app.services.graph.state import GraphState

_RAG_PROMPT = """你是电商平台的客服。请只根据下面提供的资料回答，资料里没有的就说\
"这个我需要帮你转人工确认"，不要自己编。

资料：
{context}

问题：{question}"""


def preprocess_node(state: GraphState) -> dict:
    """指代消解 + 意图识别，并把补全后的问题作为本轮对话起点。"""
    result = intent.analyze(state["query"], state.get("history"), state.get("summary", ""))
    return {
        "standalone_query": result["standalone_query"],
        "intent": result["intent"],
        "route": result["route"],
        "messages": [HumanMessage(content=result["standalone_query"])],
    }


def retrieve_node(state: GraphState) -> dict:
    """只负责检索，把资料和最高分放进 state，判证交给下一个节点。"""
    chunks = retrieval.hybrid_search(state["standalone_query"], top_k=settings.RAG_TOP_K)
    context = "\n\n".join(f"[{c.heading_path}] {c.text}" for c in chunks)
    retrieved = [
        {"id": c.id, "heading_path": c.heading_path, "text": c.text, "score": c.score}
        for c in chunks
    ]
    top_score = chunks[0].score if chunks else 0.0
    return {"context": context, "retrieved": retrieved, "top_score": top_score}


def confidence_node(state: GraphState) -> dict:
    confident, reason = confidence.judge(
        state["standalone_query"], state.get("context", ""), state.get("top_score", 0.0)
    )
    return {"confident": confident, "confidence_reason": reason}


def generate_node(state: GraphState) -> dict:
    """证据够了，基于资料生成回答。"""
    answer = llm.chat([
        SystemMessage(content=_RAG_PROMPT.format(
            context=state.get("context", ""), question=state["standalone_query"]
        ))
    ])
    return {"answer": answer}


def handoff_node(state: GraphState) -> dict:
    """证据不够，转人工：先落问题池（数据飞轮入口），再给用户话术。"""
    handoff.record_handoff(
        user_id=state.get("user_id"),
        session_id=state.get("session_id"),
        query=state["standalone_query"],
        intent=state.get("intent"),
        reason=state.get("confidence_reason", "low_confidence"),
        retrieved=state.get("retrieved"),
    )
    return {
        "answer": "这个问题我不太确定，已经帮你转人工客服，请稍等一下。",
        "need_human": True,
    }


_REFUND_PROMPT = """你是电商售后客服。结合订单信息和售后政策，告诉用户这笔订单能不能退、怎么退。

订单信息：{order}

售后政策：
{context}

用户问题：{question}"""


def order_check_node(state: GraphState) -> dict:
    """售后入口：确认要处理哪笔订单。

    名下多笔订单时暂停，让用户选；只有一笔就直接用；没有就直说。
    暂停靠 interrupt，配合 checkpointer 才能恢复。
    """
    db = SessionLocal()
    try:
        orders = order_service.list_orders(db, state["user_id"])
        options = [
            {"id": o.id, "title": f"订单 {o.id}（{o.status}，{o.total_amount} 元）"}
            for o in orders
        ]
    finally:
        db.close()

    if not options:
        return {"answer": "你名下暂时没有可申请售后的订单。"}
    if len(options) == 1:
        return {"order_id": options[0]["id"]}

    # 多笔订单：中断，等前端把用户选的那笔传回来
    selection = interrupt({"type": "select_order", "orders": options})
    return {"order_id": int(selection["order_id"])}


def refund_answer_node(state: GraphState) -> dict:
    """拿到订单后，结合订单信息和售后政策生成回答。"""
    db = SessionLocal()
    try:
        order = order_service.get_order(db, state["user_id"], state["order_id"])
        order_info = f"订单 {order.id}，状态 {order.status}，金额 {order.total_amount} 元"
    except AppException as exc:
        return {"answer": f"查订单时出错了：{exc.message}"}
    finally:
        db.close()

    chunks = retrieval.hybrid_search(state["standalone_query"])
    context = "\n\n".join(f"[{c.heading_path}] {c.text}" for c in chunks)
    answer = llm.chat([
        SystemMessage(content=_REFUND_PROMPT.format(
            order=order_info, context=context, question=state["standalone_query"]
        ))
    ])
    return {"answer": answer}


def make_agent_node(llm_with_tools):
    """工厂：把绑好工具的模型包成一个节点函数。"""

    def agent_node(state: GraphState) -> dict:
        return {"messages": [llm_with_tools.invoke(state["messages"])]}

    return agent_node


def finalize_node(state: GraphState) -> dict:
    """收尾：RAG 路径已有 answer；Agent 路径取最后一条 AI 消息。"""
    if state.get("answer"):
        return {}
    messages = state.get("messages", [])
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and not getattr(msg, "tool_calls", None):
            return {"answer": msg.content if isinstance(msg.content, str) else str(msg.content)}
    return {"answer": "抱歉，我没能处理这个问题。"}
