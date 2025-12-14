from __future__ import annotations

from app.handlers import execute_handler


def test_call_external_service_mock(monkeypatch):
    # Avoid actual sleep during test
    monkeypatch.setattr("time.sleep", lambda *_: None)
    monkeypatch.setattr("random.uniform", lambda a, b: 0)

    output = execute_handler(
        "exec",
        "node",
        "call_external_service",
        {"url": "http://example.test"},
        graph=None,
    )
    assert output["status"] == "ok"
    assert output["url"] == "http://example.test"
    assert output["data"]["mock"] is True
