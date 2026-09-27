"""反馈测试：点踩把问题写进问题池。"""

import random

from app.database import SessionLocal
from app.models import ChatSession, Feedback, Message, QuestionPool, User
from app.services import feedback


def _seed() -> dict:
    db = SessionLocal()
    try:
        user = User(username=f"fb_{random.randint(100000, 999999)}", password_hash="x")
        db.add(user)
        db.commit()
        db.refresh(user)
        session = ChatSession(user_id=user.id)
        db.add(session)
        db.commit()
        db.refresh(session)
        question = f"这个冷门问题没人回答 {random.randint(100000, 999999)}"
        um = Message(session_id=session.id, role="user", content=question)
        db.add(um)
        db.commit()
        db.refresh(um)
        am = Message(session_id=session.id, role="assistant", content="我不太确定")
        db.add(am)
        db.commit()
        db.refresh(am)
        return {"user": user.id, "session": session.id, "assistant": am.id, "question": question}
    finally:
        db.close()


def _cleanup(user_id: int, session_id: int) -> None:
    db = SessionLocal()
    try:
        db.query(QuestionPool).filter(QuestionPool.session_id == session_id).delete()
        # feedback 外键指向 messages，得先删
        msg_ids = [m.id for m in db.query(Message).filter(Message.session_id == session_id).all()]
        if msg_ids:
            db.query(Feedback).filter(Feedback.message_id.in_(msg_ids)).delete(
                synchronize_session=False
            )
        db.query(Message).filter(Message.session_id == session_id).delete()
        session = db.get(ChatSession, session_id)
        if session:
            db.delete(session)
        user = db.get(User, user_id)
        if user:
            db.delete(user)
        db.commit()
    finally:
        db.close()


def test_thumbs_down_creates_question() -> None:
    ids = _seed()
    db = SessionLocal()
    try:
        feedback.submit_feedback(db, ids["user"], ids["assistant"], "down", "答得不对")
    finally:
        db.close()

    verify = SessionLocal()
    try:
        row = (
            verify.query(QuestionPool)
            .filter(QuestionPool.session_id == ids["session"])
            .one()
        )
        assert row.entry == "thumbs_down"
        assert row.query == ids["question"]
    finally:
        verify.close()
        _cleanup(ids["user"], ids["session"])


def test_thumbs_up_does_not_create_question() -> None:
    ids = _seed()
    db = SessionLocal()
    try:
        feedback.submit_feedback(db, ids["user"], ids["assistant"], "up", None)
        count = (
            db.query(QuestionPool)
            .filter(QuestionPool.session_id == ids["session"])
            .count()
        )
        assert count == 0
    finally:
        db.close()
        _cleanup(ids["user"], ids["session"])


def test_feedback_forbidden_for_other_user() -> None:
    ids = _seed()
    db = SessionLocal()
    try:
        import pytest

        from app.core.exceptions import ForbiddenError

        with pytest.raises(ForbiddenError):
            feedback.submit_feedback(db, ids["user"] + 999999, ids["assistant"], "up", None)
    finally:
        db.close()
        _cleanup(ids["user"], ids["session"])
