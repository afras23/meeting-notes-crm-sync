"""
Notification rules with mocked Slack and email (no network).
"""

# Standard library
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

# Local
from app.integrations.email_client import EmailClientMock
from app.integrations.slack_client import SlackClientMock
from app.models.action_item import ActionItem
from app.models.extraction import MeetingExtraction
from app.models.meeting import Meeting
from app.repositories.notification_repository import NotificationRepository
from app.services.notification_service import NotificationService


def _meeting_with_actions() -> Meeting:
    extraction = MeetingExtraction(
        title="Sync",
        summary="Summary body.",
        action_items=[ActionItem(description="Do the thing", status="open")],
        next_steps="Next: deploy",
        confidence=0.9,
    )
    return Meeting(
        id="m1",
        meeting_series_id="s1",
        deal_id="d1",
        project_id=None,
        title="Sync",
        occurred_at=datetime.now(UTC),
        transcript="x",
        extraction=extraction,
        confidence=0.9,
    )


@pytest.mark.asyncio
async def test_slack_notification_sent_on_deal_stage_change(tmp_path: Path) -> None:
    rules = tmp_path / "rules.yaml"
    rules.write_text(
        "\n".join(
            [
                "rules:",
                "  - when: { event: deal_stage_change }",
                "    notify: { slack: true, slack_webhook_url: 'https://hooks.slack.com/test' }",
            ]
        ),
        encoding="utf-8",
    )
    slack = SlackClientMock()
    svc = NotificationService(
        slack_client=slack,
        email_client=EmailClientMock(),
        notification_repository=NotificationRepository(),
        slack_webhook_url="",
        email_from="a@example.com",
        email_to="",
        rules_path=str(rules),
    )
    meeting = _meeting_with_actions()
    session = AsyncMock()
    await svc.notify_meeting_events(
        session,
        meeting=meeting,
        crm_result={"changed_properties": {"dealstage": "proposal"}},
    )
    assert slack.sent_messages
    url = slack.sent_messages[0]["webhook_url"]
    assert isinstance(url, str)
    assert "hooks.slack.com" in url


@pytest.mark.asyncio
async def test_slack_notification_sent_on_new_action_items(tmp_path: Path) -> None:
    rules = tmp_path / "rules.yaml"
    rules.write_text(
        "\n".join(
            [
                "rules:",
                "  - when: { event: new_action_items }",
                "    notify: { slack: true, slack_webhook_url: 'https://hooks.slack.com/a' }",
            ]
        ),
        encoding="utf-8",
    )
    slack = SlackClientMock()
    svc = NotificationService(
        slack_client=slack,
        email_client=EmailClientMock(),
        notification_repository=NotificationRepository(),
        slack_webhook_url="",
        email_from="a@example.com",
        email_to="",
        rules_path=str(rules),
    )
    meeting = _meeting_with_actions()
    session = AsyncMock()
    await svc.notify_meeting_events(session, meeting=meeting, crm_result={"changed_properties": {}})
    assert slack.sent_messages


@pytest.mark.asyncio
async def test_email_summary_format_includes_all_sections(tmp_path: Path) -> None:
    rules = tmp_path / "rules.yaml"
    rules.write_text(
        "\n".join(
            [
                "rules:",
                "  - when: { event: meeting_processed }",
                "    notify: { email: true }",
            ]
        ),
        encoding="utf-8",
    )
    email = EmailClientMock()
    svc = NotificationService(
        slack_client=SlackClientMock(),
        email_client=email,
        notification_repository=NotificationRepository(),
        slack_webhook_url="",
        email_from="from@example.com",
        email_to="to@example.com",
        rules_path=str(rules),
    )
    meeting = _meeting_with_actions()
    session = AsyncMock()
    await svc.notify_meeting_events(session, meeting=meeting, crm_result={"changed_properties": {}})
    assert email.sent_messages
    body = email.sent_messages[0]["body"]
    assert "Summary body" in body or meeting.extraction.summary in body
    assert "Next steps" in body or "Next:" in body
