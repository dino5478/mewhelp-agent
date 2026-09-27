"""检索评测：4 方案对照，输出 Recall@5 / Recall@10 / MRR。

用法（需先 build_index，且配置好 EMBEDDING_API_KEY）:
    python -m uv run python scripts/eval_retrieval.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import retrieval

EVAL_PATH = Path(__file__).resolve().parents[1] / "data" / "eval" / "retrieval_eval.jsonl"

SCHEMES: dict[str, dict] = {
    "dense_only": {"use_dense": True, "use_sparse": False, "use_rerank": False},
    "sparse_only": {"use_dense": False, "use_sparse": True, "use_rerank": False},
    "hybrid": {"use_dense": True, "use_sparse": True, "use_rerank": False},
    "hybrid+rerank": {"use_dense": True, "use_sparse": True, "use_rerank": True},
}


def load_eval() -> list[dict]:
    entries = []
    for line in EVAL_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            entries.append(json.loads(line))
    return entries


def _is_relevant(text: str, gold: list[str]) -> bool:
    return any(keyword in text for keyword in gold)


def evaluate(entries: list[dict], top_k: int = 10, recall_n: int = 20, **scheme) -> dict:
    recall5 = recall10 = 0
    mrr = 0.0
    for entry in entries:
        results = retrieval.hybrid_search(
            entry["query"], top_k=top_k, recall_n=recall_n, **scheme
        )
        ranks = [i for i, r in enumerate(results, start=1) if _is_relevant(r.text, entry["gold"])]
        if ranks:
            if ranks[0] <= 5:
                recall5 += 1
            if ranks[0] <= 10:
                recall10 += 1
            mrr += 1.0 / ranks[0]
    n = len(entries)
    return {"Recall@5": recall5 / n, "Recall@10": recall10 / n, "MRR": mrr / n}


def main() -> None:
    entries = load_eval()
    print(f"eval queries: {len(entries)}")
    print(f"{'scheme':<16}{'Recall@5':>10}{'Recall@10':>11}{'MRR':>8}")
    for name, scheme in SCHEMES.items():
        metrics = evaluate(entries, **scheme)
        print(
            f"{name:<16}{metrics['Recall@5']:>10.3f}"
            f"{metrics['Recall@10']:>11.3f}{metrics['MRR']:>8.3f}"
        )


if __name__ == "__main__":
    main()
