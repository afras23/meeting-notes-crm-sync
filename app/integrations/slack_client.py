"""
Slack client (mock).

Provides a minimal interface for sending Slack notifications without external calls.
"""

# Standard library
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SlackClientMock:
    """Mock Slack client that records sent messages."""

    sent_messages: list[dict[str, object]] = field(default_factory=list)

    async def post_webhook(self, webhook_url: str, payload: dict[str, object]) -> None:
        """
        Record a Slack webhook post.

        Args:
            webhook_url: Slack webhook URL.
            payload: Slack message payload.
        """

        self.sent_messages.append({"webhook_url": webhook_url, "payload": payload})
