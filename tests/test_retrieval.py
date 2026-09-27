"""检索测试：RRF 纯函数 + hybrid_search 分支逻辑（用假数据，不真调 API）。"""

from app.services import retrieval
from app.services.retrieval import RetrievedChunk


def test_rrf_prefers_items_ranked_high_in_both() -> None:
    # "b" 在两路都排第 1，应该融合后第一
    fused = retrieval.reciprocal_rank_fusion([["b", "a"], ["b", "c"]])
    assert fused[0][0] == "b"
    assert {doc_id for doc_id, _ in fused} == {"a", "b", "c"}


def test_rrf_empty() -> None:
    assert retrieval.reciprocal_rank_fusion([]) == []


def _fake_chunk(doc_id: str, text: str) -> RetrievedChunk:
    return RetrievedChunk(id=doc_id, text=text, heading_path="", doc_id=1, source="d", score=0.0)


def test_hybrid_search_dense_only_no_rerank(monkeypatch) -> None:
    monkeypatch.setattr(retrieval.embedding, "embed_query", lambda q: [0.1, 0.2])
    fake = [_fake_chunk("c1", "满99包邮"), _fake_chunk("c2", "7天退货")]
    monkeypatch.setattr(retrieval, "_search", lambda *a, **k: fake)
    # 关闭 rerank（否则要真调 API）
    out = retrieval.hybrid_search("运费", use_dense=True, use_sparse=False, use_rerank=False)
    assert [c.id for c in out] == ["c1", "c2"]
