"""运营路由：问题池查看与审核。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import QuestionPool
from app.schemas.ops import ApproveRequest, QuestionOut, RejectRequest
from app.services import ops

router = APIRouter(prefix="/ops", tags=["ops"])


@router.get("/questions", response_model=list[QuestionOut])
def list_questions(
    status: str | None = "pending", db: Session = Depends(get_db)
) -> list[QuestionPool]:
    return ops.list_questions(db, status)


@router.post("/questions/{question_id}/approve")
def approve(
    question_id: int, payload: ApproveRequest, db: Session = Depends(get_db)
) -> dict:
    return ops.approve(db, question_id, payload.answer, payload.reviewer)


@router.post("/questions/{question_id}/reject")
def reject(
    question_id: int, payload: RejectRequest, db: Session = Depends(get_db)
) -> dict:
    return ops.reject(db, question_id, payload.reviewer)
