"""
CRM mapping unit tests.

Verifies that YAML mapping is applied to meeting payload correctly.
"""

# Standard library
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

# Local
from app.integrations.hubspot_client import HubSpotClientMock
from app.models.meeting import CRMDealUpdate, CRMUpdates, Meeting
from app.services.crm_service import CRMService


@pytest.mark.asyncio
async def test_crm_service_applies_deal_mappings(tmp_path: Path) -> None:
    mapping_file = tmp_path / "crm_mapping.yaml"
    mapping_file.write_text(
        "\n".join(
            [
                'version: "1"',
                'crm: "hubspot"',
                "entities:",
                "  deal:",
                "    fields:",
                "      dealname:",
                '        source: "meeting.title"',
                "      amount:",
                '        source: "crm_updates.deal.amount"',
            ]
        ),
        encoding="utf-8",
    )

    meeting = Meeting(
        id="m_1",
        title="Discovery call",
        occurred_at=datetime.now(UTC),
        transcript="text",
        summary="summary",
        participants=[],
        action_items=[],
        crm_updates=CRMUpdates(deal=CRMDealUpdate(amount=123.0, stage=None)),
        confidence=0.9,
    )

    crm_client = HubSpotClientMock()
    service = CRMService(crm_client=crm_client, mapping_path=str(mapping_file))
    applied = await service.apply_updates(meeting=meeting, deal_id="deal_1")

    properties = applied["properties"]
    assert isinstance(properties, dict)
    assert properties["dealname"] == "Discovery call"
    assert properties["amount"] == 123.0
    assert crm_client.applied_updates
