"""
Observability tests: correlation id + metrics.
"""

# Standard library
from __future__ import annotations

# Third party
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_correlation_id_generated_and_returned_in_header(app: FastAPI) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/v1/health")
        assert r.status_code == 200
        assert "x-correlation-id" in {k.lower(): v for k, v in r.headers.items()}


@pytest.mark.asyncio
async def test_metrics_returns_real_data_from_db(app: FastAPI) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # seed a meeting so metrics are non-zero
        r = await client.post(
            "/api/v1/process", json={"text": "Speaker 1: Hello", "deal_id": "deal_m"}
        )
        assert r.status_code == 202

        m = await client.get("/api/v1/metrics")
        assert m.status_code == 200
        payload = m.json()
        assert "meetings_processed_today" in payload
        assert payload["meetings_processed_today"] >= 1
