"""种子数据：本地开发用的用户、商品、订单。可重复执行（存在则跳过）。

用法（项目根目录）:
    python -m uv run python scripts/seed_data.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bcrypt

from app.database import SessionLocal
from app.models import Order, OrderItem, Product, User


def hash_password(raw: str) -> str:
    return bcrypt.hashpw(raw.encode(), bcrypt.gensalt()).decode()


def seed() -> None:
    db = SessionLocal()
    try:
        if db.query(User).filter_by(username="alice").first() is None:
            user = User(username="alice", password_hash=hash_password("alice123"))
            db.add(user)
            db.flush()
            print(f"[seed] created user alice (id={user.id})")
        else:
            user = db.query(User).filter_by(username="alice").first()
            print("[seed] user alice already exists, skip")

        if db.query(Product).count() == 0:
            products = [
                Product(title="无线蓝牙耳机", price=299.00, attrs={"color": "白色", "保修": "1年"}),
                Product(title="机械键盘", price=499.00, attrs={"轴体": "红轴", "保修": "2年"}),
                Product(title="保温杯", price=129.00, attrs={"容量": "500ml", "材质": "316不锈钢"}),
            ]
            db.add_all(products)
            db.flush()
            print(f"[seed] created {len(products)} products")
        else:
            products = db.query(Product).order_by(Product.id).all()
            print("[seed] products already exist, skip")

        if db.query(Order).count() == 0:
            order = Order(user_id=user.id, status="shipped", total_amount=798.00)
            db.add(order)
            db.flush()
            db.add_all([
                OrderItem(
                    order_id=order.id, product_id=products[0].id,
                    quantity=1, unit_price=299.00,
                ),
                OrderItem(
                    order_id=order.id, product_id=products[1].id,
                    quantity=1, unit_price=499.00,
                ),
            ])
            print(f"[seed] created order id={order.id}")
        else:
            print("[seed] orders already exist, skip")

        db.commit()
        print("[seed] done")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
