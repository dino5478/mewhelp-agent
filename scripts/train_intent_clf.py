"""微调 RoBERTa 意图分类器（CPU 可跑）。

不用 transformers 的 Trainer（在这个环境下会卡住），手写训练循环，简单可控。
用法（项目根目录）:
    python -m uv run python scripts/train_intent_clf.py
产物在 models/intent_clf（已被 .gitignore 忽略）。
"""

import json
import random
import sys
import time
from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.intent import INTENT_ROUTE  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "finetune" / "intents.jsonl"
OUT_DIR = ROOT / "models" / "intent_clf"
BASE_MODEL = "hfl/chinese-roberta-wwm-ext"

LABELS = list(INTENT_ROUTE.keys())
LABEL2ID = {label: i for i, label in enumerate(LABELS)}
MAX_LEN = 32
BATCH = 16
EPOCHS = 3


def _load_rows() -> list[dict]:
    lines = DATA_PATH.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def _encode(texts, labels, tokenizer):
    enc = tokenizer(texts, padding=True, truncation=True, max_length=MAX_LEN,
                    return_tensors="pt")
    enc["labels"] = torch.tensor(labels)
    return enc


def _evaluate(model, val_enc) -> float:
    model.eval()
    with torch.no_grad():
        logits = model(**{k: v for k, v in val_enc.items() if k != "labels"}).logits
    preds = logits.argmax(dim=-1)
    return float((preds == val_enc["labels"]).float().mean())


def main() -> None:
    rows = _load_rows()
    random.seed(42)
    random.shuffle(rows)
    n_val = max(1, int(len(rows) * 0.2))
    val_rows, train_rows = rows[:n_val], rows[n_val:]
    print(f"[train] total={len(rows)} train={len(train_rows)} val={len(val_rows)}", flush=True)

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(
        BASE_MODEL,
        num_labels=len(LABELS),
        id2label={i: label for label, i in LABEL2ID.items()},
        label2id=LABEL2ID,
    )

    train_enc = _encode([r["text"] for r in train_rows],
                        [LABEL2ID[r["label"]] for r in train_rows], tokenizer)
    val_enc = _encode([r["text"] for r in val_rows],
                      [LABEL2ID[r["label"]] for r in val_rows], tokenizer)

    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-5)
    n = len(train_rows)
    for epoch in range(1, EPOCHS + 1):
        model.train()
        order = torch.randperm(n)
        running = 0.0
        start = time.time()
        for i in range(0, n, BATCH):
            idx = order[i:i + BATCH]
            batch = {k: v[idx] for k, v in train_enc.items()}
            out = model(**batch)
            optimizer.zero_grad()
            out.loss.backward()
            optimizer.step()
            running += float(out.loss)
        acc = _evaluate(model, val_enc)
        print(
            f"[train] epoch {epoch}/{EPOCHS} loss={running:.3f} "
            f"val_acc={acc:.3f} ({time.time() - start:.0f}s)",
            flush=True,
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(OUT_DIR)
    tokenizer.save_pretrained(OUT_DIR)
    (OUT_DIR / "labels.json").write_text(json.dumps(LABELS, ensure_ascii=False), encoding="utf-8")
    print(f"[train] saved -> {OUT_DIR}", flush=True)


if __name__ == "__main__":
    main()
