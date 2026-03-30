"""
Notification service.

Sends Slack/email notifications based on processing outcomes and configured rules.
"""

# Standard library
from __future__ import annotations

from pathlib import Path
from typing import Any, cast

# Third party
import yaml
from sqlalchemy.ext.asyncio import AsyncSession

# Local
from app.core.retry import retry_async
from app.integrations.email_client import EmailClientMock
from app.integrations.slack_client import SlackClientMock
from app.models.meeting import Meeting
from app.repositories.notification_repository import NotificationRepository


class NotificationService:
    """Applies notification rules and sends messages via integration clients."""

    def __init__(
        self,
        *,
        slack_client: SlackClientMock,
        email_client: EmailClientMock,
        notification_repository: NotificationRepository,
        slack_webhook_url: str,
        email_from: str,
        email_to: str,
        rules_path: str = "config/notification_rules.yaml",
    ) -> None:
        self._slack = slack_client
        self._email = email_client
        self._notification_repository = notification_repository
        self._slack_webhook_url = slack_webhook_url
        self._email_from = email_from
        self._email_to = email_to
        self._rules_path = rules_path

    async def notify_meeting_events(
        self,
        session: AsyncSession,
        *,
        meeting: Meeting,
        crm_result: dict[str, Any],
    ) -> None:
        """
        Evaluate rules and send notifications for meeting lifecycle events.

        Args:
            session: DB session for notification audit rows.
            meeting: Processed meeting.
            crm_result: Output from CRMService.apply_updates.
        """

        changed = cast(dict[str, Any], crm_result.get("changed_properties") or {})
        rules = self._load_rules()

        for rule in rules:
            when_cfg = rule.get("when", {})
            when_dict = cast(dict[str, Any], when_cfg) if isinstance(when_cfg, dict) else {}
            event_name = str(when_dict.get("event") or "")

            if not self._rule_applies(
                event_name=event_name,
                when_dict=when_dict,
                meeting=meeting,
                changed_properties=changed,
            ):
                continue

            notify_cfg = rule.get("notify", {})
            notify_dict = cast(dict[str, Any], notify_cfg) if isinstance(notify_cfg, dict) else {}

            webhook = str(notify_dict.get("slack_webhook_url") or self._slack_webhook_url)
            if bool(notify_dict.get("slack")) and webhook:
                text = self._slack_text(
                    event_name=event_name or "meeting", meeting=meeting, crm_result=crm_result
                )
                payload: dict[str, object] = {"text": text}
                await self._post_slack_with_retry(webhook, payload)
                await self._notification_repository.create(
                    session,
                    meeting_id=meeting.id,
                    channel="slack",
                    event_type=event_name or "slack",
                    payload=payload,
                )

            if bool(notify_dict.get("email")) and self._email_to:
                subject = f"Meeting summary: {meeting.title}"
                body = (
                    f"{meeting.extraction.summary}\n\n"
                    f"Next steps: {meeting.extraction.next_steps or '—'}\n"
                    f"Follow-up: {meeting.extraction.follow_up_date or '—'}"
                )
                await self._email.send_meeting_summary(
                    to_addr=self._email_to,
                    from_addr=self._email_from,
                    subject=subject,
                    body_text=body,
                )
                await self._notification_repository.create(
                    session,
                    meeting_id=meeting.id,
                    channel="email",
                    event_type=event_name or "email",
                    payload={"subject": subject, "body_preview": body[:200]},
                )

    async def _post_slack_with_retry(self, webhook_url: str, payload: dict[str, object]) -> None:
        """Send Slack webhook with bounded retries (transient network errors)."""

        async def send() -> None:
            await self._slack.post_webhook(webhook_url, payload)

        await retry_async(send, attempts=3)

    def _rule_applies(
        self,
        *,
        event_name: str,
        when_dict: dict[str, Any],
        meeting: Meeting,
        changed_properties: dict[str, Any],
    ) -> bool:
        if event_name == "new_action_items":
            return bool(meeting.extraction.action_items)
        if event_name == "deal_stage_change":
            return "dealstage" in changed_properties
        if event_name == "meeting_processed":
            return True
        if event_name == "low_confidence":
            threshold_raw = when_dict.get("confidence_lt", 0.85)
            threshold = (
                float(threshold_raw) if isinstance(threshold_raw, int | float | str) else 0.85
            )
            return meeting.confidence < threshold
        return False

    def _slack_text(
        self,
        *,
        event_name: str,
        meeting: Meeting,
        crm_result: dict[str, Any],
    ) -> str:
        changed = crm_result.get("changed_properties") or {}
        return (
            f"[{event_name}] {meeting.title}\n"
            f"Confidence: {meeting.confidence:.2f}\n"
            f"CRM changes: {changed!s}"
        )

    def _load_rules(self) -> list[dict[str, Any]]:
        rules_path = Path(self._rules_path)
        if not rules_path.exists():
            return []
        raw = yaml.safe_load(rules_path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            return []
        rules = raw.get("rules") or []
        if not isinstance(rules, list):
            return []
        return [cast(dict[str, Any], r) for r in rules if isinstance(r, dict)]
