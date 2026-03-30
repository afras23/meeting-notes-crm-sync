"""
Action item repository.

Provides persistence abstraction for action items (in-memory implementation by default).
"""

# Standard library
from __future__ import annotations

from dataclasses import dataclass, field

# Local
from app.models.action_item import ActionItem


@dataclass
class ActionItemRepository:
    """In-memory repository for action items."""

    _actions_by_id: dict[str, ActionItem] = field(default_factory=dict)

    async def upsert(self, action_item: ActionItem) -> None:
        """Insert or update an action item record."""

        self._actions_by_id[action_item.id] = action_item

    async def get(self, action_item_id: str) -> ActionItem | None:
        """Get an action item by id."""

        return self._actions_by_id.get(action_item_id)

    async def list_by_meeting(self, meeting_id: str) -> list[ActionItem]:
        """List action items for a meeting."""

        return [a for a in self._actions_by_id.values() if a.meeting_id == meeting_id]
