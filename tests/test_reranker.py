"""重排客户端测试：用假 httpx.Client 验证解析与排序（离线）。"""

from app.services import reranker


class _FakeResp:
    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return {
            "results": [
                {"index": 2, "relevance_score": 0.2},
                {"index": 0, "relevance_score": 0.9},
                {"index": 1, "relevance_score": 0.5},
            ]
        }


class _FakeClient:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args) -> bool:
        return False

    def post(self, url, json=None, headers=None):
        return _FakeResp()


def test_rerank_parses_and_sorts(monkeypatch) -> None:
    monkeypatch.setattr(reranker.httpx, "Client", _FakeClient)
    out = reranker.rerank("问题", ["a", "b", "c"])
    assert out == [(0, 0.9), (1, 0.5), (2, 0.2)]


def test_rerank_empty_documents() -> None:
    assert reranker.rerank("问题", []) == []
