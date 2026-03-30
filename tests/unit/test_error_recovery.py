"""
Error recovery: AI timeouts, CRM failures, malformed inputs (all mocked).
"""

# Standard library
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

# Local
from app.core.exceptions import ExtractionFailed
from app.models.extraction import MeetingExtraction
from app.models.meeting import Meeting
from app.models.transcription import ParsedTranscript
from app.repositories.audit_repository import AuditRepository
from app.services.crm_service import CRMService
from app.services.extraction_service import ExtractionService
from app.services.process_service import MeetingProcessService
from tests.fixtures.ai_clients import AlwaysTimeoutAIClient, FlakyAIClient, ScriptedAIClient


@pytest.mark.asyncio
async def test_ai_timeout_retries_then_succeeds_on_third_llm_call() -> None:
    """First two generate_json calls raise TimeoutError; extraction retries and succeeds."""

    ai = FlakyAIClient(failures_before_success=2)
    svc = ExtractionService(ai_client=ai, audit_repository=AuditRepository())
    m = await svc.extract_meeting(
        transcript="Speaker 1: proposal stage 10k next week.", deal_id=None, project_id=None
    )
    assert m.id
    assert m.extraction.title


@pytest.mark.asyncio
async def test_ai_timeout_retries_then_returns_error() -> None:
    """After three TimeoutErrors extraction fails with ExtractionFailed."""

    ai = AlwaysTimeoutAIClient()
    svc = ExtractionService(ai_client=ai, audit_repository=AuditRepository())
    with pytest.raises(ExtractionFailed, match="timed out"):
        await svc.extract_meeting(transcript="Speaker 1: hello", deal_id=None, project_id=None)


@pytest.mark.asyncio
async def test_crm_unavailable_logs_error_continues_processing() -> None:
    """When CRM apply_updates raises, pipeline still persists the meeting."""

    extraction = MeetingExtraction(title="T", summary="s", confidence=0.9)
    meeting = Meeting(
        id="mid",
        meeting_series_id="s",
        deal_id="d1",
        project_id=None,
        title="T",
        occurred_at=datetime.now(UTC),
        transcript="hello world",
        extraction=extraction,
        confidence=0.9,
    )
    pt = ParsedTranscript(raw_text="hello world", speakers=[])

    transcription = MagicMock()
    transcription.parse_transcript = AsyncMock(return_value=pt)

    ext = MagicMock()
    ext.extract_meeting = AsyncMock(return_value=meeting)

    crm = MagicMock(spec=CRMService)
    crm.apply_updates = AsyncMock(side_effect=ConnectionError("CRM unavailable"))

    notif = MagicMock()
    notif.notify_meeting_events = AsyncMock()

    session = AsyncMock()
    meeting_repo = AsyncMock()
    meeting_repo.find_by_transcript_hash = AsyncMock(return_value=None)
    meeting_repo.upsert = AsyncMock()

    svc = MeetingProcessService(
        transcription_service=transcription,
        extraction_service=ext,
        crm_service=crm,
        notification_service=notif,
        meeting_repo=meeting_repo,
        crm_sync_repo=AsyncMock(),
        audit_repo=AsyncMock(),
    )
    result = await svc.process_meeting(
        session,
        content="hello world",
        filename=None,
        input_type="text",
        deal_id="deal_x",
        project_id=None,
    )
    assert "error" in result.crm_result
    meeting_repo.upsert.assert_awaited()


@pytest.mark.asyncio
async def test_malformed_transcript_returns_partial_extraction() -> None:
    """Valid JSON with sparse fields still yields a Meeting (graceful defaults)."""

    ai = ScriptedAIClient()
    ai.enqueue_json(
        {
            "title": "Recovered",
            "summary": "Partial parse ok.",
            "confidence": 0.35,
            "crm_updates": {"deal": {}},
        }
    )
    svc = ExtractionService(ai_client=ai, audit_repository=AuditRepository())
    m = await svc.extract_meeting(
        transcript="!!! not a sentence !!!", deal_id=None, project_id=None
    )
    assert m.extraction.title == "Recovered"
    assert m.extraction.confidence == 0.35
