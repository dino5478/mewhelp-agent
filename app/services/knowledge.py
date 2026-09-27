"""知识入库：把一段文本切块、向量化，写进 MySQL + Milvus。

建库脚本和运营回写共用这一份逻辑。
"""

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import KnowledgeChunk, KnowledgeDoc
from app.services import embedding, milvus_store
from app.services.chunking import split_markdown


def ingest_document(db: Session, title: str, text: str, source: str = "manual") -> int:
    """入库一个文档，返回切块数。集合是追加，不会清空已有数据。"""
    client = milvus_store.get_client()
    collection = milvus_store.ensure_collection(client)

    doc = KnowledgeDoc(title=title, source=source)
    db.add(doc)
    db.commit()
    db.refresh(doc)

    chunks = split_markdown(text, max_chars=settings.RAG_CHUNK_SIZE)
    for index, chunk in enumerate(chunks):
        db.add(
            KnowledgeChunk(
                doc_id=doc.id,
                chunk_index=index,
                heading_path=chunk.heading_path,
                content=chunk.content,
            )
        )
    db.commit()

    saved = (
        db.query(KnowledgeChunk)
        .filter_by(doc_id=doc.id)
        .order_by(KnowledgeChunk.chunk_index)
        .all()
    )
    if not saved:
        return 0

    vectors = embedding.embed_texts([c.content for c in saved])
    rows = []
    for chunk, vector in zip(saved, vectors):
        milvus_id = f"{doc.id}-{chunk.chunk_index}"
        chunk.milvus_id = milvus_id
        rows.append(
            {
                "id": milvus_id,
                "dense": vector,
                "text": chunk.content,
                "heading_path": chunk.heading_path,
                "doc_id": doc.id,
                "source": source,
            }
        )
    db.commit()
    client.insert(collection_name=collection, data=rows)
    return len(rows)
