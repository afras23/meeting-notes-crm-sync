"""
Processing endpoint.

Accepts meeting transcripts, runs extraction, applies CRM updates, and triggers notifications.
"""

# Standard library
from __future__ import annotations

import logging
from typing import Any

# Third party
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

# Local
from app.dependencies import (
    get_action_repo,
    get_crm_service,
    get_extraction_service,
    get_meeting_repo,
    get_notification_service,
    get_transcription_service,
)
from app.models.meeting import Meeting
from app.repositories.action_item_repository import ActionItemRepository
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


class ProcessMeetingResponse(BaseModel):
    """Response payload for meeting processing."""

    meeting: Meeting = Field(..., description="Structured meeting output.")
    crm_update: dict[str, Any] = Field(..., description="Applied CRM update summary.")


@router.post("/process", response_model=ProcessMeetingResponse)
async def process_meeting(
    request: ProcessMeetingRequest,
    transcription_service: TranscriptionService = Depends(get_transcription_service),
    extraction_service: ExtractionService = Depends(get_extraction_service),
    crm_service: CRMService = Depends(get_crm_service),
    notification_service: NotificationService = Depends(get_notification_service),
    meeting_repo: MeetingRepository = Depends(get_meeting_repo),
    action_repo: ActionItemRepository = Depends(get_action_repo),
) -> ProcessMeetingResponse:
    """Process a meeting transcript end-to-end."""

    transcript = await transcription_service.get_transcript(
        transcript_text=request.transcript_text, audio_bytes=None
    )
    meeting = await extraction_service.extract_meeting(transcript=transcript)

    for action_item in meeting.action_items:
        await action_repo.upsert(action_item)
    await meeting_repo.upsert(meeting)

    crm_update = await crm_service.apply_updates(meeting=meeting, deal_id=request.deal_id)
    await notification_service.notify_for_meeting(meeting=meeting)

    logger.info("Processed meeting", extra={"meeting_id": meeting.id, "deal_id": request.deal_id})
    return ProcessMeetingResponse(meeting=meeting, crm_update=crm_update)
