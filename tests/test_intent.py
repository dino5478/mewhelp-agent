"""前置处理测试：mock 掉 LLM，验证意图到出口的映射与兜底。"""

from app.services import intent


def test_analyze_maps_intent_to_route(monkeypatch) -> None:
    monkeypatch.setattr(
        intent.llm,
        "chat_json",
        lambda msgs: {"standalone_query": "订单 1001 能不能退货", "intent": "退换货"},
    )
    result = intent.analyze("那它能退吗", history=[{"role": "user", "content": "订单 1001"}])
    assert result["standalone_query"] == "订单 1001 能不能退货"
    assert result["route"] == "aftersale"


def test_unknown_intent_falls_back(monkeypatch) -> None:
    monkeypatch.setattr(
        intent.llm,
        "chat_json",
        lambda msgs: {"standalone_query": "你好", "intent": "外星语"},
    )
    result = intent.analyze("你好")
    assert result["intent"] == "其他"
    assert result["route"] == "agent"


def test_missing_standalone_falls_back_to_message(monkeypatch) -> None:
    monkeypatch.setattr(intent.llm, "chat_json", lambda msgs: {"intent": "运费咨询"})
    result = intent.analyze("运费多少")
    assert result["standalone_query"] == "运费多少"
    assert result["route"] == "faq"
