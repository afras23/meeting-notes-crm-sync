"""
Action items endpoints.

Provides access to extracted action items.
"""

# Standard library
from __future__ import annotations

# Third party
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

# Local
from app.dependencies import get_action_repo, get_db_session
from app.models.action_item import ActionItem
from app.repositories.action_item_repository import ActionItemRepository

router = APIRouter()


class ListActionItemsResponse(BaseModel):
    """Response for action item list endpoints."""

    action_items: list[ActionItem] = Field(default_factory=list, description="Action items.")


@router.get("/meetings/{meeting_id}/actions", response_model=ListActionItemsResponse)
async def list_actions_for_meeting(
    meeting_id: str,
    session: AsyncSession = Depends(get_db_session),
    action_repo: ActionItemRepository = Depends(get_action_repo),
) -> ListActionItemsResponse:
    """List action items for a meeting."""

    action_items = await action_repo.list_by_meeting(session, meeting_id)
    return ListActionItemsResponse(action_items=action_items)
