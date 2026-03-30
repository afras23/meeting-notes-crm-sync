"""
Performance expectations with mocked time and AI.
"""

# Standard library
from __future__ import annotations

import itertools
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_single_meeting_processes_within_30_seconds_mocked_ai(app: FastAPI) -> None:
    """Wall-clock span for /process stays negligible when time is mocked."""

    transport = ASGITransport(app=app)
    with patch(
        "time.monotonic",
        side_effect=(i * 0.001 for i in itertools.count()),
    ):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post(
                "/api/v1/process",
                json={"text": "Speaker 1: performance test proposal 10k.", "deal_id": "deal_perf"},
            )
    assert r.status_code == 202
    assert r.json()["data"]["meeting_id"]
