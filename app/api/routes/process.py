"""
Processing endpoint.

Accepts meeting transcripts, runs extraction, applies CRM updates, and triggers notifications.
"""

# Standard library
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

# Third party
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

# Local
from app.dependencies import (
    get_calendar_client,
    get_crm_service,
    get_crm_sync_repo,
    get_db_session,
    get_extraction_service,
    get_meeting_repo,
    get_notification_service,
    get_transcription_service,
)
from app.integrations.calendar_client import CalendarClientMock
from app.models.meeting import Meeting
from app.repositories.crm_sync_repository import CrmSyncRepository
from app.repositories.meeting_repository import MeetingRepository
from app.services.crm_service import CRMService
from app.services.extraction_service import ExtractionService
from app.services.notification_service import NotificationService
from app.services.transcription_service import TranscriptionService

logger = logging.getLogger(__name__)

router = APIRouter()


class ProcessMeetingRequest(BaseModel):
    """Request payload to process a meeting."""

    transcript_text: str = Field(
        ..., min_length=1, max_length=100_000, description="Meeting transcript text."
    )
    deal_id: str = Field(default="deal_mock_1", description="CRM deal identifier to update.")
    project_id: str | None = Field(
        default=None, description="Linked project id for series grouping."
    )
    calendar_event_id: str | None = Field(
        default=None, description="Optional calendar event id to fetch metadata."
    )


class ProcessMeetingResponse(BaseModel):
    """Response payload for meeting processing."""

    meeting: Meeting = Field(..., description="Structured meeting output.")
    crm_update: dict[str, Any] = Field(..., description="Applied CRM update summary.")


@router.post("/process", response_model=ProcessMeetingResponse)
async def process_meeting(
    request: ProcessMeetingRequest,
    session: AsyncSession = Depends(get_db_session),
    transcription_service: TranscriptionService = Depends(get_transcription_service),
    extraction_service: ExtractionService = Depends(get_extraction_service),
    crm_service: CRMService = Depends(get_crm_service),
    notification_service: NotificationService = Depends(get_notification_service),
    calendar_client: CalendarClientMock = Depends(get_calendar_client),
    meeting_repo: MeetingRepository = Depends(get_meeting_repo),
    crm_sync_repo: CrmSyncRepository = Depends(get_crm_sync_repo),
) -> ProcessMeetingResponse:
    """Process a meeting transcript end-to-end."""

    transcript = await transcription_service.get_transcript(
        transcript_text=request.transcript_text, audio_bytes=None
    )
    occurred_at: datetime | None = None
    if request.calendar_event_id:
        meta = await calendar_client.fetch_event_metadata(request.calendar_event_id)
        if meta:
            title = str(meta.get("title") or "")
            participants = meta.get("participants") or []
            if not isinstance(participants, list):
                participants = []
            transcript = f"[Calendar: title={title} | participants={participants}]\n" + transcript
            start_at = meta.get("start_at")
            if isinstance(start_at, datetime):
                occurred_at = start_at
            elif isinstance(start_at, str):
                occurred_at = datetime.fromisoformat(start_at.replace("Z", "+00:00"))

    meeting = await extraction_service.extract_meeting(
        transcript=transcript,
        deal_id=request.deal_id,
        project_id=request.project_id,
        occurred_at=occurred_at,
    )

    await meeting_repo.upsert(session, meeting)

    crm_update = await crm_service.apply_updates(meeting=meeting, deal_id=request.deal_id)
    changed = crm_update.get("changed_properties") or {}
    if isinstance(changed, dict) and changed:
        await crm_sync_repo.create(
            session,
            meeting_id=meeting.id,
            deal_id=request.deal_id,
            changed_properties=dict(changed),
            previous_snapshot=dict(crm_update.get("previous_snapshot") or {}),
        )

    await notification_service.notify_meeting_events(
        session, meeting=meeting, crm_result=crm_update
    )
    await session.commit()

    logger.info("Processed meeting", extra={"meeting_id": meeting.id, "deal_id": request.deal_id})
    return ProcessMeetingResponse(meeting=meeting, crm_update=crm_update)
