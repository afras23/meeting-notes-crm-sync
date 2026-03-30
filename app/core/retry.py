"""
Async retry helpers with bounded exponential backoff and jitter.
"""

# Standard library
from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


async def retry_async(
    fn: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    base_delay_seconds: float = 0.1,
    max_delay_seconds: float = 2.0,
) -> T:
    """
    Run ``fn`` up to ``attempts`` times on failure.

    Delay before retry i uses ``min(max_delay, base * 2**i)`` plus small jitter.
    """

    last: Exception | None = None
    for attempt in range(attempts):
        try:
            return await fn()
        except Exception as e:
            last = e
            if attempt == attempts - 1:
                break
            delay = min(max_delay_seconds, base_delay_seconds * (2**attempt))
            jitter = random.uniform(0, delay * 0.2)
            await asyncio.sleep(delay + jitter)
    assert last is not None
    raise last
