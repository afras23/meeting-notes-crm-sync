"""
HubSpot client (mock).

Provides a minimal interface for CRM updates without calling real external APIs.
"""

# Standard library
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class HubSpotClientMock:
    """Mock HubSpot client that records updates for tests and debugging."""

    applied_updates: list[dict[str, object]] = field(default_factory=list)

    async def update_deal(self, deal_id: str, properties: dict[str, object]) -> None:
        """
        Record a deal update.

        Args:
            deal_id: HubSpot deal identifier.
            properties: Deal properties to update.
        """

        self.applied_updates.append(
            {"entity": "deal", "deal_id": deal_id, "properties": properties}
        )
