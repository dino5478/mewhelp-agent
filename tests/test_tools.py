"""工具测试：订单归属校验 + 知识库工具（mock 掉检索）。"""

import random

from app.database import SessionLocal
from app.models import Order, User
from app.services import tools
from app.services.retrieval import RetrievedChunk


def _make_user_and_order() -> tuple[int, int]:
    db = SessionLocal()
    try:
        user = User(username=f"tool_{random.randint(100000, 999999)}", password_hash="x")
        db.add(user)
        db.commit()
        db.refresh(user)
        order = Order(user_id=user.id, status="shipped", total_amount=88.0)
        db.add(order)
        db.commit()
        db.refresh(order)
        return user.id, order.id
    finally:
        db.close()


def _cleanup(user_id: int, order_id: int) -> None:
    db = SessionLocal()
    try:
        order = db.get(Order, order_id)
        user = db.get(User, user_id)
        if order:
            db.delete(order)
        if user:
            db.delete(user)
        db.commit()
    finally:
        db.close()


def test_get_order_ok_and_forbidden() -> None:
    owner_id, order_id = _make_user_and_order()
    try:
        owner_tools = {t.name: t for t in tools.build_tools(owner_id)}
        assert "订单" in owner_tools["get_order"].invoke({"order_id": order_id})

        other_tools = {t.name: t for t in tools.build_tools(owner_id + 999999)}
        assert "失败" in other_tools["get_order"].invoke({"order_id": order_id})
    finally:
        _cleanup(owner_id, order_id)


def test_search_knowledge_base_formats_chunks(monkeypatch) -> None:
    fake = [RetrievedChunk(id="1-0", text="满99包邮", heading_path="运费政策", doc_id=1,
                           source="a.md", score=1.0)]
    monkeypatch.setattr(tools.retrieval, "hybrid_search", lambda q, **k: fake)
    kb = {t.name: t for t in tools.build_tools(1)}["search_knowledge_base"]
    out = kb.invoke({"query": "运费"})
    assert "满99包邮" in out
    assert "运费政策" in out


def test_tools_registered() -> None:
    names = {t.name for t in tools.build_tools(1)}
    assert names == {"search_knowledge_base", "get_order", "get_logistics"}
