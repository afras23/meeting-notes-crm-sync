"""
Meetings endpoints.

Provides access to stored processed meetings.
"""

# Standard library
from __future__ import annotations

# Third party
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

# Local
from app.api.schemas.envelope import ResponseMetadata, SuccessEnvelope
from app.api.schemas.meetings import (
    CrmSyncStatus,
    MeetingDetailResponse,
    MeetingListResponse,
    MeetingSummary,
)
from app.api.schemas.pagination import PageInfo, PaginatedResponse
from app.core.exceptions import NotFound
from app.core.logging import correlation_id_ctx
from app.dependencies import (
    get_action_repo,
    get_crm_sync_repo,
    get_db_session,
    get_meeting_repo,
    get_notification_repo,
)
from app.repositories.action_item_repository import ActionItemRepository
from app.repositories.crm_sync_repository import CrmSyncRepository
from app.repositories.meeting_repository import MeetingRepository
from app.repositories.notification_repository import NotificationRepository

router = APIRouter()


@router.get("/meetings", response_model=SuccessEnvelope[MeetingListResponse])
async def list_meetings(
    session: AsyncSession = Depends(get_db_session),
    meeting_repo: MeetingRepository = Depends(get_meeting_repo),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)."),
    page_size: int = Query(default=20, ge=1, le=200, description="Items per page."),
    deal_id: str | None = Query(default=None, description="Filter by deal id."),
    status: str | None = Query(default=None, description="Filter by meeting status."),
) -> SuccessEnvelope[MeetingListResponse]:
    correlation_id = correlation_id_ctx.get() or ""
    meetings = await meeting_repo.list(
        session, page=page, page_size=page_size, deal_id=deal_id, status=status
    )
    summaries = [
        MeetingSummary(
            id=m.id,
            deal_id=m.deal_id,
            title=m.title,
            occurred_at=m.occurred_at,
            confidence=m.confidence,
        )
        for m in meetings
    ]
    data = MeetingListResponse(
        meetings=PaginatedResponse(
            items=summaries, page_info=PageInfo(page=page, page_size=page_size)
        )
    )
    return SuccessEnvelope(data=data, metadata=ResponseMetadata(correlation_id=correlation_id))


@router.get("/meetings/{meeting_id}", response_model=SuccessEnvelope[MeetingDetailResponse])
async def get_meeting(
    meeting_id: str,
    session: AsyncSession = Depends(get_db_session),
    meeting_repo: MeetingRepository = Depends(get_meeting_repo),
    action_repo: ActionItemRepository = Depends(get_action_repo),
    crm_sync_repo: CrmSyncRepository = Depends(get_crm_sync_repo),
    notification_repo: NotificationRepository = Depends(get_notification_repo),
) -> SuccessEnvelope[MeetingDetailResponse]:
    correlation_id = correlation_id_ctx.get() or ""
    meeting = await meeting_repo.get(session, meeting_id)
    if meeting is None:
        raise NotFound("Meeting not found.", context={"meeting_id": meeting_id})

    actions = await action_repo.list_by_meeting(session, meeting_id)
    has_sync = await crm_sync_repo.has_sync_for_meeting(session, meeting_id)
    notifications_sent = await notification_repo.count_for_meeting(session, meeting_id)
    crm_status = "synced" if has_sync else "pending"

    data = MeetingDetailResponse(
        meeting=meeting,
        action_items=actions,
        crm_sync=CrmSyncStatus(status=crm_status),
        notifications_sent=notifications_sent,
    )
    return SuccessEnvelope(data=data, metadata=ResponseMetadata(correlation_id=correlation_id))
