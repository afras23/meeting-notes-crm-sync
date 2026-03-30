"""
CRM diff detection tests.
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


@pytest.mark.asyncio
async def test_crm_skips_update_when_seed_matches_desired_properties(tmp_path: Path) -> None:
    mapping_file = tmp_path / "crm_mapping.yaml"
    mapping_file.write_text(
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

    extraction = MeetingExtraction(
        title="Discovery call",
        summary="s",
        confidence=0.9,
    )
    meeting = Meeting(
        id="m_1",
        meeting_series_id="s1",
        deal_id="deal_x",
        project_id=None,
        title=extraction.title,
        occurred_at=datetime.now(UTC),
        transcript="t",
        extraction=extraction,
        crm_updates=CRMUpdates(deal=CRMDealUpdate(amount=123.0, stage="proposal")),
        confidence=0.9,
    )

    crm = HubSpotClientMock()
    crm.seed_deal(
        "deal_x",
        {"dealname": "Discovery call", "amount": 123.0, "dealstage": "proposal"},
    )
    service = CRMService(crm_client=crm, mapping_path=str(mapping_file), crm_key="hubspot")
    result = await service.apply_updates(meeting=meeting, deal_id="deal_x")

    assert result["changed_properties"] == {}
    assert not any(u.get("entity") == "deal" for u in crm.applied_updates)
