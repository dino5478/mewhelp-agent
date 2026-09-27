"""嵌入客户端测试（离线，不真调 API）。"""

import pytest

from app.core.config import settings
from app.core.exceptions import AppException
from app.services import embedding


def test_embed_missing_key_raises(monkeypatch) -> None:
    monkeypatch.setattr(settings, "EMBEDDING_API_KEY", "")
    monkeypatch.setattr(embedding, "_client", None)
    with pytest.raises(AppException):
        embedding.embed_texts(["你好"])


def test_embed_empty_returns_empty() -> None:
    assert embedding.embed_texts([]) == []
