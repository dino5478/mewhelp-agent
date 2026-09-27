"""Milvus 集合管理测试（需要 Milvus 在跑，否则自动跳过）。"""

import pytest

from app.services import milvus_store

TEST_COLLECTION = "mewhelp_test_kb"


def _milvus_available() -> bool:
    try:
        milvus_store.get_client().list_collections()
        return True
    except Exception:  # noqa: BLE001
        return False


pytestmark = pytest.mark.skipif(not _milvus_available(), reason="Milvus 未运行")


def test_ensure_collection_creates_and_drops() -> None:
    name = milvus_store.ensure_collection(recreate=True, collection_name=TEST_COLLECTION)
    try:
        assert milvus_store.get_client().has_collection(name)
        # 幂等：再次调用不应报错
        assert milvus_store.ensure_collection(collection_name=TEST_COLLECTION) == name
    finally:
        milvus_store.drop_collection(TEST_COLLECTION)
    assert not milvus_store.get_client().has_collection(TEST_COLLECTION)
