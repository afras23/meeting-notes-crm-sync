"""
Correlation ID middleware.

Reads X-Correlation-ID from request header or generates a UUID, stores it in contextvars,
adds to response headers, and ensures logs include it via JsonFormatter.
"""

# Standard library
from __future__ import annotations

from collections.abc import Awaitable, Callable
from uuid import uuid4

# Third party
from fastapi import Request, Response

# Local
from app.core.constants import CORRELATION_ID_HEADER
from app.core.logging import correlation_id_ctx, get_correlation_id_from_headers


async def correlation_id_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    incoming_headers = {k.lower(): v for k, v in request.headers.items()}
    correlation_id = get_correlation_id_from_headers(incoming_headers) or str(uuid4())
    token = correlation_id_ctx.set(correlation_id)
    try:
        response = await call_next(request)
        response.headers[CORRELATION_ID_HEADER] = correlation_id
        return response
    finally:
        correlation_id_ctx.reset(token)
