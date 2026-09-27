"""认证相关测试：注册 / 登录 / 当前用户。"""

import random

from fastapi.testclient import TestClient


def test_register_login_me(client: TestClient) -> None:
    username = f"auth_{random.randint(100000, 999999)}"
    r = client.post("/users/register", json={"username": username, "password": "pass123"})
    assert r.status_code == 201
    assert r.json()["username"] == username

    r = client.post("/users/login", data={"username": username, "password": "pass123"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    assert token

    r = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["username"] == username


def test_duplicate_register_conflicts(client: TestClient) -> None:
    username = f"dup_{random.randint(100000, 999999)}"
    assert client.post(
        "/users/register", json={"username": username, "password": "pass123"}
    ).status_code == 201
    r = client.post("/users/register", json={"username": username, "password": "pass123"})
    assert r.status_code == 409
    assert r.json()["code"] == "conflict"


def test_wrong_password_unauthorized(client: TestClient) -> None:
    username = f"wrong_{random.randint(100000, 999999)}"
    client.post("/users/register", json={"username": username, "password": "pass123"})
    r = client.post("/users/login", data={"username": username, "password": "bad-pass"})
    assert r.status_code == 401


def test_me_requires_token(client: TestClient) -> None:
    assert client.get("/users/me").status_code == 401
