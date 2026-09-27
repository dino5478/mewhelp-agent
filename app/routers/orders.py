"""订单路由：当前用户的订单列表与详情（均需登录）。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Order, User
from app.schemas.order import OrderOut
from app.services import order_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("", response_model=list[OrderOut])
def list_my_orders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Order]:
    return order_service.list_orders(db, current_user.id)


@router.get("/{order_id}", response_model=OrderOut)
def get_my_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Order:
    return order_service.get_order(db, current_user.id, order_id)
