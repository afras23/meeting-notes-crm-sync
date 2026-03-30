"""
Meeting repository.

Provides persistence abstraction for meeting records (in-memory implementation by default).
"""

# Standard library
from __future__ import annotations

from dataclasses import dataclass, field

# Local
from app.models.meeting import Meeting


@dataclass
class MeetingRepository:
    """In-memory repository for meetings."""

    _meetings_by_id: dict[str, Meeting] = field(default_factory=dict)

    async def upsert(self, meeting: Meeting) -> None:
        """Insert or update a meeting record."""

        self._meetings_by_id[meeting.id] = meeting

    async def get(self, meeting_id: str) -> Meeting | None:
        """Get a meeting by id."""

        return self._meetings_by_id.get(meeting_id)

    async def list(self, *, limit: int = 50) -> list[Meeting]:
        """List meetings (most recent insertion order not guaranteed)."""

        return list(self._meetings_by_id.values())[:limit]
