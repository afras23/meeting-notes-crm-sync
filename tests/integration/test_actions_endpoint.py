"""
Actions endpoints integration tests.
"""

# Standard library
from __future__ import annotations

# Third party
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_actions_filterable_by_owner_and_status(app: FastAPI) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/api/v1/process",
            json={"text": "Speaker 1: Follow up needed.", "deal_id": "deal_actions"},
        )
        assert r.status_code == 202

        listed = await client.get("/api/v1/actions", params={"status": "open"})
        assert listed.status_code == 200
        payload = listed.json()
        assert payload["status"] == "success"
        assert isinstance(payload["data"]["actions"]["items"], list)


@pytest.mark.asyncio
async def test_patch_action_updates_status_and_logs_audit(app: FastAPI) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/api/v1/process",
            json={"text": "Speaker 1: Follow up needed.", "deal_id": "deal_actions2"},
        )
        assert r.status_code == 202
        meeting_id = r.json()["data"]["meeting_id"]

        detail = await client.get(f"/api/v1/meetings/{meeting_id}")
        assert detail.status_code == 200
        actions = detail.json()["data"]["action_items"]
        assert actions
        action_id = actions[0]["id"]

        patch = await client.patch(f"/api/v1/actions/{action_id}", json={"status": "done"})
        assert patch.status_code == 200
        assert patch.json()["data"]["action"]["status"] == "done"
