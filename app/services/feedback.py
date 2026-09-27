"""反馈业务：落库 + 点踩入问题池。"""

from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.models import ChatSession, Feedback, Message
from app.services import handoff


def _preceding_user_query(db: Session, message: Message) -> str:
    """点踩的是客服回复，往前找最近一条用户提问当作问题内容。"""
    row = (
        db.query(Message)
        .filter(
            Message.session_id == message.session_id,
            Message.role == "user",
            Message.id < message.id,
        )
        .order_by(Message.id.desc())
        .first()
    )
    return row.content if row else "(未知问题)"


def submit_feedback(
    db: Session, user_id: int, message_id: int, feedback_type: str, comment: str | None
) -> Feedback:
    message = db.get(Message, message_id)
    if message is None:
        raise NotFoundError("消息不存在")

    session = db.get(ChatSession, message.session_id)
    if session is None or session.user_id != user_id:
        raise ForbiddenError("无权反馈该消息")

    fb = Feedback(message_id=message_id, type=feedback_type, comment=comment)
    db.add(fb)
    db.commit()
    db.refresh(fb)

    if feedback_type == "down":
        handoff.record_question(
            query=_preceding_user_query(db, message),
            entry="thumbs_down",
            user_id=user_id,
            session_id=session.id,
            reason="thumbs_down",
        )
    return fb
