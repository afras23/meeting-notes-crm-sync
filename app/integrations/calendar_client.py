"""
Calendar client (mock).

Represents a calendar integration boundary for future meeting metadata retrieval.
"""

# Standard library
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CalendarClientMock:
    """Mock calendar client storing retrieved events."""

    fetched_events: list[dict[str, object]] = field(default_factory=list)

    async def get_meeting(self, meeting_id: str) -> dict[str, object] | None:
        """
        Fetch meeting metadata.

        Args:
            meeting_id: Meeting identifier.

        Returns:
            Meeting metadata if found; otherwise None.
        """

        for event in self.fetched_events:
            if event.get("meeting_id") == meeting_id:
                return event
        return None
