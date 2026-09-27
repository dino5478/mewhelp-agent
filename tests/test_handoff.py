"""转人工落库测试。"""

from app.database import SessionLocal
from app.models import QuestionPool
from app.services import handoff


def test_record_handoff_inserts_row() -> None:
    record_id = handoff.record_handoff(
        user_id=None,
        session_id=None,
        query="一个知识库没有的问题",
        intent="其他",
        reason="self_eval_no",
        retrieved=[{"id": "1-0", "text": "无关片段"}],
    )
    assert record_id is not None

    db = SessionLocal()
    try:
        row = db.get(QuestionPool, record_id)
        assert row.query == "一个知识库没有的问题"
        assert row.entry == "weak_retrieval"
        assert row.retrieval_snapshot["reason"] == "self_eval_no"
        db.delete(row)
        db.commit()
    finally:
        db.close()


def test_same_question_dedups_and_counts() -> None:
    query = f"重复问题 {__import__('random').randint(1000, 9999)}"
    first = handoff.record_question(query=query, entry="weak_retrieval")
    second = handoff.record_question(query=query, entry="weak_retrieval")
    assert first == second

    db = SessionLocal()
    try:
        rows = db.query(QuestionPool).filter(QuestionPool.query == query).all()
        assert len(rows) == 1
        assert rows[0].freq == 2
        db.query(QuestionPool).filter(QuestionPool.query == query).delete()
        db.commit()
    finally:
        db.close()
