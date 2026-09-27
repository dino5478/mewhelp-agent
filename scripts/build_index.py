"""建库脚本：知识文档 -> 切块 -> 存 MySQL -> 向量化 -> 存 Milvus。

用法（项目根目录）:
    python -m uv run python scripts/build_index.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.models import KnowledgeChunk, KnowledgeDoc
from app.services import knowledge, milvus_store

KNOWLEDGE_DIR = Path(__file__).resolve().parents[1] / "data" / "knowledge"


def build_index(recreate: bool = True) -> int:
    if recreate:
        milvus_store.ensure_collection(recreate=True)
        db = SessionLocal()
        try:
            db.query(KnowledgeChunk).delete()
            db.query(KnowledgeDoc).delete()
            db.commit()
        finally:
            db.close()

    total = 0
    db = SessionLocal()
    try:
        for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            count = knowledge.ingest_document(db, title=path.stem, text=text, source=path.name)
            total += count
            print(f"[build] {path.name}: {count} chunks")
    finally:
        db.close()

    print(f"[build] done. chunks={total}")
    return total


if __name__ == "__main__":
    build_index()
