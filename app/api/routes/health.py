"""
Health and metrics endpoints.

Provides liveness and basic operational metrics (including AI cost tracking).
"""

# Standard library
from __future__ import annotations

from datetime import UTC, datetime

# Third party
from fastapi import APIRouter, Depends

# Local
from app.dependencies import get_ai_client
from app.services.ai.client import AIClient

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, object]:
    """Basic liveness check."""

    return {"status": "healthy", "timestamp": datetime.now(UTC).isoformat()}


@router.get("/metrics")
async def metrics(ai_client: AIClient = Depends(get_ai_client)) -> dict[str, object]:
    """Expose minimal operational metrics."""

    return {
        "ai": {
            "today_usd": ai_client.daily_cost_usd,
            "request_count": ai_client.request_count,
            "limit_usd": ai_client.max_daily_cost_usd,
        }
    }
