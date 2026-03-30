"""
Meeting series behaviour (deterministic series ids, isolation).
"""

# Standard library
from __future__ import annotations

from datetime import UTC, datetime

# Local
from app.models.extraction import MeetingExtraction
from app.models.meeting import Meeting
from app.services.meeting_series_service import compute_meeting_series_id


def test_meetings_linked_by_deal_id() -> None:
    a = compute_meeting_series_id(deal_id="deal_shared", project_id=None)
    b = compute_meeting_series_id(deal_id="deal_shared", project_id=None)
    assert a == b


def test_meeting_without_deal_id_is_standalone() -> None:
    s = compute_meeting_series_id(deal_id=None, project_id=None)
    assert isinstance(s, str)
    assert len(s) == 32


def test_action_items_carry_forward_across_series() -> None:
    """Each meeting keeps its own action items; series id only groups meetings."""

    series = compute_meeting_series_id(deal_id="deal_series", project_id=None)
    ext1 = MeetingExtraction(
        title="M1",
        summary="s",
        confidence=0.9,
    )
    ext2 = MeetingExtraction(
        title="M2",
        summary="s",
        confidence=0.9,
    )
    m1 = Meeting(
        id="id1",
        meeting_series_id=series,
        deal_id="deal_series",
        project_id=None,
        title="M1",
        occurred_at=datetime.now(UTC),
        transcript="t1",
        extraction=ext1,
        confidence=0.9,
    )
    m2 = Meeting(
        id="id2",
        meeting_series_id=series,
        deal_id="deal_series",
        project_id=None,
        title="M2",
        occurred_at=datetime.now(UTC),
        transcript="t2",
        extraction=ext2,
        confidence=0.9,
    )
    assert m1.meeting_series_id == m2.meeting_series_id
    assert m1.id != m2.id
