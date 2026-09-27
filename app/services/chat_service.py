"""聊天服务：会话管理 + SSE 事件流。

P1 只是骨架：用固定话术逐字输出，验证 SSE 管道。P3 会把这里替换成
LangGraph 编排 + 大模型生成。
"""

import asyncio
import json
from collections.abc import AsyncGenerator

from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.database import SessionLocal
from app.models import ChatSession, Message


def _sse(event: str, data: dict) -> str:
    """拼成一条 SSE 消息：event 行 + data 行 + 空行分隔。"""
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


async def stream_reply(session_id: int, message: str) -> AsyncGenerator[str, None]:
    """产出结构化 SSE 事件：逐个 token，最后 done。

    用独立的 SessionLocal 在生成器内部落库，避免请求级会话提前关闭。
    """
    reply = f"（P1 骨架回复）我收到了你的消息：{message}"

    # 逐字推送 token 事件
    for ch in reply:
        yield _sse("token", {"text": ch})
        await asyncio.sleep(0.03)

    # 落库助手回复，并把 message_id 一起返回
    db = SessionLocal()
    try:
        assistant_msg = Message(session_id=session_id, role="assistant", content=reply)
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)
        message_id = assistant_msg.id
    finally:
        db.close()

    yield _sse("done", {"session_id": session_id, "message_id": message_id})
