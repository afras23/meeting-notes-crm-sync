"""
Notification rule matching tests.
"""

# Standard library
from __future__ import annotations

from datetime import UTC, datetime

# Local
from app.integrations.email_client import EmailClientMock
from app.integrations.slack_client import SlackClientMock
from app.models.action_item import ActionItem
from app.models.extraction import MeetingExtraction
from app.models.meeting import Meeting
from app.repositories.notification_repository import NotificationRepository
from app.services.notification_service import NotificationService


def _meeting(*, confidence: float = 0.9, action_items: list[ActionItem] | None = None) -> Meeting:
    extraction = MeetingExtraction(
        title="T",
        summary="S",
        action_items=action_items or [],
        confidence=confidence,
    )
    return Meeting(
        id="m1",
        meeting_series_id="s1",
        deal_id="d1",
        project_id=None,
        title="T",
        occurred_at=datetime.now(UTC),
        transcript="x",
        extraction=extraction,
        confidence=confidence,
    )


def test_rule_applies_deal_stage_change_when_dealstage_in_diff() -> None:
    svc = NotificationService(
        slack_client=SlackClientMock(),
        email_client=EmailClientMock(),
        notification_repository=NotificationRepository(),
        slack_webhook_url="",
        email_from="a@example.com",
        email_to="",
        rules_path="config/notification_rules.yaml",
    )
    meeting = _meeting()
    assert svc._rule_applies(
        event_name="deal_stage_change",
        when_dict={},
        meeting=meeting,
        changed_properties={"dealstage": "proposal"},
    )


def test_rule_applies_new_action_items() -> None:
    svc = NotificationService(
        slack_client=SlackClientMock(),
        email_client=EmailClientMock(),
        notification_repository=NotificationRepository(),
        slack_webhook_url="",
        email_from="a@example.com",
        email_to="",
        rules_path="config/notification_rules.yaml",
    )
    meeting = _meeting(
        action_items=[ActionItem(description="Do thing", status="open")],
    )
    assert svc._rule_applies(
        event_name="new_action_items",
        when_dict={},
        meeting=meeting,
        changed_properties={},
    )


def test_rule_applies_low_confidence() -> None:
    svc = NotificationService(
        slack_client=SlackClientMock(),
        email_client=EmailClientMock(),
        notification_repository=NotificationRepository(),
        slack_webhook_url="",
        email_from="a@example.com",
        email_to="",
        rules_path="config/notification_rules.yaml",
    )
    meeting = _meeting(confidence=0.5)
    assert svc._rule_applies(
        event_name="low_confidence",
        when_dict={"confidence_lt": 0.85},
        meeting=meeting,
        changed_properties={},
    )
