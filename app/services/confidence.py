"""置信度闸门：生成答案前先判断"证据够不够"。

两道关卡：
1. 没检索到东西 -> 直接判不可信；
2. 重排分够高 -> 放行；分不够再让 LLM 看一眼资料，自评能不能回答。
宁可说"不知道"，也别让模型一本正经地编。
"""

from langchain_core.messages import HumanMessage

from app.core.config import settings
from app.services import llm

_SELF_EVAL_PROMPT = """你是审核员。判断下面的资料能否回答用户问题。

资料：
{context}

问题：{question}

只输出 JSON：{{"answerable": "yes" 或 "no"}}，不要解释。"""


def judge(question: str, context: str, top_score: float) -> tuple[bool, str]:
    """返回 (是否可信, 原因)。原因便于排查和进问题池。"""
    if not context.strip():
        return False, "no_context"

    if top_score >= settings.CONFIDENCE_SCORE_THRESHOLD:
        return True, "high_score"

    if not settings.CONFIDENCE_SELF_EVAL:
        return False, "low_score"

    try:
        verdict = llm.chat_json([
            HumanMessage(content=_SELF_EVAL_PROMPT.format(context=context, question=question))
        ])
    except Exception:  # noqa: BLE001  自评失败就保守判不可信
        return False, "self_eval_error"

    answerable = str(verdict.get("answerable", "no")).strip().lower()
    return (answerable == "yes"), ("self_eval_yes" if answerable == "yes" else "self_eval_no")
