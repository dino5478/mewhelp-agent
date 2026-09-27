"""前置处理：指代消解 + 意图识别。

意图识别有两条路：
- llm（默认）：一次调用同时做 coref 和 intent；
- local：用微调好的本地分类器判意图，coref 仍走一次轻量 LLM。
通过 settings.INTENT_BACKEND 切换；本地模型不存在时自动回退到 llm。
"""

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import settings
from app.services import intent_clf, llm

# 9 类意图 -> 4 个处理出口。出口决定图里往哪条分支走。
INTENT_ROUTE: dict[str, str] = {
    "运费咨询": "faq",
    "商品咨询": "faq",
    "支付问题": "faq",
    "发票问题": "faq",
    "订单查询": "order",
    "物流查询": "order",
    "退换货": "aftersale",
    "售后投诉": "aftersale",
    "其他": "agent",
}

_SYSTEM_PROMPT = """你是电商客服系统的前置理解模块。请完成两件事：

1. 指代消解：结合最近几轮对话，把用户当前这句话补成一句"脱离上下文也能看懂"的完整问题。
   如果当前这句话本身已经完整，就原样返回。
2. 意图识别：从下面 9 个类别里选一个最贴切的：
   运费咨询、商品咨询、支付问题、发票问题、订单查询、物流查询、退换货、售后投诉、其他

只输出 JSON，不要解释：
{"standalone_query": "补全后的完整问题", "intent": "类别"}

示例：
用户上一句：订单 1001 是什么情况
用户当前句：那它能退吗
输出：{"standalone_query": "订单 1001 能不能退货", "intent": "退换货"}"""

_COREF_PROMPT = """结合最近几轮对话，把用户当前这句话补成一句独立、完整的问题。\
已经完整就原样返回。只输出这句话本身，不要解释。"""


def _format_history(history: list[dict]) -> str:
    recent = history[-4:]  # 只看最近几轮，多了反而干扰
    if not recent:
        return "（无）"
    lines = []
    for item in recent:
        role = "用户" if item.get("role") == "user" else "客服"
        lines.append(f"{role}: {item.get('content', '')}")
    return "\n".join(lines)


def _context_block(history: list[dict] | None, summary: str) -> str:
    parts = []
    if summary:
        parts.append(f"更早对话摘要：{summary}")
    parts.append(f"最近对话：\n{_format_history(history or [])}")
    return "\n\n".join(parts)


def _to_route(intent: str) -> str:
    return INTENT_ROUTE.get(intent, "agent")


def _llm_analyze(message: str, history: list[dict] | None, summary: str) -> dict:
    user_prompt = f"{_context_block(history, summary)}\n\n用户当前句：{message}"
    data = llm.chat_json(
        [SystemMessage(content=_SYSTEM_PROMPT), HumanMessage(content=user_prompt)]
    )
    standalone = str(data.get("standalone_query") or message).strip()
    intent = str(data.get("intent") or "其他").strip()
    if intent not in INTENT_ROUTE:
        intent = "其他"
    return {"standalone_query": standalone, "intent": intent, "route": _to_route(intent)}


def _local_analyze(message: str, history: list[dict] | None, summary: str) -> dict:
    try:
        intent = intent_clf.classify(message)
    except Exception:  # noqa: BLE001  分类器出问题就退回 LLM
        return _llm_analyze(message, history, summary)
    if intent not in INTENT_ROUTE:
        intent = "其他"

    standalone = message
    if history or summary:
        try:
            context = _context_block(history, summary)
            text = llm.chat([
                SystemMessage(content=_COREF_PROMPT),
                HumanMessage(content=f"{context}\n\n用户当前句：{message}"),
            ])
            standalone = text.strip() or message
        except Exception:  # noqa: BLE001  coref 失败也能用原句继续
            standalone = message
    return {"standalone_query": standalone, "intent": intent, "route": _to_route(intent)}


def analyze(message: str, history: list[dict] | None = None, summary: str = "") -> dict:
    """返回 {standalone_query, intent, route}。"""
    if settings.INTENT_BACKEND == "local" and intent_clf.is_available():
        return _local_analyze(message, history, summary)
    return _llm_analyze(message, history, summary)
