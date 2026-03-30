"""
Process endpoint integration tests.
"""

# Standard library
from __future__ import annotations

# Third party
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_process_text_returns_202_with_meeting_id(app: FastAPI) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/api/v1/process",
            json={"text": "Speaker 1: Hello\nSpeaker 2: Hi", "deal_id": "deal_1"},
        )
        assert r.status_code == 202
        payload = r.json()
        assert payload["status"] == "success"
        assert payload["data"]["meeting_id"]
        assert payload["metadata"]["correlation_id"]


@pytest.mark.asyncio
async def test_process_audio_returns_202_with_meeting_id(app: FastAPI) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/api/v1/process",
            files={"audio": ("meeting.mp3", b"\x00" * 10000, "audio/mpeg")},
        )
        assert r.status_code == 202
        payload = r.json()
        assert payload["status"] == "success"
        assert payload["data"]["meeting_id"]


@pytest.mark.asyncio
async def test_duplicate_transcript_returns_409(app: FastAPI) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        body = {"text": "Speaker 1: Same transcript", "deal_id": "deal_dup"}
        r1 = await client.post("/api/v1/process", json=body)
        assert r1.status_code == 202
        r2 = await client.post("/api/v1/process", json=body)
        assert r2.status_code == 409
        payload = r2.json()
        assert payload["status"] == "error"
        assert payload["error"]["code"] == "DUPLICATE"


@pytest.mark.asyncio
async def test_process_with_deal_id_links_to_series(app: FastAPI) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/v1/process", json={"text": "Notes", "deal_id": "deal_series"})
        assert r.status_code == 202
        meeting_id = r.json()["data"]["meeting_id"]

        detail = await client.get(f"/api/v1/meetings/{meeting_id}")
        assert detail.status_code == 200
        series_id = detail.json()["data"]["meeting"]["meeting_series_id"]
        assert isinstance(series_id, str) and series_id
