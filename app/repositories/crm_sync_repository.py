"""
CRM sync record repository.
"""

# Standard library
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

# Third party
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
