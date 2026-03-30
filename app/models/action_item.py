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

    id: str = Field(default="", description="Stable id; assigned when persisted.")
    meeting_id: str = Field(default="", description="Meeting id; assigned when persisted.")
    owner: str | None = Field(default=None, description="Person responsible.")
    description: str = Field(..., min_length=1, description="Action item description.")
    deadline: datetime | None = Field(default=None, description="Due datetime in UTC when known.")
    status: str = Field(default="open", description="open|done|cancelled")
