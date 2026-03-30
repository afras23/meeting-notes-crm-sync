"""
Rich extraction schema tests (mock AI).
"""

# Standard library
from __future__ import annotations

import pytest

# Local
from app.repositories.audit_repository import AuditRepository
from app.services.ai.client import AIClient
from app.services.extraction_service import ExtractionService


@pytest.mark.asyncio
async def test_mock_extraction_populates_attendees_decisions_and_stage_change() -> None:
    ai = AIClient(provider="mock", model="mock-llm", max_daily_cost_usd=10.0, timeout_seconds=30)
    service = ExtractionService(ai_client=ai, audit_repository=AuditRepository())
    meeting = await service.extract_meeting(
        transcript="We moved to proposal stage. Budget 10k. follow",
        deal_id="d1",
        project_id=None,
    )
    assert len(meeting.extraction.attendees) >= 1
    assert len(meeting.extraction.decisions) >= 1
    assert meeting.extraction.deal_stage_change is not None
    assert meeting.extraction.deal_stage_change.new_stage is not None
    assert meeting.extraction.sentiment is not None
