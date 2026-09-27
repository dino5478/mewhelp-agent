"""聊天路由：SSE 流式对话（需登录）。"""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas.chat import ChatRequest
from app.services import chat_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/stream")
def chat_stream(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    session = chat_service.get_or_create_session(db, current_user.id, payload.session_id)
    chat_service.append_message(db, session.id, "user", payload.message)

    return StreamingResponse(
        chat_service.stream_reply(session.id, payload.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",       # 不缓存
            "X-Accel-Buffering": "no",         # 告诉 Nginx 之类的代理别缓冲，保证实时
        },
    )
