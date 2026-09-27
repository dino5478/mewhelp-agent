"""可观测路由：查一次请求的调用链。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.database import get_db
from app.services import observability

router = APIRouter(prefix="/trace", tags=["observability"])


@router.get("/recent")
def recent(db: Session = Depends(get_db)) -> list[dict]:
    return observability.recent_traces(db)


@router.get("/{request_id}")
def detail(request_id: str, db: Session = Depends(get_db)) -> dict:
    rows = observability.fetch_trace(db, request_id)
    if not rows:
        raise NotFoundError("没有这条链路记录")
    return {
        "request_id": request_id,
        "spans": [
            {
                "node": r.node,
                "tool": r.tool,
                "latency_ms": r.latency_ms,
                "error": r.error,
                "time": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }
