"""重排（rerank）客户端：对候选文档按与 query 的相关性重新排序。

硅基流动的 rerank 是独立 HTTP 接口（OpenAI SDK 不含），故用 httpx 手写。
返回 [(原始下标, 相关性分数)]，已按分数从高到低排序。
"""

import httpx

from app.core.config import settings
from app.core.exceptions import AppException


def _api_key() -> str:
    return settings.RERANK_API_KEY or settings.EMBEDDING_API_KEY


def rerank(query: str, documents: list[str], top_n: int | None = None) -> list[tuple[int, float]]:
    if not documents:
        return []
    key = _api_key()
    if not key:
        raise AppException("未配置 RERANK_API_KEY / EMBEDDING_API_KEY", 500, "config_error")

    payload: dict = {
        "model": settings.RERANK_MODEL,
        "query": query,
        "documents": documents,
    }
    if top_n is not None:
        payload["top_n"] = top_n

    url = settings.RERANK_BASE_URL.rstrip("/") + "/rerank"
    with httpx.Client(timeout=settings.EMBEDDING_TIMEOUT) as client:
        resp = client.post(url, json=payload, headers={"Authorization": f"Bearer {key}"})
        resp.raise_for_status()
        data = resp.json()

    results = data.get("results", [])
    ranked = [(item["index"], float(item.get("relevance_score", 0.0))) for item in results]
    ranked.sort(key=lambda x: x[1], reverse=True)
    return ranked
