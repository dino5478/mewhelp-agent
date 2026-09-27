"""双层上下文测试：摘要触发与近期窗口。"""

import random

from app.database import SessionLocal
from app.models import ChatSession, Message, User
from app.services import context


def _make_session() -> int:
    db = SessionLocal()
    try:
        user = User(username=f"ctx_{random.randint(100000, 999999)}", password_hash="x")
        db.add(user)
        db.commit()
        db.refresh(user)
        session = ChatSession(user_id=user.id)
        db.add(session)
        db.commit()
        db.refresh(session)
        return session.id
    finally:
        db.close()


def _cleanup(session_id: int) -> None:
    db = SessionLocal()
    try:
        session = db.get(ChatSession, session_id)
        if session:
            user_id = session.user_id
            db.query(Message).filter(Message.session_id == session_id).delete()
            db.delete(session)
            user = db.get(User, user_id)
            if user:
                db.delete(user)
            db.commit()
    finally:
        db.close()


def test_get_context_returns_recent_and_summary() -> None:
    session_id = _make_session()
    try:
        db = SessionLocal()
        session = db.get(ChatSession, session_id)
        for i in range(3):
            db.add(Message(session_id=session_id, role="user", content=f"q{i}"))
            db.add(Message(session_id=session_id, role="assistant", content=f"a{i}"))
        session.summary = "之前的摘要"
        db.commit()

        ctx = context.get_context(db, session)
        assert ctx["summary"] == "之前的摘要"
        assert len(ctx["recent"]) <= context.RECENT_KEEP
        db.close()
    finally:
        _cleanup(session_id)


def test_summarize_triggers_when_too_many(monkeypatch) -> None:
    session_id = _make_session()
    monkeypatch.setattr(context.llm, "chat", lambda messages, temperature=0.0: "压缩后的摘要")
    try:
        db = SessionLocal()
        for i in range(context.SUMMARIZE_AFTER + 2):
            db.add(Message(session_id=session_id, role="user", content=f"m{i}"))
        db.commit()
        session = db.get(ChatSession, session_id)

        summary = context.summarize_if_needed(db, session)
        assert summary == "压缩后的摘要"
        assert session.summary == "压缩后的摘要"
        db.close()
    finally:
        _cleanup(session_id)


def test_summarize_skips_when_short() -> None:
    session_id = _make_session()
    try:
        db = SessionLocal()
        db.add(Message(session_id=session_id, role="user", content="只有一条"))
        db.commit()
        session = db.get(ChatSession, session_id)
        assert context.summarize_if_needed(db, session) is None
        db.close()
    finally:
        _cleanup(session_id)
