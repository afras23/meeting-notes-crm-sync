"""
CRM mapping and diff behaviour (mock HubSpot).
"""

# Standard library
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

# Local
from app.integrations.hubspot_client import HubSpotClientMock
from app.models.extraction import MeetingExtraction
from app.models.meeting import CRMDealUpdate, CRMUpdates, Meeting
from app.services.crm_service import CRMService


def _mapping(tmp_path: Path) -> str:
    p = tmp_path / "m.yaml"
    p.write_text(
        "\n".join(
            [
                'version: "2"',
                "crm_mappings:",
                "  hubspot:",
                "    entities:",
                "      deal:",
                "        fields:",
                "          dealname:",
                '            source: "meeting.title"',
                "          amount:",
                '            source: "meeting.crm_updates.deal.amount"',
                "          dealstage:",
                '            source: "meeting.crm_updates.deal.stage"',
            ]
        ),
        encoding="utf-8",
    )
    return str(p)


@pytest.mark.asyncio
async def test_hubspot_mapping_produces_correct_fields(tmp_path: Path) -> None:
    extraction = MeetingExtraction(title="Mapped title", summary="s", confidence=0.9)
    meeting = Meeting(
        id="m1",
        meeting_series_id="s1",
        deal_id="d1",
        project_id=None,
        title=extraction.title,
        occurred_at=datetime.now(UTC),
        transcript="t",
        extraction=extraction,
        crm_updates=CRMUpdates(deal=CRMDealUpdate(amount=5000.0, stage="negotiation")),
        confidence=0.9,
    )
    crm = HubSpotClientMock()
    svc = CRMService(crm_client=crm, mapping_path=_mapping(tmp_path), crm_key="hubspot")
    result = await svc.apply_updates(meeting=meeting, deal_id="deal_hs")
    changed = result["changed_properties"]
    assert changed.get("dealname") == "Mapped title"
    assert changed.get("amount") == 5000.0
    assert changed.get("dealstage") == "negotiation"


@pytest.mark.asyncio
async def test_diff_detection_only_updates_changed_fields(tmp_path: Path) -> None:
    extraction = MeetingExtraction(title="Same title", summary="s", confidence=0.9)
    meeting = Meeting(
        id="m2",
        meeting_series_id="s1",
        deal_id="d1",
        project_id=None,
        title=extraction.title,
        occurred_at=datetime.now(UTC),
        transcript="t",
        extraction=extraction,
        crm_updates=CRMUpdates(deal=CRMDealUpdate(amount=100.0, stage="lead")),
        confidence=0.9,
    )
    crm = HubSpotClientMock()
    crm.seed_deal("deal_x", {"dealname": "Same title", "amount": 50.0, "dealstage": "lead"})
    svc = CRMService(crm_client=crm, mapping_path=_mapping(tmp_path), crm_key="hubspot")
    result = await svc.apply_updates(meeting=meeting, deal_id="deal_x")
    assert "amount" in result["changed_properties"]
    assert result["changed_properties"]["amount"] == 100.0
    assert "dealname" not in result["changed_properties"]


@pytest.mark.asyncio
async def test_diff_detection_preserves_manual_crm_edits(tmp_path: Path) -> None:
    """Fields not present in desired payload remain untouched in mock deal store."""

    extraction = MeetingExtraction(title="New title from meeting", summary="s", confidence=0.9)
    meeting = Meeting(
        id="m3",
        meeting_series_id="s1",
        deal_id="d1",
        project_id=None,
        title=extraction.title,
        occurred_at=datetime.now(UTC),
        transcript="t",
        extraction=extraction,
        crm_updates=CRMUpdates(deal=CRMDealUpdate(amount=200.0, stage="lead")),
        confidence=0.9,
    )
    crm = HubSpotClientMock()
    crm.seed_deal(
        "deal_manual",
        {
            "dealname": "Old manual name",
            "amount": 200.0,
            "dealstage": "lead",
            "notes_last_updated_by": "human@example.com",
        },
    )
    svc = CRMService(crm_client=crm, mapping_path=_mapping(tmp_path), crm_key="hubspot")
    await svc.apply_updates(meeting=meeting, deal_id="deal_manual")
    stored = await crm.get_deal("deal_manual")
    assert stored is not None
    assert stored.get("notes_last_updated_by") == "human@example.com"


@pytest.mark.asyncio
async def test_no_changes_detected_skips_crm_update(tmp_path: Path) -> None:
    extraction = MeetingExtraction(title="Aligned", summary="s", confidence=0.9)
    meeting = Meeting(
        id="m4",
        meeting_series_id="s1",
        deal_id="d1",
        project_id=None,
        title=extraction.title,
        occurred_at=datetime.now(UTC),
        transcript="t",
        extraction=extraction,
        crm_updates=CRMUpdates(deal=CRMDealUpdate(amount=99.0, stage="s")),
        confidence=0.9,
    )
    crm = HubSpotClientMock()
    crm.seed_deal("deal_same", {"dealname": "Aligned", "amount": 99.0, "dealstage": "s"})
    svc = CRMService(crm_client=crm, mapping_path=_mapping(tmp_path), crm_key="hubspot")
    result = await svc.apply_updates(meeting=meeting, deal_id="deal_same")
    assert result["changed_properties"] == {}
    assert not any(u.get("entity") == "deal" and u.get("properties") for u in crm.applied_updates)
