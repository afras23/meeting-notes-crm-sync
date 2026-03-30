"""
Meetings endpoints integration tests.
"""

# Standard library
from __future__ import annotations

# Third party
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_meetings_list_paginated(app: FastAPI) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for i in range(3):
            r = await client.post(
                "/api/v1/process", json={"text": f"Speaker 1: m{i}", "deal_id": "deal_x"}
            )
            assert r.status_code == 202

        listed = await client.get(
            "/api/v1/meetings", params={"page": 1, "page_size": 2, "deal_id": "deal_x"}
        )
        assert listed.status_code == 200
        payload = listed.json()
        assert payload["status"] == "success"
        assert len(payload["data"]["meetings"]["items"]) == 2


@pytest.mark.asyncio
async def test_meeting_detail_includes_actions_and_crm_status(app: FastAPI) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/api/v1/process",
            json={
                "text": "We discussed proposal and next steps. Budget 10k.",
                "deal_id": "deal_123",
            },
        )
        assert r.status_code == 202
        meeting_id = r.json()["data"]["meeting_id"]

        detail = await client.get(f"/api/v1/meetings/{meeting_id}")
        assert detail.status_code == 200
        payload = detail.json()
        assert payload["status"] == "success"
        assert payload["data"]["meeting"]["id"] == meeting_id
        assert isinstance(payload["data"]["action_items"], list)
        assert payload["data"]["crm_sync"]["status"] in ("synced", "pending", "failed")


@pytest.mark.asyncio
async def test_meeting_not_found_returns_404(app: FastAPI) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/v1/meetings/does_not_exist")
        assert r.status_code == 404
