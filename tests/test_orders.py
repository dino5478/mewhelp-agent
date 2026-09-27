"""订单测试：归属校验、列表、404。"""

from fastapi.testclient import TestClient


def test_order_ownership_ok(client: TestClient, make_user, make_order) -> None:
    headers, user_id, _ = make_user()
    order_id = make_order(user_id)

    assert client.get(f"/orders/{order_id}", headers=headers).status_code == 200
    r = client.get("/orders", headers=headers)
    assert r.status_code == 200
    assert order_id in [o["id"] for o in r.json()]


def test_order_forbidden_for_other_user(client: TestClient, make_user, make_order) -> None:
    _, owner_id, _ = make_user()
    order_id = make_order(owner_id)

    headers2, _, _ = make_user()
    r = client.get(f"/orders/{order_id}", headers=headers2)
    assert r.status_code == 403
    assert r.json()["code"] == "forbidden"


def test_order_not_found(client: TestClient, make_user) -> None:
    headers, _, _ = make_user()
    assert client.get("/orders/99999999", headers=headers).status_code == 404


def test_orders_require_token(client: TestClient) -> None:
    assert client.get("/orders").status_code == 401
