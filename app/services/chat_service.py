"""聊天服务：会话管理 + 调用状态图并做 SSE 流式输出。"""

import json
from collections.abc import AsyncGenerator

from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.database import SessionLocal
from app.models import ChatSession, Message
from app.services import context
from app.services.graph.build import build_graph

# 只有这两个节点的输出给用户看；retrieve/confidence 这些别透出去
STREAM_NODES = {"generate", "agent"}


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def get_or_create_session(db: Session, user_id: int, session_id: int | None) -> ChatSession:
    if session_id is None:
        session = ChatSession(user_id=user_id)
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    session = db.get(ChatSession, session_id)
    if session is None:
        raise NotFoundError("会话不存在")
    if session.user_id != user_id:
        raise ForbiddenError("无权访问该会话")
    return session


def append_message(db: Session, session_id: int, role: str, content: str) -> Message:
    msg = Message(session_id=session_id, role=role, content=content)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def _save_assistant_message(session_id: int, content: str) -> int:
    db = SessionLocal()
    try:
        msg = Message(session_id=session_id, role="assistant", content=content)
        db.add(msg)
        db.commit()
        db.refresh(msg)
        return msg.id
    finally:
        db.close()


def _summarize(session_id: int) -> None:
    db = SessionLocal()
    try:
        session = db.get(ChatSession, session_id)
        if session is not None:
            context.summarize_if_needed(db, session)
    finally:
        db.close()


async def stream_reply(
    session_id: int, user_id: int, query: str, history: list[dict], summary: str = ""
) -> AsyncGenerator[str, None]:
    """调用状态图，把模型 token 逐条以 SSE 推给前端，最后落库并 done。"""
    graph = build_graph(user_id)
    state = {
        "query": query,
        "user_id": user_id,
        "session_id": session_id,
        "history": history,
        "summary": summary,
    }

    streamed = ""
    final_state: dict = {}
    try:
        async for mode, data in graph.astream(state, stream_mode=["messages", "values"]):
            if mode == "messages":
                chunk, meta = data
                if meta.get("langgraph_node") not in STREAM_NODES:
                    continue
                text = chunk.content if isinstance(chunk.content, str) else ""
                if text:
                    streamed += text
                    yield _sse("token", {"text": text})
            else:
                final_state = data
    except Exception as exc:  # noqa: BLE001
        yield _sse("error", {"message": f"处理失败：{exc}"})
        return

    answer = final_state.get("answer") or streamed or "抱歉，我没能处理这个问题。"
    message_id = _save_assistant_message(session_id, answer)
    _summarize(session_id)
    if final_state.get("need_human"):
        yield _sse("handoff", {"reason": final_state.get("confidence_reason", "")})
    yield _sse("done", {"session_id": session_id, "message_id": message_id})
