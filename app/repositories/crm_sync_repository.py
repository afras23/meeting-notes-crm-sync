"""
CRM sync record repository.
"""

# Standard library
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

# Third party
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

# Local
from app.db.tables import CrmSyncRecordORM


class CrmSyncRepository:
    """Persist CRM diff application audit rows."""

    async def create(
        self,
        session: AsyncSession,
        *,
        meeting_id: str,
        deal_id: str,
        changed_properties: dict[str, object],
        previous_snapshot: dict[str, object],
    ) -> str:
        """Insert a sync record and return its id."""

        record_id = str(uuid4())
        row = CrmSyncRecordORM(
            id=record_id,
            meeting_id=meeting_id,
            deal_id=deal_id,
            changed_properties_json=dict(changed_properties),
            previous_snapshot_json=dict(previous_snapshot),
            created_at=datetime.now(UTC),
        )
        session.add(row)
        await session.flush()
        return record_id

    async def count_today(self, session: AsyncSession) -> int:
        start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        result = await session.execute(
            select(func.count())
            .select_from(CrmSyncRecordORM)
            .where(CrmSyncRecordORM.created_at >= start)
        )
        return int(result.scalar_one() or 0)

    async def has_sync_for_meeting(self, session: AsyncSession, meeting_id: str) -> bool:
        result = await session.execute(
            select(func.count())
            .select_from(CrmSyncRecordORM)
            .where(CrmSyncRecordORM.meeting_id == meeting_id)
        )
        return int(result.scalar_one() or 0) > 0
