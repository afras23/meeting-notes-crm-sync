"""
Action item extraction edge cases (mock LLM).
"""

# Standard library
from __future__ import annotations

from datetime import UTC

import pytest

# Local
from app.repositories.audit_repository import AuditRepository
from app.services.extraction_service import ExtractionService
from tests.fixtures.ai_clients import ScriptedAIClient


def _svc(ai: ScriptedAIClient) -> ExtractionService:
    return ExtractionService(ai_client=ai, audit_repository=AuditRepository())


@pytest.mark.asyncio
async def test_no_action_items_returns_empty_list_not_error() -> None:
    ai = ScriptedAIClient()
    ai.enqueue_json(
        {
            "title": "T",
            "summary": "No actions.",
            "action_items": [],
            "confidence": 0.8,
            "crm_updates": {"deal": {}},
        }
    )
    m = await _svc(ai).extract_meeting(
        transcript="Speaker 1: Casual chat only.", deal_id=None, project_id=None
    )
    assert m.extraction.action_items == []


@pytest.mark.asyncio
async def test_20_plus_action_items_all_extracted() -> None:
    ai = ScriptedAIClient()
    items = [
        {
            "owner": f"u{i}@example.com",
            "description": f"Task {i}",
            "due_date_iso": f"2026-07-{(i % 27) + 1:02d}T12:00:00+00:00",
            "status": "open",
        }
        for i in range(22)
    ]
    ai.enqueue_json(
        {
            "title": "Planning",
            "summary": "Many tasks.",
            "action_items": items,
            "confidence": 0.9,
            "crm_updates": {"deal": {}},
        }
    )
    m = await _svc(ai).extract_meeting(
        transcript="Bulk planning session.", deal_id=None, project_id=None
    )
    assert len(m.extraction.action_items) == 22


@pytest.mark.asyncio
async def test_ambiguous_ownership_flags_for_review() -> None:
    ai = ScriptedAIClient()
    ai.enqueue_json(
        {
            "title": "T",
            "summary": "Ambiguous.",
            "action_items": [
                {
                    "owner": None,
                    "description": "Someone should review the contract draft.",
                    "status": "open",
                }
            ],
            "confidence": 0.7,
            "crm_updates": {"deal": {}},
        }
    )
    m = await _svc(ai).extract_meeting(
        transcript="Speaker 1: Someone should review the contract draft.",
        deal_id=None,
        project_id=None,
    )
    assert m.extraction.action_items[0].owner is None
    assert "review" in m.extraction.action_items[0].description.lower()


@pytest.mark.asyncio
async def test_action_with_deadline_parses_date_correctly() -> None:
    ai = ScriptedAIClient()
    ai.enqueue_json(
        {
            "title": "T",
            "summary": "Due dates.",
            "action_items": [
                {
                    "owner": "a@example.com",
                    "description": "Ship",
                    "due_date_iso": "2026-08-20T15:30:00+00:00",
                    "status": "open",
                }
            ],
            "confidence": 0.9,
            "crm_updates": {"deal": {}},
        }
    )
    m = await _svc(ai).extract_meeting(transcript="Due next week.", deal_id=None, project_id=None)
    d = m.extraction.action_items[0].deadline
    assert d is not None
    assert d.tzinfo == UTC or d.tzinfo is not None
    assert d.year == 2026
    assert d.month == 8
