"""图的节点与分支逻辑测试（离线，不真调模型/检索）。"""

from langchain_core.messages import AIMessage, HumanMessage

from app.services.graph import build, nodes
from app.services.retrieval import RetrievedChunk


def test_route_after_preprocess() -> None:
    assert build._route_after_preprocess({"route": "faq"}) == "rag"
    assert build._route_after_preprocess({"route": "order"}) == "agent"
    assert build._route_after_preprocess({"route": "aftersale"}) == "agent"


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


def test_rag_node_with_context(monkeypatch) -> None:
    fake = [RetrievedChunk(id="1-0", text="满99包邮", heading_path="运费", doc_id=1,
                           source="a.md", score=1.0)]
    monkeypatch.setattr(nodes.retrieval, "hybrid_search", lambda q, **k: fake)
    monkeypatch.setattr(nodes.llm, "chat", lambda messages, temperature=0.0: "满 99 元包邮。")
    out = nodes.rag_node({"standalone_query": "运费多少"})
    assert out["answer"] == "满 99 元包邮。"


def test_rag_node_no_hit() -> None:
    # 用空的检索结果直接调，触发兜底话术
    import app.services.graph.nodes as n

    original = n.retrieval.hybrid_search
    n.retrieval.hybrid_search = lambda q, **k: []
    try:
        out = nodes.rag_node({"standalone_query": "没收录的问题"})
    finally:
        n.retrieval.hybrid_search = original
    assert "转人工" in out["answer"]


def test_finalize_prefers_answer() -> None:
    assert nodes.finalize_node({"answer": "已答"}) == {}


def test_finalize_falls_back_to_last_ai_message() -> None:
    out = nodes.finalize_node({"messages": [HumanMessage(content="hi"), AIMessage(content="你好")]})
    assert out["answer"] == "你好"
