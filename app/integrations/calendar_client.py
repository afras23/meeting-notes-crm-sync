"""
Calendar client (mock).

Fetches meeting metadata (title, time, participants) for enrichment.
"""

# Standard library
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CalendarClientMock:
    """Mock calendar client storing events by id."""

    events_by_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    fetched_events: list[dict[str, object]] = field(default_factory=list)

    def seed_event(self, event_id: str, payload: dict[str, Any]) -> None:
        """Insert or replace a calendar event for tests."""

        self.events_by_id[event_id] = payload

    async def fetch_event_metadata(self, event_id: str) -> dict[str, Any] | None:
        """
        Return meeting metadata for a calendar event.

        Expected keys:
        - title (str)
        - start_at (datetime UTC)
        - end_at (datetime UTC, optional)
        - participants (list[str] emails or names)
        """

        event = self.events_by_id.get(event_id)
        if event is None:
            return None
        self.fetched_events.append({"event_id": event_id, **event})
        return dict(event)

    async def get_meeting(self, meeting_id: str) -> dict[str, object] | None:
        """Legacy alias for fetch by internal meeting id."""

        return await self.fetch_event_metadata(meeting_id)
