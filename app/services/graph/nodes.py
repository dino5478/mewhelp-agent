"""图的各个节点。

每个节点拿到 state，返回要更新的字段（部分更新）。
"""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.services import intent, llm, retrieval
from app.services.graph.state import GraphState

_RAG_PROMPT = """你是电商平台的客服。请只根据下面提供的资料回答，资料里没有的就说\
"这个我需要帮你转人工确认"，不要自己编。

资料：
{context}

问题：{question}"""


def preprocess_node(state: GraphState) -> dict:
    """指代消解 + 意图识别，并把补全后的问题作为本轮对话起点。"""
    result = intent.analyze(state["query"], state.get("history"))
    return {
        "standalone_query": result["standalone_query"],
        "intent": result["intent"],
        "route": result["route"],
        "messages": [HumanMessage(content=result["standalone_query"])],
    }


def rag_node(state: GraphState) -> dict:
    """知识问答：先检索，再让模型基于资料回答。"""
    chunks = retrieval.hybrid_search(state["standalone_query"])
    if not chunks:
        return {"answer": "这个我需要帮你转人工确认。"}
    context = "\n\n".join(f"[{c.heading_path}] {c.text}" for c in chunks)
    answer = llm.chat([
        SystemMessage(content=_RAG_PROMPT.format(
            context=context, question=state["standalone_query"]
        ))
    ])
    return {"answer": answer, "context": context}


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
