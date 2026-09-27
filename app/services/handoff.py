"""转人工 / 问题池：没答好的问题都往这里沉淀，等人工审核后补库。

入口有三种：检索弱被拒答、自评未通过、用户点踩。
同一个问题被问多次只记一条，累加 freq，审核时按热度排。
"""

import logging

from app.database import SessionLocal
from app.models import QuestionPool

logger = logging.getLogger("mewhelp")


def record_question(
    query: str,
    entry: str,
    user_id: int | None = None,
    session_id: int | None = None,
    intent: str | None = None,
    reason: str = "",
    retrieved: list[dict] | None = None,
) -> int | None:
    """写一条问题池记录（同问题累加频次）。失败不影响给用户的回复。"""
    db = SessionLocal()
    try:
        existing = (
            db.query(QuestionPool)
            .filter(QuestionPool.query == query, QuestionPool.status == "pending")
            .first()
        )
        if existing is not None:
            existing.freq += 1
            db.commit()
            return existing.id

        row = QuestionPool(
            user_id=user_id,
            session_id=session_id,
            query=query,
            intent=intent,
            entry=entry,
            retrieval_snapshot={"reason": reason, "chunks": retrieved or []},
            status="pending",
            freq=1,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row.id
    except Exception:  # noqa: BLE001  落库失败也不能把用户请求带崩
        logger.exception("record_question failed")
        return None
    finally:
        db.close()


def record_handoff(
    user_id: int | None,
    session_id: int | None,
    query: str,
    intent: str | None,
    reason: str,
    retrieved: list[dict] | None,
    entry: str = "weak_retrieval",
) -> int | None:
    return record_question(
        query=query,
        entry=entry,
        user_id=user_id,
        session_id=session_id,
        intent=intent,
        reason=reason,
        retrieved=retrieved,
    )
