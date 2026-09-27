"""前置处理：指代消解 + 意图识别。

用户常说不完整的话（"那它能退吗"），得结合上文补全，再判断意图。
一次 LLM 调用同时干这两件事，省一轮开销。
"""

from langchain_core.messages import HumanMessage, SystemMessage

from app.services import llm

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


def _format_history(history: list[dict]) -> str:
    recent = history[-4:]  # 只看最近几轮，多了反而干扰
    if not recent:
        return "（无）"
    lines = []
    for item in recent:
        role = "用户" if item.get("role") == "user" else "客服"
        lines.append(f"{role}: {item.get('content', '')}")
    return "\n".join(lines)


def analyze(message: str, history: list[dict] | None = None) -> dict:
    """返回 {standalone_query, intent, route}。intent 不认识时归到"其他"。"""
    user_prompt = f"最近对话：\n{_format_history(history or [])}\n\n用户当前句：{message}"

    data = llm.chat_json(
        [SystemMessage(content=_SYSTEM_PROMPT), HumanMessage(content=user_prompt)]
    )

    standalone = str(data.get("standalone_query") or message).strip()
    intent = str(data.get("intent") or "其他").strip()
    if intent not in INTENT_ROUTE:
        intent = "其他"

    return {"standalone_query": standalone, "intent": intent, "route": INTENT_ROUTE[intent]}
