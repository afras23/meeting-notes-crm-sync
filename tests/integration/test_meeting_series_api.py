"""
Meeting series API tests.
"""

# Standard library
from __future__ import annotations

# Third party
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

# Local
from app.services.meeting_series_service import compute_meeting_series_id


@pytest.mark.asyncio
async def test_two_meetings_same_deal_share_series_id(app: FastAPI) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for round_idx in range(2):
            r = await client.post(
                "/api/v1/process",
                json={
                    "transcript_text": f"Call notes round {round_idx} proposal 10k.",
                    "deal_id": "deal_series_1",
                },
            )
            assert r.status_code == 200

        expected_series = compute_meeting_series_id(deal_id="deal_series_1", project_id=None)
        listed = await client.get("/api/v1/meetings", params={"series_id": expected_series})
        assert listed.status_code == 200
        meetings = listed.json()["meetings"]
        assert len(meetings) == 2
        assert all(m["meeting_series_id"] == expected_series for m in meetings)
