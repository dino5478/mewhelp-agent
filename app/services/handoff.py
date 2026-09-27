"""转人工：把处理不了的问题记进问题池，等人工审核后补进知识库。

这就是数据飞轮的入口之一（检索弱被拒答）。
"""

import logging

from app.database import SessionLocal
from app.models import QuestionPool

logger = logging.getLogger("mewhelp")


def record_handoff(
    user_id: int | None,
    session_id: int | None,
    query: str,
    intent: str | None,
    reason: str,
    retrieved: list[dict] | None,
) -> int | None:
    """写一条问题池记录，返回记录 id。失败不影响给用户的回复。"""
    db = SessionLocal()
    try:
        row = QuestionPool(
            user_id=user_id,
            session_id=session_id,
            query=query,
            intent=intent,
            entry="weak_retrieval",
            retrieval_snapshot={"reason": reason, "chunks": retrieved or []},
            status="pending",
            freq=1,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row.id
    except Exception:  # noqa: BLE001  落库失败也不能把用户请求带崩
        logger.exception("record_handoff failed")
        return None
    finally:
        db.close()
