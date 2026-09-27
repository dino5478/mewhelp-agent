"""聊天服务：会话管理 + 调用状态图并做 SSE 流式输出。"""

import json
from collections.abc import AsyncGenerator

from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.database import SessionLocal
from app.models import ChatSession, Message
from app.services.graph.build import build_graph


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


def load_history(db: Session, session_id: int, limit: int = 6) -> list[dict]:
    """取最近几轮对话，供指代消解用。"""
    rows = (
        db.query(Message)
        .filter(Message.session_id == session_id, Message.role.in_(["user", "assistant"]))
        .order_by(Message.id.desc())
        .limit(limit)
        .all()
    )
    return [{"role": m.role, "content": m.content} for m in reversed(rows)]


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


async def stream_reply(
    session_id: int, user_id: int, query: str, history: list[dict]
) -> AsyncGenerator[str, None]:
    """调用状态图，把模型 token 逐条以 SSE 推给前端，最后落库并 done。"""
    graph = build_graph(user_id)
    state = {"query": query, "user_id": user_id, "session_id": session_id, "history": history}

    streamed = ""
    final_state: dict = {}
    try:
        async for mode, data in graph.astream(state, stream_mode=["messages", "values"]):
            if mode == "messages":
                chunk, meta = data
                # 只放行真正给用户看的节点，别把意图识别的 JSON 也吐出去
                if meta.get("langgraph_node") not in {"rag", "agent"}:
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
    yield _sse("done", {"session_id": session_id, "message_id": message_id})
