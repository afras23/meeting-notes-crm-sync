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
    title: str = Field(..., min_length=1, description="Meeting title.")
    occurred_at: datetime | None = Field(
        default=None, description="When the meeting occurred (UTC)."
    )
    transcript: str = Field(
        ..., min_length=1, description="Meeting transcript (or summarized notes)."
    )
    summary: str = Field(..., min_length=1, description="Short meeting summary.")
    participants: list[str] = Field(default_factory=list, description="Participant names/emails.")
    action_items: list[ActionItem] = Field(
        default_factory=list, description="Extracted action items."
    )
    crm_updates: CRMUpdates = Field(
        default_factory=CRMUpdates, description="Structured CRM updates."
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence score.")
