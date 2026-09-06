"""Structured JSON logging and request correlation without query-body logging."""

from __future__ import annotations

import contextvars
import datetime as dt
import json
import logging
import sys
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request, Response

from hr_policy_rag.config import Settings

_request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)


class JsonFormatter(logging.Formatter):
    """Emit a stable JSON log envelope suitable for Cloud Logging ingestion."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": dt.datetime.now(dt.UTC).isoformat(),
            "severity": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event", "application_log"),
            "message": record.getMessage(),
        }
        request_id = _request_id.get()
        if request_id:
            payload["request_id"] = request_id
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_logging(settings: Settings) -> None:
    """Configure the root logger once for the current process."""

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.log_level)


def normalize_request_id(value: str | None, *, max_length: int) -> str:
    """Accept a conservative caller correlation ID or generate a UUID."""

    if value and len(value) <= max_length and all(character.isalnum() or character in "-_." for character in value):
        return value
    return str(uuid.uuid4())


def request_id_middleware(
    settings: Settings,
) -> Callable[[Request, Callable[[Request], Awaitable[Response]]], Awaitable[Response]]:
    async def middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        request_id = normalize_request_id(
            request.headers.get(settings.request_id_header),
            max_length=settings.max_request_id_length,
        )
        token = _request_id.set(request_id)
        try:
            response = await call_next(request)
            response.headers[settings.request_id_header] = request_id
            return response
        finally:
            _request_id.reset(token)

    return middleware
