"""运营业务：问题池的查看与审核回写。"""

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models import QuestionPool
from app.services import knowledge


def list_questions(db: Session, status: str | None = "pending") -> list[QuestionPool]:
    query = db.query(QuestionPool)
    if status:
        query = query.filter(QuestionPool.status == status)
    # 被问得多的排前面，人工先处理高频的
    return query.order_by(QuestionPool.freq.desc(), QuestionPool.id.asc()).all()


def approve(
    db: Session, question_id: int, answer: str, reviewer: str | None = None
) -> dict:
    row = db.get(QuestionPool, question_id)
    if row is None:
        raise NotFoundError("问题不存在")

    row.status = "approved"
    row.answer = answer
    row.reviewer = reviewer
    db.commit()

    # 回写知识库：把"问题+答案"作为一个新文档入库，下次就能检索到
    text = f"# 运营补充：{row.query}\n\n问题：{row.query}\n\n答案：{answer}\n"
    chunks = knowledge.ingest_document(
        db, title=f"运营补充-{row.id}", text=text, source="ops"
    )
    return {"id": row.id, "status": row.status, "chunks": chunks}


def reject(db: Session, question_id: int, reviewer: str | None = None) -> dict:
    row = db.get(QuestionPool, question_id)
    if row is None:
        raise NotFoundError("问题不存在")
    row.status = "rejected"
    row.reviewer = reviewer
    db.commit()
    return {"id": row.id, "status": row.status}
