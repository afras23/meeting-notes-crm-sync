"""
Meetings endpoints.

Provides access to stored processed meetings.
"""

# Standard library
from __future__ import annotations

# Third party
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

# Local
from app.dependencies import get_meeting_repo
from app.models.meeting import Meeting
from app.repositories.meeting_repository import MeetingRepository

router = APIRouter()


class ListMeetingsResponse(BaseModel):
    """Response for meeting list endpoint."""

    meetings: list[Meeting] = Field(default_factory=list, description="Meetings.")


@router.get("/meetings", response_model=ListMeetingsResponse)
async def list_meetings(
    meeting_repo: MeetingRepository = Depends(get_meeting_repo),
    limit: int = 50,
) -> ListMeetingsResponse:
    """List recent meetings."""

    meetings = await meeting_repo.list(limit=limit)
    return ListMeetingsResponse(meetings=meetings)


@router.get("/meetings/{meeting_id}", response_model=Meeting)
async def get_meeting(
    meeting_id: str,
    meeting_repo: MeetingRepository = Depends(get_meeting_repo),
) -> Meeting:
    """Get a meeting by id."""

    meeting = await meeting_repo.get(meeting_id)
    if meeting is None:
        from app.core.exceptions import ValidationFailed

        raise ValidationFailed("Meeting not found.", context={"meeting_id": meeting_id})
    return meeting
