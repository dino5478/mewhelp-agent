"""图的节点与分支逻辑测试（离线，不真调模型/检索）。"""

from langchain_core.messages import AIMessage, HumanMessage

from app.services.graph import build, nodes
from app.services.retrieval import RetrievedChunk


def _chunk() -> RetrievedChunk:
    return RetrievedChunk(id="1-0", text="满99包邮", heading_path="运费", doc_id=1,
                          source="a.md", score=0.9)


def test_route_after_preprocess() -> None:
    assert build._route_after_preprocess({"route": "faq"}) == "retrieve"
    assert build._route_after_preprocess({"route": "order"}) == "agent"


def test_route_after_confidence() -> None:
    assert build._route_after_confidence({"confident": True}) == "generate"
    assert build._route_after_confidence({"confident": False}) == "handoff"


def test_agent_should_continue() -> None:
    with_tool = {"messages": [AIMessage(content="", tool_calls=[
        {"name": "get_order", "args": {"order_id": 1}, "id": "c1"}
    ])]}
    assert build._agent_should_continue(with_tool) == "tools"
    assert build._agent_should_continue({"messages": [AIMessage(content="好的")]}) == "finalize"


def test_preprocess_node(monkeypatch) -> None:
    monkeypatch.setattr(
        nodes.intent, "analyze",
        lambda msg, history=None: {
            "standalone_query": "运费是多少", "intent": "运费咨询", "route": "faq"
        },
    )
    out = nodes.preprocess_node({"query": "运费多少"})
    assert out["route"] == "faq"
    assert out["messages"][0].content == "运费是多少"


def test_retrieve_node(monkeypatch) -> None:
    monkeypatch.setattr(nodes.retrieval, "hybrid_search", lambda q, **k: [_chunk()])
    out = nodes.retrieve_node({"standalone_query": "运费"})
    assert "满99包邮" in out["context"]
    assert out["top_score"] == 0.9
    assert out["retrieved"][0]["id"] == "1-0"


def test_confidence_node(monkeypatch) -> None:
    monkeypatch.setattr(nodes.confidence, "judge", lambda q, c, s: (False, "self_eval_no"))
    out = nodes.confidence_node({"standalone_query": "x", "context": "y", "top_score": 0.1})
    assert out["confident"] is False
    assert out["confidence_reason"] == "self_eval_no"


def test_generate_node(monkeypatch) -> None:
    monkeypatch.setattr(nodes.llm, "chat", lambda messages, temperature=0.0: "满 99 元包邮。")
    out = nodes.generate_node({"standalone_query": "运费", "context": "满99包邮"})
    assert out["answer"] == "满 99 元包邮。"


def test_handoff_node() -> None:
    out = nodes.handoff_node({"standalone_query": "答不上来的问题"})
    assert out["need_human"] is True
    assert "转人工" in out["answer"]


def test_finalize_prefers_answer() -> None:
    assert nodes.finalize_node({"answer": "已答"}) == {}


def test_finalize_falls_back_to_last_ai_message() -> None:
    out = nodes.finalize_node({"messages": [HumanMessage(content="hi"), AIMessage(content="你好")]})
    assert out["answer"] == "你好"
