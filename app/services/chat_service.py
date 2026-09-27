"""聊天服务：会话管理 + 调用状态图并做 SSE 流式输出。

支持中断恢复：售后流程需要用户选订单时，图会暂停，前端选完再调 resume。
顺带把每个节点的耗时记进 audit_logs，形成可查的调用链。
"""

import json
import time
from collections.abc import AsyncGenerator

from langchain_core.messages import BaseMessage
from langgraph.types import Command
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.database import SessionLocal
from app.models import ChatSession, Message
from app.services import context, observability
from app.services.graph.build import build_graph
from app.services.graph.checkpoint import get_checkpointer

# 只有这几个节点的输出给用户看；retrieve/confidence 这些别透出去
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


async def _run(graph, config, graph_input, request_id: str, session_id: int):
    """跑图并产出 (事件名, 数据)。

    token 事件逐个吐；同时按节点记耗时（updates 模式）。
    """
    streamed = ""
    final_state: dict = {}
    last_ts = time.perf_counter()
    async for mode, data in graph.astream(
        graph_input, config, stream_mode=["messages", "values", "updates"]
    ):
        if mode == "messages":
            chunk, meta = data
            if meta.get("langgraph_node") not in STREAM_NODES:
                continue
            text = chunk.content if isinstance(chunk.content, str) else ""
            if text:
                streamed += text
                yield ("token", {"text": text})
        elif mode == "updates":
            # updates 事件是节点执行完才发的，用它给每个节点记一段耗时
            now = time.perf_counter()
            for node in data:
                if node == "__interrupt__":
                    continue
                observability.record_span(
                    request_id, session_id, node=node,
                    latency_ms=int((now - last_ts) * 1000),
                )
            last_ts = now
        else:
            final_state = data
    yield ("final", {"streamed": streamed, "state": final_state})


def _record_tool_spans(request_id: str, session_id: int, messages: list[BaseMessage]) -> None:
    for msg in messages:
        for call in getattr(msg, "tool_calls", None) or []:
            observability.record_span(request_id, session_id, tool=call.get("name"))


async def _drive(
    graph, config, graph_input, request_id: str, session_id: int
) -> AsyncGenerator[str, None]:
    """两种入口（新消息/恢复）共用的执行 + 落库 + 事件收尾。"""
    streamed = ""
    final_state: dict = {}
    try:
        async for event, payload in _run(graph, config, graph_input, request_id, session_id):
            if event == "token":
                yield _sse("token", payload)
            else:
                streamed, final_state = payload["streamed"], payload["state"]
    except Exception as exc:  # noqa: BLE001
        observability.record_span(request_id, session_id, error=str(exc))
        yield _sse("error", {"message": f"处理失败：{exc}"})
        return

    pending = await _pending_interrupt(graph, config)
    if pending:
        yield _sse("need_order_selection", pending if isinstance(pending, dict) else {})
        yield _sse("done", {
            "session_id": session_id, "interrupted": True, "request_id": request_id
        })
        return

    answer = final_state.get("answer") or streamed or "抱歉，我没能处理这个问题。"
    _record_tool_spans(request_id, session_id, final_state.get("messages", []))
    message_id = _save_assistant_message(session_id, answer)
    _summarize(session_id)
    if final_state.get("need_human"):
        yield _sse("handoff", {"reason": final_state.get("confidence_reason", "")})
    yield _sse("done", {
        "session_id": session_id, "message_id": message_id, "request_id": request_id
    })


def _build_config(session_id: int) -> dict:
    config: dict = {"configurable": {"thread_id": str(session_id)}}
    handler = observability.get_langfuse_handler()
    if handler is not None:
        config["callbacks"] = [handler]
    return config


async def stream_reply(
    session_id: int, user_id: int, query: str, history: list[dict], summary: str = ""
) -> AsyncGenerator[str, None]:
    request_id = observability.new_request_id()
    graph = build_graph(user_id, checkpointer=await get_checkpointer())
    state = {
        "query": query,
        "user_id": user_id,
        "session_id": session_id,
        "history": history,
        "summary": summary,
        "request_id": request_id,
    }
    async for chunk in _drive(graph, _build_config(session_id), state, request_id, session_id):
        yield chunk


async def stream_resume(
    session_id: int, user_id: int, order_id: int
) -> AsyncGenerator[str, None]:
    """用户选完订单后，把选择喂回中断点继续跑。"""
    request_id = observability.new_request_id()
    graph = build_graph(user_id, checkpointer=await get_checkpointer())
    command = Command(resume={"order_id": order_id})
    async for chunk in _drive(
        graph, _build_config(session_id), command, request_id, session_id
    ):
        yield chunk
