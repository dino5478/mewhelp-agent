"""用户相关的传输模型（Schema）：定义接口收/发什么字段。"""

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64, description="用户名")
    password: str = Field(min_length=6, max_length=128, description="密码（明文，仅传输）")


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # 允许直接从 ORM 对象转换

    id: int
    username: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
