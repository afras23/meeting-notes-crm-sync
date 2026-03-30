"""
HubSpot mock CRUD tests.
"""

# Standard library
from __future__ import annotations

import pytest

# Local
from app.integrations.hubspot_client import HubSpotClientMock


@pytest.mark.asyncio
async def test_create_contact_update_deal_and_add_note() -> None:
    crm = HubSpotClientMock()
    cid = await crm.create_contact({"email": "x@example.com", "firstname": "X"})
    assert cid.startswith("contact_")
    crm.seed_deal("deal_1", {"dealname": "Old"})
    await crm.update_deal("deal_1", {"dealname": "New"})
    nid = await crm.add_note(deal_id="deal_1", body="Hello")
    assert nid.startswith("note_")
    assert crm.deals["deal_1"]["dealname"] == "New"
    assert any(n["body"] == "Hello" for n in crm.notes)
