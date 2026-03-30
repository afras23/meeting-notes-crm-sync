"""
API integration tests.

Verifies the main processing flow works end-to-end via HTTP.
"""

# Standard library
from __future__ import annotations

# Third party
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_process_meeting_creates_meeting_and_actions(app: FastAPI) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        process_response = await client.post(
            "/api/v1/process",
            json={
                "transcript_text": "We discussed proposal and next steps. Budget 10k.",
                "deal_id": "deal_123",
            },
        )
        assert process_response.status_code == 200
        payload = process_response.json()
        meeting_id = payload["meeting"]["id"]

        meetings_response = await client.get("/api/v1/meetings")
        assert meetings_response.status_code == 200
        assert any(m["id"] == meeting_id for m in meetings_response.json()["meetings"])

        actions_response = await client.get(f"/api/v1/meetings/{meeting_id}/actions")
        assert actions_response.status_code == 200
        assert len(actions_response.json()["action_items"]) >= 1
