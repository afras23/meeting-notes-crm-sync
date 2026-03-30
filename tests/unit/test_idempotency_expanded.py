"""
Idempotency: duplicate transcript and duplicate audio hash behaviour (mocked services).
"""

# Standard library
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

# Local
from app.models.extraction import MeetingExtraction
from app.models.meeting import Meeting
from app.models.transcription import ParsedTranscript, SpeakerSegment, TranscriptResult
from app.repositories.audit_repository import AuditRepository
from app.services.extraction_service import ExtractionService
from app.services.process_service import DuplicateMeeting, MeetingProcessService
from tests.fixtures.ai_clients import ScriptedAIClient


@pytest.mark.asyncio
async def test_same_transcript_twice_creates_one_meeting() -> None:
    """Second extraction with same transcript hits audit cache (same logical meeting shape)."""

    ai = ScriptedAIClient()
    ai.enqueue_json(
        {
            "title": "Once",
            "summary": "s",
            "confidence": 0.9,
            "crm_updates": {"deal": {}},
        }
    )
    audit = AuditRepository()
    svc = ExtractionService(ai_client=ai, audit_repository=audit)
    t = "Speaker 1: identical content for hash."
    m1 = await svc.extract_meeting(transcript=t, deal_id=None, project_id=None)
    m2 = await svc.extract_meeting(transcript=t, deal_id=None, project_id=None)
    assert m1.extraction.title == m2.extraction.title
    assert ai._queue == []


@pytest.mark.asyncio
async def test_same_audio_file_twice_skipped() -> None:
    """Second process with identical parsed text raises DuplicateMeeting."""

    extraction = MeetingExtraction(title="T", summary="s", confidence=0.9)
    meeting = Meeting(
        id="m-id",
        meeting_series_id="ser",
        deal_id="d",
        project_id=None,
        title="T",
        occurred_at=None,
        transcript="same audio transcript",
        extraction=extraction,
        confidence=0.9,
    )
    raw = ParsedTranscript(
        raw_text="same audio transcript",
        speakers=[SpeakerSegment(speaker_id="1", text="same audio transcript")],
    )
    tr = TranscriptResult(
        raw_text=raw.raw_text,
        speakers=raw.speakers,
        duration_seconds=1.0,
        source="whisper",
        cost_usd=0.0,
        latency_ms=1.0,
    )

    transcription = MagicMock()
    transcription.transcribe = AsyncMock(return_value=tr)
    transcription.parse_transcript = AsyncMock(return_value=raw)

    ext = MagicMock()
    ext.extract_meeting = AsyncMock(return_value=meeting)

    row = MagicMock()
    row.id = "existing-meeting"

    meeting_repo = AsyncMock()
    meeting_repo.find_by_transcript_hash = AsyncMock(side_effect=[None, row])

    notifications = MagicMock()
    notifications.notify_meeting_events = AsyncMock()

    svc = MeetingProcessService(
        transcription_service=transcription,
        extraction_service=ext,
        crm_service=MagicMock(),
        notification_service=notifications,
        meeting_repo=meeting_repo,
        crm_sync_repo=AsyncMock(),
        audit_repo=AsyncMock(),
    )
    session = AsyncMock()
    await svc.process_meeting(
        session,
        content=b"bytes",
        filename="a.mp3",
        input_type="audio",
        deal_id=None,
        project_id=None,
    )
    with pytest.raises(DuplicateMeeting):
        await svc.process_meeting(
            session,
            content=b"bytes",
            filename="a.mp3",
            input_type="audio",
            deal_id=None,
            project_id=None,
        )
