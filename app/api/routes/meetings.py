"""
Meetings endpoints.

Provides access to stored processed meetings.
"""

# Standard library
from __future__ import annotations

# Third party
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

# Local
from app.dependencies import get_db_session, get_meeting_repo
from app.models.meeting import Meeting
from app.repositories.meeting_repository import MeetingRepository

router = APIRouter()


class ListMeetingsResponse(BaseModel):
    """Response for meeting list endpoint."""

    meetings: list[Meeting] = Field(default_factory=list, description="Meetings.")


@router.get("/meetings", response_model=ListMeetingsResponse)
async def list_meetings(
    session: AsyncSession = Depends(get_db_session),
    meeting_repo: MeetingRepository = Depends(get_meeting_repo),
    limit: int = 50,
    series_id: str | None = Query(default=None, description="Filter by meeting series id."),
) -> ListMeetingsResponse:
    """List recent meetings."""

    meetings = await meeting_repo.list(session, limit=limit, series_id=series_id)
    return ListMeetingsResponse(meetings=meetings)


@router.get("/meetings/{meeting_id}", response_model=Meeting)
async def get_meeting(
    meeting_id: str,
    session: AsyncSession = Depends(get_db_session),
    meeting_repo: MeetingRepository = Depends(get_meeting_repo),
) -> Meeting:
    """Get a meeting by id."""

    meeting = await meeting_repo.get(session, meeting_id)
    if meeting is None:
        from app.core.exceptions import ValidationFailed

        raise ValidationFailed("Meeting not found.", context={"meeting_id": meeting_id})
    return meeting
