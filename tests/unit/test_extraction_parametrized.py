"""
Parametrised extraction scenarios: meeting types and edge transcripts (mock LLM).
"""

# Standard library
from __future__ import annotations

from unittest.mock import patch

import pytest

# Local
from app.core.constants import MAX_TRANSCRIPT_CHARS_FOR_LLM
from app.repositories.audit_repository import AuditRepository
from app.services.ai.prompts import get_prompt as real_get_prompt
from app.services.extraction_service import ExtractionService
from tests.fixtures.ai_clients import ScriptedAIClient
from tests.fixtures.sample_transcripts import (
    CLIENT_KICKOFF,
    MULTILINGUAL_FR,
    NO_ACTIONS,
    ONE_ON_ONE,
    SALES_CALL,
    STANDUP,
    VERY_LONG_BODY,
    VERY_SHORT,
)


def _svc(ai: ScriptedAIClient) -> ExtractionService:
    return ExtractionService(ai_client=ai, audit_repository=AuditRepository())


def _minimal_payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "title": "Meeting",
        "summary": "Summary text.",
        "attendees": [],
        "action_items": [],
        "decisions": [],
        "deal_stage_change": None,
        "next_steps": None,
        "follow_up_date": None,
        "sentiment": "neutral",
        "crm_updates": {"deal": {}},
        "confidence": 0.85,
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_sales_call_extracts_deal_stage_and_next_steps() -> None:
    ai = ScriptedAIClient()
    ai.enqueue_json(
        _minimal_payload(
            title="QBR",
            summary="Discussed pipeline.",
            deal_stage_change={"old_stage": "qualification", "new_stage": "proposal"},
            next_steps="Send pricing deck",
            crm_updates={"deal": {"stage": "proposal"}},
        )
    )
    m = await _svc(ai).extract_meeting(transcript=SALES_CALL, deal_id="deal_1", project_id=None)
    assert m.extraction.deal_stage_change is not None
    assert m.extraction.deal_stage_change.new_stage == "proposal"
    assert m.extraction.next_steps


@pytest.mark.asyncio
async def test_standup_meeting_extracts_blockers_and_updates() -> None:
    ai = ScriptedAIClient()
    ai.enqueue_json(
        _minimal_payload(
            title="Standup",
            summary="Blockers: CI pipeline failing; owner fixing today.",
            next_steps="Unblock deploy",
        )
    )
    m = await _svc(ai).extract_meeting(transcript=STANDUP, deal_id=None, project_id="p1")
    assert "blocker" in m.extraction.summary.lower() or "ci" in m.extraction.summary.lower()


@pytest.mark.asyncio
async def test_client_kickoff_extracts_attendees_and_action_items() -> None:
    ai = ScriptedAIClient()
    ai.enqueue_json(
        _minimal_payload(
            title="Kickoff",
            summary="Kickoff meeting.",
            attendees=[
                {"name": "Alice", "role": "PM", "email": "a@example.com"},
                {"name": "Bob", "role": "Eng", "email": "b@example.com"},
            ],
            action_items=[
                {
                    "owner": "b@example.com",
                    "description": "Share architecture doc",
                    "due_date_iso": "2026-06-15T17:00:00+00:00",
                    "status": "open",
                }
            ],
        )
    )
    m = await _svc(ai).extract_meeting(transcript=CLIENT_KICKOFF, deal_id="d_k", project_id=None)
    assert len(m.extraction.attendees) >= 1
    assert len(m.extraction.action_items) >= 1


@pytest.mark.asyncio
async def test_one_on_one_extracts_decisions_and_follow_ups() -> None:
    ai = ScriptedAIClient()
    ai.enqueue_json(
        _minimal_payload(
            title="1:1",
            summary="Career discussion.",
            decisions=[{"text": "Promote internal tool", "decided_by": "Manager"}],
            follow_up_date="2026-05-01",
        )
    )
    m = await _svc(ai).extract_meeting(transcript=ONE_ON_ONE, deal_id=None, project_id=None)
    assert m.extraction.decisions
    assert m.extraction.follow_up_date is not None


@pytest.mark.asyncio
async def test_very_short_meeting_handles_minimal_content() -> None:
    ai = ScriptedAIClient()
    ai.enqueue_json(_minimal_payload(title="Short", summary="Brief hello.", confidence=0.5))
    m = await _svc(ai).extract_meeting(transcript=VERY_SHORT, deal_id=None, project_id=None)
    assert m.extraction.title
    assert m.confidence >= 0.0


@pytest.mark.asyncio
async def test_very_long_meeting_truncates_before_llm() -> None:
    ai = ScriptedAIClient()
    ai.enqueue_json(_minimal_payload(title="Long", summary="Lots of words."))
    long_transcript = VERY_LONG_BODY + "\n" + "Speaker 1: proposal 10k."
    lengths: dict[str, int] = {}

    def _capture(name: str, *, transcript: str) -> tuple[str, str, str]:
        lengths["prompt_transcript_len"] = len(transcript)
        return real_get_prompt(name, transcript=transcript)

    with patch("app.services.extraction_service.get_prompt", side_effect=_capture):
        await _svc(ai).extract_meeting(transcript=long_transcript, deal_id=None, project_id=None)

    assert lengths["prompt_transcript_len"] <= MAX_TRANSCRIPT_CHARS_FOR_LLM


@pytest.mark.asyncio
async def test_meeting_with_no_clear_actions_returns_empty_list() -> None:
    ai = ScriptedAIClient()
    ai.enqueue_json(_minimal_payload(title="Chat", summary="No actions.", action_items=[]))
    m = await _svc(ai).extract_meeting(transcript=NO_ACTIONS, deal_id=None, project_id=None)
    assert m.extraction.action_items == []


@pytest.mark.asyncio
async def test_multilingual_meeting_extracts_in_primary_language() -> None:
    ai = ScriptedAIClient()
    ai.enqueue_json(
        _minimal_payload(
            title="Réunion",
            summary="Résumé: accord sur le budget et prochaine étape signature.",
            confidence=0.88,
        )
    )
    m = await _svc(ai).extract_meeting(transcript=MULTILINGUAL_FR, deal_id=None, project_id=None)
    assert "budget" in m.extraction.summary.lower() or "accord" in m.extraction.summary.lower()


@pytest.mark.parametrize(
    "_label,transcript,extra",
    [
        ("sales_variant", SALES_CALL, {"next_steps": "Call back"}),
        ("standup_variant", STANDUP, {"summary": "Daily sync"}),
    ],
    ids=["sales_variant", "standup_variant"],
)
@pytest.mark.asyncio
async def test_extraction_across_meeting_type_variants(
    _label: str, transcript: str, extra: dict[str, object]
) -> None:
    ai = ScriptedAIClient()
    ai.enqueue_json(_minimal_payload(**extra))
    m = await _svc(ai).extract_meeting(transcript=transcript, deal_id="d_x", project_id=None)
    assert m.id
