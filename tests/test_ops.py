"""运营测试：问题池排序与审核。"""

import random

from app.database import SessionLocal
from app.models import QuestionPool
from app.services import ops


def _make_question(freq: int) -> int:
    db = SessionLocal()
    try:
        row = QuestionPool(
            query=f"ops问题{random.randint(100000, 999999)}",
            entry="weak_retrieval",
            freq=freq,
            status="pending",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row.id
    finally:
        db.close()


def _cleanup(ids: list[int]) -> None:
    db = SessionLocal()
    try:
        db.query(QuestionPool).filter(QuestionPool.id.in_(ids)).delete(
            synchronize_session=False
        )
        db.commit()
    finally:
        db.close()


def test_list_orders_by_freq() -> None:
    low = _make_question(1)
    high = _make_question(9)
    db = SessionLocal()
    try:
        rows = ops.list_questions(db, status="pending")
        ordered_ids = [r.id for r in rows]
        assert ordered_ids.index(high) < ordered_ids.index(low)
    finally:
        db.close()
        _cleanup([low, high])


def test_approve_writes_back(monkeypatch) -> None:
    qid = _make_question(2)
    called = {}
    monkeypatch.setattr(
        ops.knowledge, "ingest_document",
        lambda db, title, text, source="manual": called.update(title=title) or 3,
    )
    db = SessionLocal()
    try:
        result = ops.approve(db, qid, "这是人工补充的答案", reviewer="ops1")
        assert result["status"] == "approved"
        assert result["chunks"] == 3
        assert "运营补充" in called["title"]
        row = db.get(QuestionPool, qid)
        assert row.answer == "这是人工补充的答案"
    finally:
        db.close()
        _cleanup([qid])


def test_reject() -> None:
    qid = _make_question(1)
    db = SessionLocal()
    try:
        result = ops.reject(db, qid, reviewer="ops1")
        assert result["status"] == "rejected"
    finally:
        db.close()
        _cleanup([qid])
