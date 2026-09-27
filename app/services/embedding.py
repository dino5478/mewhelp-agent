"""嵌入（embedding）客户端：把文本转成向量。默认用硅基流动 BAAI/bge-m3。"""

from openai import OpenAI

from app.core.config import settings
from app.core.exceptions import AppException

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        if not settings.EMBEDDING_API_KEY:
            raise AppException("未配置 EMBEDDING_API_KEY", 500, "config_error")
        _client = OpenAI(
            api_key=settings.EMBEDDING_API_KEY,
            base_url=settings.EMBEDDING_BASE_URL,
            timeout=settings.EMBEDDING_TIMEOUT,
        )
    return _client


def embed_texts(texts: list[str]) -> list[list[float]]:
    """批量把文本转成向量。"""
    if not texts:
        return []
    resp = _get_client().embeddings.create(model=settings.EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in resp.data]


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
