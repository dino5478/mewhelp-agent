"""知识入库测试：mock 掉向量化和向量库，只验证切块与落库。"""

import random

from app.database import SessionLocal
from app.models import KnowledgeChunk, KnowledgeDoc
from app.services import knowledge


class _FakeMilvus:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def insert(self, collection_name, data):
        self.rows.extend(data)


def test_ingest_document(monkeypatch) -> None:
    fake = _FakeMilvus()
    monkeypatch.setattr(knowledge.milvus_store, "get_client", lambda: fake)
    monkeypatch.setattr(knowledge.milvus_store, "ensure_collection", lambda client=None, **k: "kb")
    monkeypatch.setattr(
        knowledge.embedding, "embed_texts", lambda texts: [[0.1] * 1024 for _ in texts]
    )

    db = SessionLocal()
    title = f"知识{random.randint(100000, 999999)}"
    try:
        count = knowledge.ingest_document(
            db, title=title, text="# 标题\n\n## 小节\n\n这是一段测试内容。\n", source="test"
        )
        assert count >= 1
        assert len(fake.rows) == count

        doc = db.query(KnowledgeDoc).filter_by(title=title).one()
        assert db.query(KnowledgeChunk).filter_by(doc_id=doc.id).count() == count

        db.query(KnowledgeChunk).filter_by(doc_id=doc.id).delete()
        db.delete(doc)
        db.commit()
    finally:
        db.close()
