"""本地意图分类器：加载微调好的 RoBERTa，做单句意图分类。

模型不存在时 is_available() 返回 False，调用方回退到 LLM。
重依赖（torch/transformers）只在真正用到时才导入，避免主应用被拖进来。
"""

import json
from pathlib import Path

from app.core.config import settings

_model = None
_tokenizer = None
_labels: list[str] = []


def is_available() -> bool:
    return Path(settings.INTENT_CLF_PATH).is_dir()


def _load() -> None:
    global _model, _tokenizer, _labels
    if _model is not None:
        return
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    path = settings.INTENT_CLF_PATH
    _tokenizer = AutoTokenizer.from_pretrained(path)
    _model = AutoModelForSequenceClassification.from_pretrained(path)
    _model.eval()
    _labels = json.loads((Path(path) / "labels.json").read_text(encoding="utf-8"))


def classify(text: str) -> str:
    """返回意图标签。调用方需先用 is_available() 判断。"""
    import torch

    _load()
    enc = _tokenizer(text, truncation=True, max_length=32, return_tensors="pt")
    with torch.no_grad():
        logits = _model(**enc).logits
    return _labels[int(logits.argmax(dim=-1))]
