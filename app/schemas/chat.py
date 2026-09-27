"""聊天相关的传输模型（Schema）。"""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000, description="用户消息")
    session_id: int | None = Field(
        default=None, description="会话 id；不传则新建一个会话"
    )
