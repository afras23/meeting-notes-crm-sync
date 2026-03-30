"""
Concurrent API requests (in-memory DB); distinct transcripts avoid idempotency collisions.
"""

# Standard library
from __future__ import annotations

import asyncio

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_concurrent_meeting_processing_no_data_corruption(app: FastAPI) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        results = await asyncio.gather(
            client.post(
                "/api/v1/process",
                json={"text": "Speaker 1: concurrent run A proposal 10k.", "deal_id": "deal_ca"},
            ),
            client.post(
                "/api/v1/process",
                json={"text": "Speaker 1: concurrent run B proposal 10k.", "deal_id": "deal_cb"},
            ),
        )
        assert all(r.status_code == 202 for r in results)
        ids = {r.json()["data"]["meeting_id"] for r in results}
        assert len(ids) == 2

        listed = await client.get("/api/v1/meetings", params={"page": 1, "page_size": 10})
        assert listed.status_code == 200
        items = listed.json()["data"]["meetings"]["items"]
        assert len(items) >= 2
