"""可观测测试：本地链路落库 + 无 key 时 Langfuse 降级。"""

from app.database import SessionLocal
from app.models import AuditLog
from app.services import observability


def test_record_and_fetch_trace() -> None:
    request_id = observability.new_request_id()
    observability.record_span(request_id, None, node="preprocess", latency_ms=5)
    observability.record_span(request_id, None, tool="get_order")

    db = SessionLocal()
    try:
        spans = observability.fetch_trace(db, request_id)
        assert len(spans) == 2
        assert spans[0].node == "preprocess"
        recent = observability.recent_traces(db)
        assert any(item["request_id"] == request_id for item in recent)
        db.query(AuditLog).filter(AuditLog.request_id == request_id).delete()
        db.commit()
    finally:
        db.close()


def test_langfuse_disabled_without_keys(monkeypatch) -> None:
    monkeypatch.setattr(observability, "_langfuse_inited", False)
    monkeypatch.setattr(observability, "_langfuse_handler", None)
    monkeypatch.setattr(observability.settings, "LANGFUSE_PUBLIC_KEY", "")
    monkeypatch.setattr(observability.settings, "LANGFUSE_SECRET_KEY", "")
    assert observability.get_langfuse_handler() is None
