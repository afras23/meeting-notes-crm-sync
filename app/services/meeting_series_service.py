"""
Meeting series identifier resolution.

Links meetings that share a deal or project.
"""

# Standard library
from __future__ import annotations

import hashlib


def compute_meeting_series_id(*, deal_id: str | None, project_id: str | None) -> str:
    """
    Compute a stable series id from deal and/or project identifiers.

    Args:
        deal_id: CRM deal id when known.
        project_id: Internal project id when known.

    Returns:
        Hex string series id (deterministic for the same inputs).
    """

    key = f"deal:{deal_id or ''}|project:{project_id or ''}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
