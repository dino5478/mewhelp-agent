"""订单相关的传输模型（Schema）。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product_title: str | None = None
    quantity: int
    unit_price: float


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    total_amount: float
    created_at: datetime
    items: list[OrderItemOut]
