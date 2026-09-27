"""大模型客户端。

统一走这里调 LLM，业务代码不直接碰 SDK。两个入口：
- chat()：普通对话，返回文本
- chat_json()：要求模型输出 JSON，解析成 dict（意图识别要用）
"""

import json
import re

from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.core.exceptions import AppException


def get_llm(temperature: float = 0.0) -> ChatOpenAI:
    """每次新建一个轻量客户端即可，不用缓存（构造开销很低）。"""
    if not settings.LLM_API_KEY:
        raise AppException("未配置 LLM_API_KEY", 500, "config_error")
    return ChatOpenAI(
        model=settings.LLM_MODEL,
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        temperature=temperature,
        timeout=settings.LLM_TIMEOUT,
    )


def chat(messages: list[BaseMessage], temperature: float = 0.0) -> str:
    result = get_llm(temperature).invoke(messages)
    return result.content if isinstance(result.content, str) else str(result.content)


def extract_json(text: str) -> dict:
    """从模型输出里抠出 JSON 对象。

    模型有时会带 ```json 代码块或前后废话，这里做兼容；实在解析不出就报错。
    """
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # 退一步：截取第一个花括号到最后一个花括号
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                pass
    raise AppException("模型未返回合法 JSON", 500, "llm_bad_json")


def chat_json(messages: list[BaseMessage], temperature: float = 0.0) -> dict:
    raw = get_llm(temperature).invoke(messages)
    content = raw.content if isinstance(raw.content, str) else str(raw.content)
    return extract_json(content)
