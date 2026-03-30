"""
Meeting series identifier tests.
"""

# Standard library
from __future__ import annotations

# Local
from app.services.meeting_series_service import compute_meeting_series_id


def test_meeting_series_id_stable_for_same_deal_and_project() -> None:
    a = compute_meeting_series_id(deal_id="d1", project_id=None)
    b = compute_meeting_series_id(deal_id="d1", project_id=None)
    assert a == b


def test_meeting_series_id_differs_when_project_changes() -> None:
    a = compute_meeting_series_id(deal_id="d1", project_id=None)
    b = compute_meeting_series_id(deal_id="d1", project_id="p1")
    assert a != b
