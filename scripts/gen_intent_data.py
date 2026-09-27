"""生成意图分类训练数据：少量人工种子 + LLM 扩增。

用法（项目根目录）:
    python -m uv run python scripts/gen_intent_data.py
产出 data/finetune/intents.jsonl，每行 {"text": ..., "label": ...}
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_core.messages import HumanMessage

from app.services import llm
from app.services.intent import INTENT_ROUTE

OUT_PATH = Path(__file__).resolve().parents[1] / "data" / "finetune" / "intents.jsonl"

SEEDS: dict[str, list[str]] = {
    "运费咨询": ["运费多少钱", "满多少包邮", "偏远地区要加钱吗", "运费怎么算的", "港澳台能发货吗"],
    "商品咨询": ["这个耳机有白色吗", "杯子容量多大", "键盘是什么轴的", "有没有优惠", "这个有货吗"],
    "支付问题": ["支持花呗吗", "能用微信支付吗", "支付失败但扣钱了", "可以货到付款吗", "能分期吗"],
    "发票问题": ["可以开发票吗", "怎么开专票", "电子发票发到哪", "发票能改抬头吗",
                 "开票要加钱吗"],
    "订单查询": ["帮我查订单 1001", "我的订单到哪了", "订单 888 什么状态",
                 "昨天买的发货没", "查一下我的订单"],
    "物流查询": ["物流怎么不动了", "运单号是多少", "什么时候能到", "快递到哪个城市了",
                 "签收但没收到"],
    "退换货": ["怎么退货", "七天无理由怎么走", "能换货吗", "退货邮费谁出", "买错了想退"],
    "售后投诉": ["客服态度太差了", "我要投诉", "东西坏了怎么办", "保修期内能修吗", "一直没人处理"],
    "其他": ["你好", "在吗", "你是谁", "谢谢", "今天天气不错"],
}

_PROMPT = """你是电商客服的数据标注员。围绕"客服意图：{intent}"，写出 30 条用户可能说的\
口语化问法，尽量多样（不同说法、有长有短）。每行一条，不要编号，不要标点之外的解释。"""


def _clean(line: str) -> str:
    return line.strip().lstrip("-•.、0123456789 ").strip()


def generate(per_class: int = 45) -> list[dict]:
    rows: list[dict] = []
    for intent in INTENT_ROUTE:
        rows.extend({"text": text, "label": intent} for text in SEEDS.get(intent, []))
        try:
            text = llm.chat([HumanMessage(content=_PROMPT.format(intent=intent))])
        except Exception as exc:  # noqa: BLE001  扩增失败不致命，种子仍在
            print(f"[gen] {intent} 扩增失败: {exc}")
            continue
        added = 0
        for line in text.splitlines():
            candidate = _clean(line)
            if 2 <= len(candidate) <= 40:
                rows.append({"text": candidate, "label": intent})
                added += 1
                if added >= per_class:
                    break
        print(f"[gen] {intent}: 种子 {len(SEEDS.get(intent, []))} + 扩增 {added}")

    # 去重
    seen: set[str] = set()
    unique: list[dict] = []
    for row in rows:
        if row["text"] not in seen:
            seen.add(row["text"])
            unique.append(row)
    return unique


def main() -> None:
    data = generate()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as f:
        for row in data:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"[gen] 共 {len(data)} 条 -> {OUT_PATH}")


if __name__ == "__main__":
    main()
