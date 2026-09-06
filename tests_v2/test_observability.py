from __future__ import annotations

import json
import logging

from hr_policy_rag.observability import JsonFormatter, normalize_request_id


def test_json_formatter_emits_queryable_envelope() -> None:
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="started",
        args=(),
        exc_info=None,
    )
    record.event = "test_started"
    payload = json.loads(JsonFormatter().format(record))
    assert payload["severity"] == "INFO"
    assert payload["event"] == "test_started"
    assert payload["message"] == "started"
    assert "timestamp" in payload


def test_request_id_validation_rejects_log_injection() -> None:
    request_id = normalize_request_id("value\nforged-log=true", max_length=128)
    assert request_id != "value\nforged-log=true"
    assert "\n" not in request_id
