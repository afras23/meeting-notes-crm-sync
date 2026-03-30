"""
HubSpot client (mock).

Realistic in-memory CRM: contacts, deals, notes, and audit trail for tests.
"""

# Standard library
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class HubSpotClientMock:
    """
    Mock HubSpot API with CRUD-style operations.

    Stores deals and contacts in memory; records all mutations for assertions.
    """

    deals: dict[str, dict[str, Any]] = field(default_factory=dict)
    contacts: dict[str, dict[str, Any]] = field(default_factory=dict)
    notes: list[dict[str, Any]] = field(default_factory=list)
    applied_updates: list[dict[str, Any]] = field(default_factory=list)

    def seed_deal(self, deal_id: str, properties: dict[str, Any]) -> None:
        """Initialize a deal for diff-detection tests."""

        self.deals[deal_id] = dict(properties)

    async def get_deal(self, deal_id: str) -> dict[str, Any] | None:
        """Return current deal properties or None."""

        deal = self.deals.get(deal_id)
        return dict(deal) if deal is not None else None

    async def update_deal(self, deal_id: str, properties: dict[str, Any]) -> None:
        """
        Merge properties into a deal (partial update).

        Args:
            deal_id: HubSpot deal id.
            properties: Fields to set (only changed fields expected from CRM service).
        """

        if deal_id not in self.deals:
            self.deals[deal_id] = {}
        self.deals[deal_id].update(properties)
        entry = {"entity": "deal", "deal_id": deal_id, "properties": dict(properties)}
        self.applied_updates.append(entry)

    async def create_contact(self, properties: dict[str, Any]) -> str:
        """
        Create a contact; returns synthetic id.

        Args:
            properties: HubSpot-style contact properties (email, firstname, etc.).
        """

        contact_id = f"contact_{len(self.contacts) + 1}"
        self.contacts[contact_id] = dict(properties)
        self.applied_updates.append(
            {"entity": "contact", "contact_id": contact_id, "properties": dict(properties)}
        )
        return contact_id

    async def add_note(self, *, deal_id: str, body: str) -> str:
        """
        Attach a note to a deal.

        Args:
            deal_id: Deal id.
            body: Note body text.

        Returns:
            Synthetic note id.
        """

        note_id = f"note_{len(self.notes) + 1}"
        self.notes.append({"id": note_id, "deal_id": deal_id, "body": body})
        self.applied_updates.append(
            {"entity": "note", "deal_id": deal_id, "note_id": note_id, "body": body}
        )
        return note_id
