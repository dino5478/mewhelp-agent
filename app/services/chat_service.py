"""聊天服务：会话管理 + 调用状态图并做 SSE 流式输出。

支持中断恢复：售后流程需要用户选订单时，图会暂停，前端选完再调 resume。
"""

import json
from collections.abc import AsyncGenerator

from langgraph.types import Command
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.database import SessionLocal
from app.models import ChatSession, Message
from app.services import context
from app.services.graph.build import build_graph
from app.services.graph.checkpoint import get_checkpointer

# 只有这两个节点的输出给用户看；retrieve/confidence 这些别透出去
STREAM_NODES = {"generate", "agent", "refund_answer"}


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


async def _pending_interrupt(graph, config) -> dict | None:
    """图是不是卡在某个 interrupt 上；是的话把中断载荷取出来。"""
    snapshot = await graph.aget_state(config)
    for task in snapshot.tasks:
        if getattr(task, "interrupts", None):
            return task.interrupts[0].value
    return None


async def _run(graph, config, graph_input) -> AsyncGenerator[tuple[str, dict], None]:
    """跑图并产出 (事件名, 数据)。token 事件逐个吐；最后给出 final_state。"""
    streamed = ""
    final_state: dict = {}
    async for mode, data in graph.astream(
        graph_input, config, stream_mode=["messages", "values"]
    ):
        if mode == "messages":
            chunk, meta = data
            if meta.get("langgraph_node") not in STREAM_NODES:
                continue
            text = chunk.content if isinstance(chunk.content, str) else ""
            if text:
                streamed += text
                yield ("token", {"text": text})
        else:
            final_state = data
    yield ("final", {"streamed": streamed, "state": final_state})


async def stream_reply(
    session_id: int, user_id: int, query: str, history: list[dict], summary: str = ""
) -> AsyncGenerator[str, None]:
    graph = build_graph(user_id, checkpointer=await get_checkpointer())
    config = {"configurable": {"thread_id": str(session_id)}}
    state = {
        "query": query,
        "user_id": user_id,
        "session_id": session_id,
        "history": history,
        "summary": summary,
    }

    try:
        async for event, payload in _run(graph, config, state):
            if event == "token":
                yield _sse("token", payload)
            else:
                streamed, final_state = payload["streamed"], payload["state"]
    except Exception as exc:  # noqa: BLE001
        yield _sse("error", {"message": f"处理失败：{exc}"})
        return

    pending = await _pending_interrupt(graph, config)
    if pending:
        # 暂停等用户选订单，先不落库回答
        yield _sse("need_order_selection", pending if isinstance(pending, dict) else {})
        yield _sse("done", {"session_id": session_id, "interrupted": True})
        return

    answer = final_state.get("answer") or streamed or "抱歉，我没能处理这个问题。"
    message_id = _save_assistant_message(session_id, answer)
    _summarize(session_id)
    if final_state.get("need_human"):
        yield _sse("handoff", {"reason": final_state.get("confidence_reason", "")})
    yield _sse("done", {"session_id": session_id, "message_id": message_id})


async def stream_resume(
    session_id: int, user_id: int, order_id: int
) -> AsyncGenerator[str, None]:
    """用户选完订单后，把选择喂回中断点继续跑。"""
    graph = build_graph(user_id, checkpointer=await get_checkpointer())
    config = {"configurable": {"thread_id": str(session_id)}}

    try:
        async for event, payload in _run(graph, config, Command(resume={"order_id": order_id})):
            if event == "token":
                yield _sse("token", payload)
            else:
                streamed, final_state = payload["streamed"], payload["state"]
    except Exception as exc:  # noqa: BLE001
        yield _sse("error", {"message": f"处理失败：{exc}"})
        return

    answer = final_state.get("answer") or streamed or "抱歉，我没能处理这个问题。"
    message_id = _save_assistant_message(session_id, answer)
    _summarize(session_id)
    yield _sse("done", {"session_id": session_id, "message_id": message_id})
