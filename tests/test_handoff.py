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
