"""
Notification log repository.
"""

# Standard library
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

# Third party
from sqlalchemy.ext.asyncio import AsyncSession

# Local
from app.db.tables import NotificationORM


class NotificationRepository:
    """Persist outbound notification audit rows."""

    async def create(
        self,
        session: AsyncSession,
        *,
        meeting_id: str,
        channel: str,
        event_type: str,
        payload: dict[str, object],
    ) -> str:
        """Insert a notification record."""

        nid = str(uuid4())
        row = NotificationORM(
            id=nid,
            meeting_id=meeting_id,
            channel=channel,
            event_type=event_type,
            payload_json=dict(payload),
            created_at=datetime.now(UTC),
        )
        session.add(row)
        await session.flush()
        return nid
