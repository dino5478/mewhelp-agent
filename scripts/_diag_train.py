import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

print("torch threads:", torch.get_num_threads(), flush=True)
t0 = time.time()
tok = AutoTokenizer.from_pretrained("hfl/chinese-roberta-wwm-ext")
print("tokenizer loaded", round(time.time() - t0, 1), flush=True)

t0 = time.time()
model = AutoModelForSequenceClassification.from_pretrained(
    "hfl/chinese-roberta-wwm-ext", num_labels=9
)
print("model loaded", round(time.time() - t0, 1), flush=True)

enc = tok(["运费多少钱", "帮我查订单 1001"] * 8, padding=True, truncation=True,
          max_length=32, return_tensors="pt")
labels = torch.tensor([0] * 8 + [4] * 8)
opt = torch.optim.AdamW(model.parameters(), lr=3e-5)

t0 = time.time()
out = model(**enc, labels=labels)
out.loss.backward()
opt.step()
print("one step seconds:", round(time.time() - t0, 1), flush=True)
