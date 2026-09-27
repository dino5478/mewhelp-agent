"""图的各个节点。

每个节点拿到 state，返回要更新的字段（部分更新）。
"""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.core.config import settings
from app.services import confidence, handoff, intent, llm, retrieval
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
