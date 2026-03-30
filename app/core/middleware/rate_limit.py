"""
Basic in-memory rate limiting middleware.

Configurable requests-per-minute; intended for demos/tests (not production).
"""

# Standard library
from __future__ import annotations

import time
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

# Third party
from fastapi import Request, Response

# Local
from app.core.exceptions import AppError


class TooManyRequests(AppError):
    def __init__(self, *, retry_after_seconds: float) -> None:
        super().__init__(
            "Too many requests.",
            error_code="TOO_MANY_REQUESTS",
            context={"retry_after_seconds": retry_after_seconds},
        )


@dataclass
class _Bucket:
    hits: deque[float] = field(default_factory=deque)


class RateLimiter:
    def __init__(self, *, requests_per_minute: int) -> None:
        self._rpm = max(1, int(requests_per_minute))
        self._window_seconds = 60.0
        self._buckets: dict[str, _Bucket] = {}

    def check(self, key: str) -> None:
        now = time.monotonic()
        bucket = self._buckets.setdefault(key, _Bucket())
        while bucket.hits and now - bucket.hits[0] > self._window_seconds:
            bucket.hits.popleft()
        if len(bucket.hits) >= self._rpm:
            retry_after = self._window_seconds - (now - bucket.hits[0])
            raise TooManyRequests(retry_after_seconds=max(0.1, retry_after))
        bucket.hits.append(now)


def _client_key(request: Request) -> str:
    host = request.client.host if request.client else "unknown"
    return host


def build_rate_limit_middleware(*, limiter: RateLimiter, enabled: bool = True) -> Any:
    async def middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if not enabled:
            return await call_next(request)
        # Don't rate limit readiness/health/metrics.
        path = request.url.path
        if path.endswith(("/health", "/health/ready", "/metrics")):
            return await call_next(request)
        limiter.check(_client_key(request))
        return await call_next(request)

    return middleware
