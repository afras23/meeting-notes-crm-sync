"""
Meeting domain model.

Represents the structured result of processing meeting notes/transcripts.
"""

# Standard library
from __future__ import annotations

from datetime import datetime

# Third party
from pydantic import BaseModel, Field

# Local
from app.models.action_item import ActionItem
from app.models.extraction import MeetingExtraction


class CRMDealUpdate(BaseModel):
    """Proposed CRM deal updates derived from a meeting."""

    amount: float | None = Field(default=None, ge=0.0, description="Proposed deal amount.")
    stage: str | None = Field(default=None, description="Proposed deal stage name.")


class CRMUpdates(BaseModel):
    """CRM update payload grouped by entity."""

    deal: CRMDealUpdate = Field(default_factory=CRMDealUpdate, description="Deal updates.")


class Meeting(BaseModel):
    """A processed meeting record."""

    id: str = Field(..., description="Meeting identifier.")
    meeting_series_id: str = Field(..., description="Series this meeting belongs to.")
    deal_id: str | None = Field(default=None, description="Linked CRM deal id.")
    project_id: str | None = Field(default=None, description="Linked internal project id.")
    title: str = Field(..., min_length=1, description="Meeting title (mirrors extraction.title).")
    occurred_at: datetime | None = Field(
        default=None, description="When the meeting occurred (UTC)."
    )
    transcript: str = Field(
        ..., min_length=1, description="Meeting transcript (or summarized notes)."
    )
    extraction: MeetingExtraction = Field(
        ..., description="Structured extraction (attendees, actions, decisions, etc.)."
    )
    crm_updates: CRMUpdates = Field(
        default_factory=CRMUpdates, description="Mapped CRM field updates."
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Top-level extraction confidence.")

    @property
    def action_items(self) -> list[ActionItem]:
        """Convenience: action items from extraction."""

        return self.extraction.action_items
