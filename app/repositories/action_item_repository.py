"""
Action item repository (async SQLAlchemy).
"""

# Standard library
from __future__ import annotations

from datetime import UTC, datetime

# Third party
from sqlalchemy import func, select
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

    async def list(
        self,
        session: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        owner: str | None = None,
        status: str | None = None,
        meeting_id: str | None = None,
        overdue: bool | None = None,
    ) -> list[ActionItem]:
        stmt = select(ActionItemORM).order_by(ActionItemORM.created_at.desc())
        if owner is not None:
            stmt = stmt.where(ActionItemORM.owner == owner)
        if status is not None:
            stmt = stmt.where(ActionItemORM.status == status)
        if meeting_id is not None:
            stmt = stmt.where(ActionItemORM.meeting_id == meeting_id)
        if overdue is True:
            stmt = stmt.where(
                ActionItemORM.deadline.is_not(None),
                ActionItemORM.deadline < datetime.now(UTC),
                ActionItemORM.status != "done",
            )
        stmt = stmt.offset(max(0, page - 1) * page_size).limit(page_size)
        result = await session.execute(stmt)
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

    async def update_status(
        self, session: AsyncSession, action_id: str, *, status: str
    ) -> ActionItem | None:
        row = await session.get(ActionItemORM, action_id)
        if row is None:
            return None
        row.status = status
        await session.flush()
        return ActionItem(
            id=row.id,
            meeting_id=row.meeting_id,
            owner=row.owner,
            description=row.description,
            deadline=row.deadline,
            status=row.status,
        )

    async def count_created_today(self, session: AsyncSession) -> int:
        start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        result = await session.execute(
            select(func.count()).select_from(ActionItemORM).where(ActionItemORM.created_at >= start)
        )
        return int(result.scalar_one() or 0)

    async def count_pending(self, session: AsyncSession) -> int:
        result = await session.execute(
            select(func.count()).select_from(ActionItemORM).where(ActionItemORM.status != "done")
        )
        return int(result.scalar_one() or 0)

    async def count_overdue(self, session: AsyncSession) -> int:
        now = datetime.now(UTC)
        result = await session.execute(
            select(func.count())
            .select_from(ActionItemORM)
            .where(
                ActionItemORM.deadline.is_not(None),
                ActionItemORM.deadline < now,
                ActionItemORM.status != "done",
            )
        )
        return int(result.scalar_one() or 0)
