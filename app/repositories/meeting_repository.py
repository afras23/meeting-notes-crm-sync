"""
Meeting repository (async SQLAlchemy).
"""

# Standard library
from __future__ import annotations

# Third party
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Local
from app.db.tables import ActionItemORM, MeetingORM
from app.models.extraction import MeetingExtraction
from app.models.meeting import CRMUpdates, Meeting


class MeetingRepository:
    """Persist and load meetings."""

    async def upsert(self, session: AsyncSession, meeting: Meeting) -> None:
        """Insert or replace a meeting and its action items."""

        existing = await session.get(MeetingORM, meeting.id)
        if existing is not None:
            await session.delete(existing)
            await session.flush()

        row = MeetingORM(
            id=meeting.id,
            meeting_series_id=meeting.meeting_series_id,
            deal_id=meeting.deal_id,
            project_id=meeting.project_id,
            title=meeting.title,
            transcript=meeting.transcript,
            occurred_at=meeting.occurred_at,
            extraction_json=meeting.extraction.model_dump(mode="json"),
            crm_updates_json=meeting.crm_updates.model_dump(mode="json"),
            confidence=meeting.confidence,
        )
        session.add(row)
        for ai in meeting.extraction.action_items:
            session.add(
                ActionItemORM(
                    id=ai.id,
                    meeting_id=meeting.id,
                    owner=ai.owner,
                    description=ai.description,
                    deadline=ai.deadline,
                    status=ai.status,
                )
            )
        await session.flush()

    async def get(self, session: AsyncSession, meeting_id: str) -> Meeting | None:
        """Load meeting by id."""

        row = await session.get(MeetingORM, meeting_id)
        if row is None:
            return None
        return self._to_domain(row)

    async def list(
        self,
        session: AsyncSession,
        *,
        limit: int = 50,
        series_id: str | None = None,
    ) -> list[Meeting]:
        """List recent meetings, optionally filtered by meeting series id."""

        stmt = select(MeetingORM)
        if series_id is not None:
            stmt = stmt.where(MeetingORM.meeting_series_id == series_id)
        stmt = stmt.limit(limit)
        result = await session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_domain(r) for r in rows]

    def _to_domain(self, row: MeetingORM) -> Meeting:
        extraction = MeetingExtraction.model_validate(row.extraction_json)
        crm_updates = CRMUpdates.model_validate(row.crm_updates_json)
        return Meeting(
            id=row.id,
            meeting_series_id=row.meeting_series_id,
            deal_id=row.deal_id,
            project_id=row.project_id,
            title=row.title,
            occurred_at=row.occurred_at,
            transcript=row.transcript,
            extraction=extraction,
            crm_updates=crm_updates,
            confidence=row.confidence,
        )
