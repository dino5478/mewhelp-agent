"""订单业务逻辑：查询 + 归属校验。"""

from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.models import Order


def list_orders(db: Session, user_id: int) -> list[Order]:
    return (
        db.query(Order)
        .filter_by(user_id=user_id)
        .order_by(Order.id.desc())
        .all()
    )


def get_order(db: Session, user_id: int, order_id: int) -> Order:
    order = db.get(Order, order_id)
    if order is None:
        raise NotFoundError("订单不存在")
    if order.user_id != user_id:
        # 归属校验：不是本人的订单，一律 403，避免越权
        raise ForbiddenError("无权查看该订单")
    return order
