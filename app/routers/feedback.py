"""反馈路由。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas.feedback import FeedbackRequest
from app.services import feedback

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", status_code=201)
def create(
    payload: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    fb = feedback.submit_feedback(
        db, current_user.id, payload.message_id, payload.type, payload.comment
    )
    return {"id": fb.id, "type": fb.type}
