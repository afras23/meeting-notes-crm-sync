"""
Audit repository.

Provides persistence abstraction for audit entries (in-memory implementation by default).
"""

# Standard library
from __future__ import annotations

from dataclasses import dataclass, field

# Local
from app.models.audit import AuditEntry


@dataclass
class AuditRepository:
    """In-memory repository for audit entries."""

    _entries_by_id: dict[str, AuditEntry] = field(default_factory=dict)
    _entries_by_hash: dict[str, AuditEntry] = field(default_factory=dict)

    async def upsert(self, entry: AuditEntry) -> None:
        """Insert or update audit entry."""

        self._entries_by_id[entry.id] = entry
        self._entries_by_hash[entry.input_hash] = entry

    async def find_by_input_hash(self, input_hash: str) -> AuditEntry | None:
        """Return existing audit entry for the given input hash."""

        return self._entries_by_hash.get(input_hash)

    async def get(self, audit_id: str) -> AuditEntry | None:
        """Get an audit entry by id."""

        return self._entries_by_id.get(audit_id)
