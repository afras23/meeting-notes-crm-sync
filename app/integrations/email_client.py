"""
Email client (mock).

Records outbound emails for meeting summaries without sending real mail.
"""

# Standard library
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EmailClientMock:
    """Mock SMTP/email sender that stores messages for tests."""

    sent_messages: list[dict[str, str]] = field(default_factory=list)

    async def send_meeting_summary(
        self,
        *,
        to_addr: str,
        from_addr: str,
        subject: str,
        body_text: str,
    ) -> None:
        """
        Record a meeting summary email.

        Args:
            to_addr: Recipient address.
            from_addr: Sender address.
            subject: Email subject.
            body_text: Plain text body.
        """

        self.sent_messages.append(
            {
                "to": to_addr,
                "from": from_addr,
                "subject": subject,
                "body": body_text,
            }
        )
