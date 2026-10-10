import pytest
from app.services.log_analyzer import _classify_error, _extract_error_lines, receive_pushed_logs, _pushed_logs

def test_classify_error():
    assert _classify_error("This is an exception") == "error"
    assert _classify_error("connection refused by peer") == "connection_error"
    assert _classify_error("normal log line") is None

def test_extract_error_lines():
    log_text = """INFO: starting up
ERROR: connection refused
WARN: retrying
FATAL: out of memory
INFO: shutting down"""
    errors = _extract_error_lines(log_text, max_lines=20)
    assert len(errors) == 2
    assert errors[0]["type"] in ("error", "connection_error")
    assert errors[1]["type"] in ("error", "memory_error")

def test_receive_pushed_logs():
    service = "test_service"
    lines = ["log 1", "error log 2"]
    receive_pushed_logs(service, lines)
    assert service in _pushed_logs
    assert "log 1" in _pushed_logs[service]
    assert "error log 2" in _pushed_logs[service]
