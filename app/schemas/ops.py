"""运营相关的传输模型。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ApproveRequest(BaseModel):
    answer: str = Field(min_length=1, max_length=2000, description="人工补充的答案")
    reviewer: str | None = Field(default=None, max_length=64)


class RejectRequest(BaseModel):
    reviewer: str | None = Field(default=None, max_length=64)


class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    query: str
    intent: str | None = None
    entry: str
    freq: int
    status: str
    retrieval_snapshot: dict | None = None
    created_at: datetime
