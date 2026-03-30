"""
Meeting repository (async SQLAlchemy).
"""

# Standard library
from __future__ import annotations

# Standard library
from datetime import UTC, datetime

# Third party
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

# Local
from app.db.tables import ActionItemORM, MeetingORM
from app.models.extraction import MeetingExtraction
from app.models.meeting import CRMUpdates, Meeting


class MeetingRepository:
    """Persist and load meetings."""

    async def upsert(
        self,
        session: AsyncSession,
        meeting: Meeting,
        *,
        transcript_hash: str,
        processing_ms: float,
        cost_usd: float,
        status: str,
    ) -> None:
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
            transcript_hash=transcript_hash,
            status=status,
            processing_ms=float(processing_ms),
            cost_usd=float(cost_usd),
            created_at=datetime.now(UTC),
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
                    created_at=datetime.now(UTC),
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
        page: int = 1,
        page_size: int = 20,
        deal_id: str | None = None,
        status: str | None = None,
    ) -> list[Meeting]:
        """List meetings with basic filters."""

        stmt: Select[tuple[MeetingORM]] = select(MeetingORM).order_by(MeetingORM.created_at.desc())
        if deal_id is not None:
            stmt = stmt.where(MeetingORM.deal_id == deal_id)
        if status is not None:
            stmt = stmt.where(MeetingORM.status == status)
        stmt = stmt.offset(max(0, page - 1) * page_size).limit(page_size)
        result = await session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_domain(r) for r in rows]

    async def find_by_transcript_hash(
        self, session: AsyncSession, transcript_hash: str
    ) -> MeetingORM | None:
        result = await session.execute(
            select(MeetingORM).where(MeetingORM.transcript_hash == transcript_hash).limit(1)
        )
        return result.scalars().first()

    async def count_processed_today(self, session: AsyncSession) -> int:
        start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        result = await session.execute(
            select(func.count()).select_from(MeetingORM).where(MeetingORM.created_at >= start)
        )
        return int(result.scalar_one() or 0)

    async def avg_processing_ms_today(self, session: AsyncSession) -> float:
        start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        result = await session.execute(
            select(func.avg(MeetingORM.processing_ms))
            .select_from(MeetingORM)
            .where(MeetingORM.created_at >= start)
        )
        value = result.scalar_one()
        return float(value or 0.0)

    async def cost_today_usd(self, session: AsyncSession) -> float:
        start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        result = await session.execute(
            select(func.sum(MeetingORM.cost_usd))
            .select_from(MeetingORM)
            .where(MeetingORM.created_at >= start)
        )
        value = result.scalar_one()
        return float(value or 0.0)

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
