"""Milvus 客户端与集合管理。

集合同时承载两路召回：
- dense：稠密语义向量（bge-m3）
- sparse：由 BM25 函数从 text 字段自动生成的稀疏向量（Milvus 2.5 全文检索）
"""

from pymilvus import DataType, Function, FunctionType, MilvusClient

from app.core.config import settings


def get_client() -> MilvusClient:
    return MilvusClient(uri=f"http://{settings.MILVUS_HOST}:{settings.MILVUS_PORT}")


def _build_schema(client: MilvusClient):
    schema = client.create_schema(auto_id=False, enable_dynamic_field=False)
    schema.add_field("id", DataType.VARCHAR, is_primary=True, max_length=64)
    schema.add_field("dense", DataType.FLOAT_VECTOR, dim=settings.EMBEDDING_DIM)
    schema.add_field(
        "text",
        DataType.VARCHAR,
        max_length=8192,
        enable_analyzer=True,
        analyzer_params={"type": "chinese"},  # 中文分词
    )
    schema.add_field("sparse", DataType.SPARSE_FLOAT_VECTOR)
    schema.add_field("heading_path", DataType.VARCHAR, max_length=1024)
    schema.add_field("doc_id", DataType.INT64)
    schema.add_field("source", DataType.VARCHAR, max_length=255)
    # BM25 函数：把 text 自动转成 sparse 向量，无需我们手动算
    schema.add_function(
        Function(
            name="bm25",
            function_type=FunctionType.BM25,
            input_field_names=["text"],
            output_field_names=["sparse"],
        )
    )
    return schema


def _index_params(client: MilvusClient):
    params = client.prepare_index_params()
    params.add_index("dense", index_type="AUTOINDEX", metric_type="COSINE")
    params.add_index("sparse", index_type="AUTOINDEX", metric_type="BM25")
    return params


def ensure_collection(
    client: MilvusClient | None = None,
    recreate: bool = False,
    collection_name: str | None = None,
) -> str:
    """确保集合存在；recreate=True 时先删后建（用于重建索引）。返回集合名。"""
    client = client or get_client()
    name = collection_name or settings.MILVUS_COLLECTION

    if recreate and client.has_collection(name):
        client.drop_collection(name)
    if not client.has_collection(name):
        client.create_collection(
            collection_name=name,
            schema=_build_schema(client),
            index_params=_index_params(client),
        )
    return name


def drop_collection(collection_name: str | None = None) -> None:
    client = get_client()
    name = collection_name or settings.MILVUS_COLLECTION
    if client.has_collection(name):
        client.drop_collection(name)
