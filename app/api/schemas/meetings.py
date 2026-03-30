"""
Meeting list/detail schemas.
"""

# Standard library
from __future__ import annotations

from datetime import datetime

# Third party
from pydantic import BaseModel, Field

# Local
from app.api.schemas.pagination import PaginatedResponse
from app.models.action_item import ActionItem
from app.models.meeting import Meeting


class MeetingSummary(BaseModel):
    id: str = Field(..., description="Meeting id.")
    deal_id: str | None = Field(default=None, description="Linked deal id.")
    title: str = Field(..., description="Meeting title.")
    occurred_at: datetime | None = Field(default=None, description="When meeting occurred.")
    confidence: float = Field(..., description="Extraction confidence.")


class MeetingListResponse(BaseModel):
    meetings: PaginatedResponse[MeetingSummary] = Field(..., description="Paginated meetings.")


class CrmSyncStatus(BaseModel):
    status: str = Field(..., description="synced|pending|failed")


class MeetingDetailResponse(BaseModel):
    meeting: Meeting = Field(..., description="Meeting record.")
    action_items: list[ActionItem] = Field(default_factory=list, description="Action items.")
    crm_sync: CrmSyncStatus = Field(..., description="CRM sync status summary.")
    notifications_sent: int = Field(..., ge=0, description="Number of notifications sent.")
