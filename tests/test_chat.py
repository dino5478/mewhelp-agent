"""聊天 SSE 测试：mock 掉图，验证事件流、节点过滤与中断。"""

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessageChunk

from app.services import chat_service


@pytest.fixture(autouse=True)
def _no_checkpointer(monkeypatch):
    """聊天测试不真连 Redis 检查点。"""

    async def _cp():
        return None

    monkeypatch.setattr(chat_service, "get_checkpointer", _cp)


class _Snap:
    def __init__(self, tasks):
        self.tasks = tasks


class _Task:
    def __init__(self, interrupts):
        self.interrupts = interrupts


class _Interrupt:
    def __init__(self, value):
        self.value = value


class _FakeGraph:
    """假图：混入一个 preprocess 节点，验证它会被过滤掉。"""

    async def astream(self, state, config=None, stream_mode=None):
        yield ("messages", (AIMessageChunk(content="{意图JSON}"), {"langgraph_node": "preprocess"}))
        yield ("messages", (AIMessageChunk(content="满 99"), {"langgraph_node": "generate"}))
        yield ("messages", (AIMessageChunk(content=" 元包邮"), {"langgraph_node": "generate"}))
        yield ("values", {"answer": "满 99 元包邮"})

    async def aget_state(self, config):
        return _Snap([])


class _FakeHandoffGraph:
    async def astream(self, state, config=None, stream_mode=None):
        yield ("messages", (AIMessageChunk(content="已转人工"), {"langgraph_node": "handoff"}))
        yield ("values", {
            "answer": "已转人工", "need_human": True, "confidence_reason": "self_eval_no"
        })

    async def aget_state(self, config):
        return _Snap([])


class _FakeInterruptGraph:
    async def astream(self, state, config=None, stream_mode=None):
        yield ("values", {"query": "我要退款", "route": "aftersale"})

    async def aget_state(self, config):
        payload = {"type": "select_order", "orders": [{"id": 1, "title": "订单 1"}]}
        return _Snap([_Task([_Interrupt(payload)])])


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
    monkeypatch.setattr(
        chat_service, "build_graph", lambda user_id, checkpointer=None: _FakeGraph()
    )
    headers, _, _ = make_user()
    events, tokens = _collect(client, headers, "运费是多少")
    assert "token" in events
    assert events[-1] == "done"
    assert "满 99" in tokens
    # preprocess 的 token 不该出现
    assert "意图JSON" not in tokens


def test_chat_stream_emits_handoff(client: TestClient, make_user, monkeypatch) -> None:
    monkeypatch.setattr(
        chat_service, "build_graph", lambda user_id, checkpointer=None: _FakeHandoffGraph()
    )
    headers, _, _ = make_user()
    events, _ = _collect(client, headers, "知识库没有的问题")
    assert "handoff" in events
    assert events[-1] == "done"


def test_chat_stream_interrupts_for_order_selection(
    client: TestClient, make_user, monkeypatch
) -> None:
    monkeypatch.setattr(
        chat_service, "build_graph", lambda user_id, checkpointer=None: _FakeInterruptGraph()
    )
    headers, _, _ = make_user()
    events, _ = _collect(client, headers, "我要退款")
    assert "need_order_selection" in events
    assert events[-1] == "done"


def test_chat_requires_token(client: TestClient) -> None:
    r = client.post("/chat/stream", json={"message": "hi"})
    assert r.status_code == 401
