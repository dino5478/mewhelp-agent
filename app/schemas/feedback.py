"""用户反馈：点赞只记录，点踩把问题送进问题池。"""

from typing import Literal

from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    message_id: int = Field(description="被反馈的消息 id")
    type: Literal["up", "down"] = Field(description="up 点赞 / down 点踩")
    comment: str | None = Field(default=None, max_length=500)
