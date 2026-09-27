"""混合检索：稠密 + BM25 双路召回 -> RRF 融合 -> 重排。

对外提供 hybrid_search，并允许开关每一路，以便做 4 方案对照实验：
- dense_only
- sparse_only
- hybrid (RRF)
- hybrid + rerank
"""

from __future__ import annotations

from dataclasses import dataclass

from pymilvus import MilvusClient

from app.core.config import settings
from app.services import embedding, reranker
from app.services.milvus_store import get_client

_OUTPUT_FIELDS = ["text", "heading_path", "doc_id", "source"]


@dataclass
class RetrievedChunk:
    id: str
    text: str
    heading_path: str
    doc_id: int
    source: str
    score: float


def reciprocal_rank_fusion(rankings: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    """RRF：输入若干"按相关性排序的 id 列表"，输出融合后的 (id, 分数) 降序列表。"""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)


def _parse_hits(raw_hits) -> list[RetrievedChunk]:
    chunks: list[RetrievedChunk] = []
    for hit in raw_hits:
        # MilvusClient 返回 dict；兼容对象式访问
        if isinstance(hit, dict):
            entity = hit.get("entity", {})
            distance = hit.get("distance", 0.0)
            chunk_id = hit.get("id")
        else:
            entity = hit.entity
            distance = hit.distance
            chunk_id = hit.id
        chunks.append(
            RetrievedChunk(
                id=str(chunk_id),
                text=entity.get("text", ""),
                heading_path=entity.get("heading_path", ""),
                doc_id=int(entity.get("doc_id", 0)),
                source=entity.get("source", ""),
                score=float(distance),
            )
        )
    return chunks


def _search(
    client: MilvusClient,
    collection: str,
    data,
    anns_field: str,
    metric_type: str,
    limit: int,
) -> list[RetrievedChunk]:
    res = client.search(
        collection_name=collection,
        data=[data],
        anns_field=anns_field,
        search_params={"metric_type": metric_type},
        limit=limit,
        output_fields=_OUTPUT_FIELDS,
    )
    return _parse_hits(res[0]) if res else []


def hybrid_search(
    query: str,
    top_k: int | None = None,
    recall_n: int | None = None,
    use_dense: bool = True,
    use_sparse: bool = True,
    use_rerank: bool = True,
    collection_name: str | None = None,
    client: MilvusClient | None = None,
) -> list[RetrievedChunk]:
    """按开关执行检索。返回按相关性排序的 RetrievedChunk 列表。"""
    top_k = top_k or settings.RAG_TOP_K
    recall_n = recall_n or settings.RAG_RECALL_TOP_N
    collection = collection_name or settings.MILVUS_COLLECTION
    client = client or get_client()

    rankings: list[list[str]] = []
    by_id: dict[str, RetrievedChunk] = {}

    if use_dense:
        query_vec = embedding.embed_query(query)
        dense_hits = _search(client, collection, query_vec, "dense", "COSINE", recall_n)
        for chunk in dense_hits:
            by_id.setdefault(chunk.id, chunk)
        rankings.append([c.id for c in dense_hits])

    if use_sparse:
        sparse_hits = _search(client, collection, query, "sparse", "BM25", recall_n)
        for chunk in sparse_hits:
            by_id.setdefault(chunk.id, chunk)
        rankings.append([c.id for c in sparse_hits])

    if not rankings:
        return []

    fused = reciprocal_rank_fusion(rankings)
    if use_dense and use_sparse:
        candidates = [by_id[doc_id] for doc_id, _ in fused[:recall_n] if doc_id in by_id]
    else:
        # 单路：融合结果就等于该路顺序
        candidates = [by_id[doc_id] for doc_id, _ in fused if doc_id in by_id][:recall_n]

    if use_rerank and candidates:
        scores = reranker.rerank(query, [c.text for c in candidates])
        reranked = []
        for idx, score in scores:
            if 0 <= idx < len(candidates):
                chunk = candidates[idx]
                chunk.score = score
                reranked.append(chunk)
        candidates = reranked

    return candidates[:top_k]
