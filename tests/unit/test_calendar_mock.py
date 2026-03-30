"""
Calendar mock integration tests.
"""

# Standard library
from __future__ import annotations

from datetime import UTC, datetime

import pytest

# Local
from app.integrations.calendar_client import CalendarClientMock


@pytest.mark.asyncio
async def test_fetch_event_metadata_returns_title_and_participants() -> None:
    cal = CalendarClientMock()
    cal.seed_event(
        "evt_1",
        {
            "title": "QBR",
            "start_at": datetime(2026, 4, 1, 15, 0, tzinfo=UTC),
            "participants": ["a@example.com", "b@example.com"],
        },
    )
    meta = await cal.fetch_event_metadata("evt_1")
    assert meta is not None
    assert meta["title"] == "QBR"
    assert len(meta["participants"]) == 2
