"""
Notification service.

Sends Slack/email notifications based on processing outcomes and configured rules.
"""

# Standard library
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, cast

# Third party
import yaml

# Local
from app.integrations.slack_client import SlackClientMock
from app.models.meeting import Meeting

logger = logging.getLogger(__name__)


class NotificationService:
    """Applies notification rules and sends messages via integration clients."""

    def __init__(
        self,
        *,
        slack_client: SlackClientMock,
        slack_webhook_url: str,
        email_from: str,
        email_to: str,
        rules_path: str = "config/notification_rules.yaml",
    ) -> None:
        self._slack = slack_client
        self._slack_webhook_url = slack_webhook_url
        self._email_from = email_from
        self._email_to = email_to
        self._rules_path = rules_path

    async def notify_for_meeting(self, *, meeting: Meeting) -> None:
        """
        Send notifications as configured.

        Args:
            meeting: Processed meeting record.
        """

        rules = self._load_rules()
        for rule in rules:
            when_cfg = rule.get("when", {})
            when_cfg_dict = cast(dict[str, Any], when_cfg) if isinstance(when_cfg, dict) else {}
            threshold_raw = when_cfg_dict.get("confidence_lt", -1)
            threshold = (
                float(threshold_raw) if isinstance(threshold_raw, int | float | str) else -1.0
            )
            if threshold >= 0 and meeting.confidence < threshold:
                notify_cfg = rule.get("notify", {})
                notify_cfg_dict = (
                    cast(dict[str, Any], notify_cfg) if isinstance(notify_cfg, dict) else {}
                )
                if bool(notify_cfg_dict.get("slack")):
                    await self._notify_slack_low_confidence(meeting=meeting, threshold=threshold)

    async def _notify_slack_low_confidence(self, *, meeting: Meeting, threshold: float) -> None:
        if not self._slack_webhook_url:
            logger.info(
                "Slack webhook not configured; skipping Slack notification",
                extra={"meeting_id": meeting.id},
            )
            return

        payload: dict[str, object] = {
            "text": (
                f"Low confidence meeting extraction ({meeting.confidence:.2f} < {threshold:.2f}). "
                f"Meeting: {meeting.title}"
            )
        }
        await self._slack.post_webhook(self._slack_webhook_url, payload)
        logger.info(
            "Sent Slack notification", extra={"meeting_id": meeting.id, "rule": "low_confidence"}
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
