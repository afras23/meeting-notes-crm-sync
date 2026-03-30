"""
Health and metrics endpoints.

Provides liveness and basic operational metrics (including AI cost tracking).
"""

# Standard library
from __future__ import annotations

from datetime import UTC, datetime

# Third party
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings

# Local
from app.dependencies import (
    get_action_repo,
    get_ai_client,
    get_crm_sync_repo,
    get_db_session,
    get_meeting_repo,
    get_notification_repo,
)
from app.repositories.action_item_repository import ActionItemRepository
from app.repositories.crm_sync_repository import CrmSyncRepository
from app.repositories.meeting_repository import MeetingRepository
from app.repositories.notification_repository import NotificationRepository
from app.services.ai.client import AIClient

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, object]:
    """Basic liveness check."""

    return {"status": "healthy", "timestamp": datetime.now(UTC).isoformat()}


@router.get("/metrics")
async def metrics(
    session: AsyncSession = Depends(get_db_session),
    meeting_repo: MeetingRepository = Depends(get_meeting_repo),
    action_repo: ActionItemRepository = Depends(get_action_repo),
    crm_sync_repo: CrmSyncRepository = Depends(get_crm_sync_repo),
    notification_repo: NotificationRepository = Depends(get_notification_repo),
    ai_client: AIClient = Depends(get_ai_client),
) -> dict[str, object]:
    """Expose real operational metrics derived from repositories."""

    meetings_processed_today = await meeting_repo.count_processed_today(session)
    actions_created_today = await action_repo.count_created_today(session)
    actions_pending = await action_repo.count_pending(session)
    actions_overdue = await action_repo.count_overdue(session)
    crm_syncs_today = await crm_sync_repo.count_today(session)
    notifications_sent_today = await notification_repo.count_today(session)
    cost_today_usd = await meeting_repo.cost_today_usd(session)
    avg_processing_ms = await meeting_repo.avg_processing_ms_today(session)
    settings = get_settings()

    return {
        "meetings_processed_today": meetings_processed_today,
        "actions_created_today": actions_created_today,
        "actions_pending": actions_pending,
        "actions_overdue": actions_overdue,
        "crm_syncs_today": crm_syncs_today,
        "crm_sync_failures_today": 0,
        "notifications_sent_today": notifications_sent_today,
        "cost_today_usd": round(cost_today_usd, 2),
        "cost_limit_usd": settings.cost_limit_usd,
        "avg_processing_ms": round(avg_processing_ms, 1),
    }


@router.get("/health/ready")
async def ready(
    session: AsyncSession = Depends(get_db_session),
    ai_client: AIClient = Depends(get_ai_client),
) -> dict[str, object]:
    """Readiness check for DB and AI provider reachability."""

    checks: dict[str, object] = {}
    degraded = False

    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:  # pragma: no cover
        degraded = True
        checks["database"] = f"error: {type(e).__name__}"

    try:
        ok = await ai_client.ping()
        checks["ai_provider"] = "ok" if ok else "unreachable"
        degraded = degraded or not ok
    except Exception as e:  # pragma: no cover
        degraded = True
        checks["ai_provider"] = f"error: {type(e).__name__}"

    if degraded:
        return {"status": "degraded", "checks": checks}
    return {"status": "ready"}
