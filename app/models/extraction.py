"""
Rich meeting extraction schema.

Structured output from the extraction pipeline (AI or deterministic mock).
"""

# Standard library
from __future__ import annotations

from datetime import date

# Third party
from pydantic import BaseModel, Field

# Local
from app.models.action_item import ActionItem


class Attendee(BaseModel):
    """A meeting participant."""

    name: str = Field(..., min_length=1, description="Display name.")
    role: str | None = Field(default=None, description="Role (e.g. champion, economic buyer).")
    email: str | None = Field(default=None, description="Email if known.")


class Decision(BaseModel):
    """A decision captured from the meeting."""

    text: str = Field(..., min_length=1, description="What was decided.")
    decided_by: str | None = Field(default=None, description="Who decided or announced it.")


class DealStageChange(BaseModel):
    """Deal pipeline stage transition inferred from the meeting."""

    old_stage: str | None = Field(default=None, description="Previous stage name.")
    new_stage: str | None = Field(default=None, description="New stage name.")


class MeetingExtraction(BaseModel):
    """
    Full structured extraction for a meeting transcript.

    Nested under Meeting; drives CRM mapping and notifications.
    """

    title: str = Field(..., min_length=1, description="Meeting title.")
    summary: str = Field(..., min_length=1, description="Short summary.")
    attendees: list[Attendee] = Field(default_factory=list, description="Attendees with roles.")
    action_items: list[ActionItem] = Field(
        default_factory=list, description="Action items (ids filled when persisted)."
    )
    decisions: list[Decision] = Field(default_factory=list, description="Decisions made.")
    deal_stage_change: DealStageChange | None = Field(
        default=None, description="Inferred deal stage change."
    )
    next_steps: str | None = Field(default=None, description="Agreed next steps narrative.")
    follow_up_date: date | None = Field(default=None, description="Follow-up date if mentioned.")
    sentiment: str | None = Field(
        default=None, description="Overall sentiment label (e.g. positive, neutral, negative)."
    )
    confidence: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Model-reported extraction confidence.",
    )
