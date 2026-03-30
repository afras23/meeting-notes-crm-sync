"""
Action items API schemas.
"""

# Standard library
from __future__ import annotations

from typing import Literal

# Third party
from pydantic import BaseModel, Field

# Local
from app.api.schemas.pagination import PaginatedResponse
from app.models.action_item import ActionItem


class ActionListResponse(BaseModel):
    actions: PaginatedResponse[ActionItem] = Field(..., description="Paginated action items.")


class ActionUpdateRequest(BaseModel):
    status: Literal["open", "done"] = Field(..., description="Updated status.")


class ActionResponse(BaseModel):
    action: ActionItem = Field(..., description="Action item.")
