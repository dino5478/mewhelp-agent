"""建库脚本：知识文档 -> 切块 -> 存 MySQL -> 向量化 -> 存 Milvus。

用法（项目根目录）:
    python -m uv run python scripts/build_index.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.database import SessionLocal
from app.models import KnowledgeChunk, KnowledgeDoc
from app.services import embedding, milvus_store
from app.services.chunking import split_markdown

KNOWLEDGE_DIR = Path(__file__).resolve().parents[1] / "data" / "knowledge"


def build_index(recreate: bool = True) -> int:
    client = milvus_store.get_client()
    collection = milvus_store.ensure_collection(client, recreate=recreate)

    db = SessionLocal()
    try:
        if recreate:
            db.query(KnowledgeChunk).delete()
            db.query(KnowledgeDoc).delete()
            db.commit()

        rows: list[dict] = []
        for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            doc = KnowledgeDoc(title=path.stem, source=path.name)
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
            vectors = embedding.embed_texts([c.content for c in saved])
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
                        "source": path.name,
                    }
                )
            db.commit()
            print(f"[build] {path.name}: {len(saved)} chunks")

        if rows:
            client.insert(collection_name=collection, data=rows)

        print(f"[build] done. collection={collection}, chunks={len(rows)}")
        return len(rows)
    finally:
        db.close()


if __name__ == "__main__":
    build_index()
