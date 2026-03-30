"""
Meeting series tracking.

Links multiple meetings that belong to the same deal or project.
"""

# Standard library
from __future__ import annotations

# Third party
from pydantic import BaseModel, Field


class MeetingSeries(BaseModel):
    """A logical series of related meetings."""

    id: str = Field(..., description="Stable series identifier.")
    deal_id: str | None = Field(default=None, description="CRM deal id when series is deal-scoped.")
    project_id: str | None = Field(
        default=None, description="Internal project id when series is project-scoped."
    )
    meeting_ids: list[str] = Field(default_factory=list, description="Meeting ids in this series.")
