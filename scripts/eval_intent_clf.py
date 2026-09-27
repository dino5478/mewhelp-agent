"""对比意图识别两条路：本地微调分类器 vs LLM，比准确率和单条耗时。

用法（项目根目录，需已训练好模型）:
    python -m uv run python scripts/eval_intent_clf.py
"""

import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_core.messages import HumanMessage

from app.services import intent_clf, llm

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "finetune" / "intents.jsonl"

_LLM_PROMPT = """判断下面这句电商客服用户话属于哪一类：
运费咨询、商品咨询、支付问题、发票问题、订单查询、物流查询、退换货、售后投诉、其他
只输出 JSON：{{"intent": "类别"}}

用户：{text}"""


def _val_rows() -> list[dict]:
    lines = DATA_PATH.read_text(encoding="utf-8").splitlines()
    rows = [json.loads(line) for line in lines if line.strip()]
    random.seed(42)
    random.shuffle(rows)
    n_val = max(1, int(len(rows) * 0.2))
    return rows[:n_val]


def _eval_local(rows: list[dict]) -> tuple[float, float]:
    correct = 0
    start = time.perf_counter()
    for row in rows:
        if intent_clf.classify(row["text"]) == row["label"]:
            correct += 1
    elapsed = time.perf_counter() - start
    return correct / len(rows), elapsed / len(rows) * 1000


def _eval_llm(rows: list[dict]) -> tuple[float, float]:
    correct = 0
    start = time.perf_counter()
    for row in rows:
        try:
            data = llm.chat_json([HumanMessage(content=_LLM_PROMPT.format(text=row["text"]))])
            predicted = str(data.get("intent", "")).strip()
        except Exception:  # noqa: BLE001
            predicted = ""
        if predicted == row["label"]:
            correct += 1
    elapsed = time.perf_counter() - start
    return correct / len(rows), elapsed / len(rows) * 1000


def main() -> None:
    rows = _val_rows()
    print(f"val size: {len(rows)}")

    if intent_clf.is_available():
        acc, ms = _eval_local(rows)
        print(f"local (RoBERTa) : accuracy={acc:.3f}  avg_latency={ms:.0f} ms/条")
    else:
        print("local (RoBERTa) : 模型不存在，跳过（先跑 train_intent_clf.py）")

    acc, ms = _eval_llm(rows)
    print(f"LLM  (DeepSeek) : accuracy={acc:.3f}  avg_latency={ms:.0f} ms/条")


if __name__ == "__main__":
    main()
