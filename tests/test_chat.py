"""聊天 SSE 骨架测试：能拿到 token 事件与 done 事件。"""

from fastapi.testclient import TestClient


def _collect_events(client: TestClient, headers: dict, message: str) -> list[str]:
    events: list[str] = []
    with client.stream("POST", "/chat/stream", headers=headers, json={"message": message}) as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        for line in r.iter_lines():
            if line.startswith("event:"):
                events.append(line.split(":", 1)[1].strip())
    return events


def test_chat_stream_events(client: TestClient, make_user) -> None:
    headers, _, _ = make_user()
    events = _collect_events(client, headers, "运费是多少？")
    assert "token" in events
    assert events[-1] == "done"


def test_chat_requires_token(client: TestClient) -> None:
    r = client.post("/chat/stream", json={"message": "hi"})
    assert r.status_code == 401
