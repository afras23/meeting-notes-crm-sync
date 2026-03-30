"""
Action item domain model.

Represents an actionable follow-up extracted from a meeting transcript.
"""

# Standard library
from __future__ import annotations

from datetime import datetime

# Third party
from pydantic import BaseModel, Field


class ActionItem(BaseModel):
    """A single action item produced by meeting processing."""

    id: str = Field(..., description="Stable identifier for this action item.")
    meeting_id: str = Field(..., description="Meeting identifier this action belongs to.")
    owner: str | None = Field(default=None, description="Person responsible for the action item.")
    description: str = Field(..., min_length=1, description="Action item description.")
    due_at: datetime | None = Field(default=None, description="Optional due date in UTC.")
    status: str = Field(default="open", description="open|done|cancelled")
