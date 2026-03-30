"""
Action item repository (async SQLAlchemy).
"""

# Standard library
from __future__ import annotations

# Third party
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Local
from app.db.tables import ActionItemORM
from app.models.action_item import ActionItem


class ActionItemRepository:
    """Load action items for meetings."""

    async def list_by_meeting(self, session: AsyncSession, meeting_id: str) -> list[ActionItem]:
        """Return action items for a meeting."""

        result = await session.execute(
            select(ActionItemORM).where(ActionItemORM.meeting_id == meeting_id)
        )
        rows = result.scalars().all()
        return [
            ActionItem(
                id=r.id,
                meeting_id=r.meeting_id,
                owner=r.owner,
                description=r.description,
                deadline=r.deadline,
                status=r.status,
            )
            for r in rows
        ]
