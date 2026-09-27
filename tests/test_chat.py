"""聊天 SSE 测试：mock 掉图，验证事件流与节点过滤。"""

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessageChunk

from app.services import chat_service


class _FakeGraph:
    """假图：故意混入一个 preprocess 节点，验证它会被过滤掉。"""

    async def astream(self, state, stream_mode=None):
        yield ("messages", (AIMessageChunk(content="{意图JSON}"), {"langgraph_node": "preprocess"}))
        yield ("messages", (AIMessageChunk(content="满 99"), {"langgraph_node": "rag"}))
        yield ("messages", (AIMessageChunk(content=" 元包邮"), {"langgraph_node": "rag"}))
        yield ("values", {"answer": "满 99 元包邮"})


def _collect(client: TestClient, headers: dict, message: str) -> tuple[list[str], str]:
    events: list[str] = []
    tokens = ""
    with client.stream("POST", "/chat/stream", headers=headers, json={"message": message}) as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        current_event = None
        for line in r.iter_lines():
            if line.startswith("event:"):
                current_event = line.split(":", 1)[1].strip()
                events.append(current_event)
            elif line.startswith("data:") and current_event == "token":
                tokens += line.split(":", 1)[1].strip()
    return events, tokens


def test_chat_stream_events(client: TestClient, make_user, monkeypatch) -> None:
    monkeypatch.setattr(chat_service, "build_graph", lambda user_id: _FakeGraph())
    headers, _, _ = make_user()
    events, tokens = _collect(client, headers, "运费是多少")
    assert "token" in events
    assert events[-1] == "done"
    assert "满 99" in tokens
    # preprocess 的 token 不该出现
    assert "意图JSON" not in tokens


def test_chat_requires_token(client: TestClient) -> None:
    r = client.post("/chat/stream", json={"message": "hi"})
    assert r.status_code == 401
