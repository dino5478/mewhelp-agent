"""pytest 公共夹具：客户端、新用户、临时订单。"""

import random

import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import Order


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def make_user(client: TestClient):
    """工厂夹具：每次调用创建一个新用户，返回 (headers, user_id, username)。"""

    def _make():
        username = f"test_{random.randint(100000, 999999)}"
        client.post("/users/register", json={"username": username, "password": "pass123"})
        token = client.post(
            "/users/login", data={"username": username, "password": "pass123"}
        ).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        user_id = client.get("/users/me", headers=headers).json()["id"]
        return headers, user_id, username

    return _make


@pytest.fixture
def make_order():
    """为指定用户创建一条订单，测试结束后清理。"""
    created: list[int] = []

    def _make(user_id: int, amount: float = 199.00) -> int:
        db = SessionLocal()
        try:
            order = Order(user_id=user_id, status="paid", total_amount=amount)
            db.add(order)
            db.commit()
            db.refresh(order)
            created.append(order.id)
            return order.id
        finally:
            db.close()

    yield _make

    db = SessionLocal()
    try:
        for order_id in created:
            order = db.get(Order, order_id)
            if order is not None:
                db.delete(order)
                db.commit()
    finally:
        db.close()
