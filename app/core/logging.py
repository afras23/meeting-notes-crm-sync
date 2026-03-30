"""
Structured logging setup.

Configures JSON-style logs and request correlation IDs for observability.
"""

# Standard library
from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

# Local
from app.core.constants import CORRELATION_ID_HEADER

correlation_id_ctx: ContextVar[str | None] = ContextVar("correlation_id", default=None)


class JsonFormatter(logging.Formatter):
    """Render log records as JSON with stable fields."""

    def format(self, record: logging.LogRecord) -> str:
        correlation_id = correlation_id_ctx.get()
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if correlation_id:
            payload["correlation_id"] = correlation_id

        if isinstance(record.args, dict) and record.args:
            payload.update(record.args)

        extra = getattr(record, "extra", None)
        if isinstance(extra, dict):
            payload.update(extra)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


def configure_logging(*, log_level: str) -> None:
    """
    Configure root logging handlers and format.

    Args:
        log_level: Logging level string.
    """

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level.upper())

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    logging.getLogger("uvicorn.access").disabled = True


def get_correlation_id_from_headers(headers: dict[str, str]) -> str | None:
    """Extract correlation ID from incoming headers (if present)."""

    return headers.get(CORRELATION_ID_HEADER)
