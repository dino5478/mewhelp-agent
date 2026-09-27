"""LLM 客户端的离线测试：只测 JSON 解析，不真调模型。"""

import pytest

from app.core.exceptions import AppException
from app.services import llm


def test_extract_plain_json() -> None:
    assert llm.extract_json('{"intent": "运费"}') == {"intent": "运费"}


def test_extract_json_from_code_fence() -> None:
    text = '好的，结果如下：\n```json\n{"intent": "退款", "order_id": 1001}\n```'
    assert llm.extract_json(text) == {"intent": "退款", "order_id": 1001}


def test_extract_json_with_surrounding_text() -> None:
    assert llm.extract_json('前面 { "a": 1 } 后面') == {"a": 1}


def test_extract_json_bad_raises() -> None:
    with pytest.raises(AppException):
        llm.extract_json("这里没有 JSON")
