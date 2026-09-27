"""置信度闸门测试（离线）。"""

from app.core.config import settings
from app.services import confidence


def test_no_context_is_untrusted() -> None:
    ok, reason = confidence.judge("问题", "", 0.0)
    assert ok is False
    assert reason == "no_context"


def test_high_score_passes() -> None:
    ok, reason = confidence.judge("问题", "一些资料", settings.CONFIDENCE_SCORE_THRESHOLD + 0.1)
    assert ok is True
    assert reason == "high_score"


def test_low_score_self_eval_yes(monkeypatch) -> None:
    monkeypatch.setattr(confidence.llm, "chat_json", lambda msgs: {"answerable": "yes"})
    ok, reason = confidence.judge("问题", "资料", 0.0)
    assert ok is True
    assert reason == "self_eval_yes"


def test_low_score_self_eval_no(monkeypatch) -> None:
    monkeypatch.setattr(confidence.llm, "chat_json", lambda msgs: {"answerable": "no"})
    ok, reason = confidence.judge("问题", "资料", 0.0)
    assert ok is False
    assert reason == "self_eval_no"


def test_self_eval_error_is_untrusted(monkeypatch) -> None:
    def _boom(msgs):
        raise RuntimeError("api down")

    monkeypatch.setattr(confidence.llm, "chat_json", _boom)
    ok, reason = confidence.judge("问题", "资料", 0.0)
    assert ok is False
    assert reason == "self_eval_error"
