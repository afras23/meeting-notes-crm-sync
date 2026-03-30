"""
Request logging middleware.

Logs method/path/status/latency and correlation_id for every request.
Does not log request bodies.
"""

# Standard library
from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

# Third party
from fastapi import Request, Response

# Local
from app.core.logging import correlation_id_ctx

logger = logging.getLogger(__name__)


async def request_logging_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    start = time.monotonic()
    response: Response
    try:
        response = await call_next(request)
    except Exception:
        latency_ms = (time.monotonic() - start) * 1000.0
        cid = correlation_id_ctx.get()
        logger.error(
            "Request failed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": 500,
                "latency_ms": round(latency_ms, 1),
                "correlation_id": cid,
            },
        )
        raise

    latency_ms = (time.monotonic() - start) * 1000.0
    cid = correlation_id_ctx.get()
    status_code = getattr(response, "status_code", 0)
    payload: dict[str, Any] = {
        "method": request.method,
        "path": request.url.path,
        "status_code": status_code,
        "latency_ms": round(latency_ms, 1),
        "correlation_id": cid,
    }
    if 200 <= status_code < 400:
        logger.info("Request completed", extra=payload)
    elif 400 <= status_code < 500:
        logger.warning("Request completed", extra=payload)
    else:
        logger.error("Request completed", extra=payload)
    return response
