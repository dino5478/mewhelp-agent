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


def test_local_backend_uses_classifier(monkeypatch) -> None:
    monkeypatch.setattr(intent.settings, "INTENT_BACKEND", "local")
    monkeypatch.setattr(intent.intent_clf, "is_available", lambda: True)
    monkeypatch.setattr(intent.intent_clf, "classify", lambda text: "订单查询")
    # 无历史时不调 LLM，standalone 用原句
    called = {"llm": False}
    monkeypatch.setattr(intent.llm, "chat_json", lambda msgs: called.update(llm=True) or {})
    result = intent.analyze("帮我看下订单")
    assert result["intent"] == "订单查询"
    assert result["route"] == "order"
    assert result["standalone_query"] == "帮我看下订单"


def test_local_backend_falls_back_when_model_missing(monkeypatch) -> None:
    monkeypatch.setattr(intent.settings, "INTENT_BACKEND", "local")
    monkeypatch.setattr(intent.intent_clf, "is_available", lambda: False)
    monkeypatch.setattr(
        intent.llm, "chat_json",
        lambda msgs: {"standalone_query": "运费多少", "intent": "运费咨询"},
    )
    result = intent.analyze("运费多少")
    assert result["route"] == "faq"
