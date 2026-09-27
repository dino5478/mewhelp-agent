"""可观测：给一次请求留一条调用链。

本地用 audit_logs 记每个节点/工具的耗时（无外部依赖，随时能查）；
配了 Langfuse key 就再挂一个回调，把 prompt/耗时/成本传到云端。
没配 key 也不会报错，直接降级成本地模式。
"""

import logging
import uuid

from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import SessionLocal
from app.models import AuditLog

logger = logging.getLogger("mewhelp")

_langfuse_handler = None
_langfuse_inited = False


def new_request_id() -> str:
    return uuid.uuid4().hex


def record_span(
    request_id: str,
    session_id: int | None = None,
    node: str | None = None,
    tool: str | None = None,
    latency_ms: int | None = None,
    error: str | None = None,
) -> None:
    """落一条 span。记录失败不能影响主流程。"""
    db = SessionLocal()
    try:
        db.add(AuditLog(
            request_id=request_id,
            session_id=session_id,
            node=node,
            tool=tool,
            latency_ms=latency_ms,
            error=error,
        ))
        db.commit()
    except Exception:  # noqa: BLE001
        logger.exception("record_span failed")
    finally:
        db.close()


def get_langfuse_handler():
    """有 key 才返回回调，否则 None（本地降级）。"""
    global _langfuse_handler, _langfuse_inited
    if _langfuse_inited:
        return _langfuse_handler
    _langfuse_inited = True

    if not (settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY):
        return None
    try:
        from langfuse.langchain import CallbackHandler

        _langfuse_handler = CallbackHandler()
        logger.info("langfuse tracing enabled")
    except Exception:  # noqa: BLE001
        logger.exception("init langfuse failed, fallback to local tracing")
        _langfuse_handler = None
    return _langfuse_handler


def fetch_trace(db: Session, request_id: str) -> list[AuditLog]:
    return (
        db.query(AuditLog)
        .filter(AuditLog.request_id == request_id)
        .order_by(AuditLog.id)
        .all()
    )


def recent_traces(db: Session, limit: int = 20) -> list[dict]:
    """按 request_id 归并出最近的链路概览。"""
    rows = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(300).all()
    seen: dict[str, dict] = {}
    for row in rows:
        item = seen.get(row.request_id)
        if item is None:
            seen[row.request_id] = {
                "request_id": row.request_id,
                "nodes": 1,
                "last_time": row.created_at.isoformat() if row.created_at else "",
            }
        else:
            item["nodes"] += 1
    return list(seen.values())[:limit]
