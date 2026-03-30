"""
Dependency injection providers.

Centralizes construction of services, repositories, and integration clients for testability.
"""

# Standard library
from __future__ import annotations

from functools import lru_cache

# Local
from app.config import get_settings
from app.integrations.hubspot_client import HubSpotClientMock
from app.integrations.slack_client import SlackClientMock
from app.repositories.action_item_repository import ActionItemRepository
from app.repositories.audit_repository import AuditRepository
from app.repositories.meeting_repository import MeetingRepository
from app.services.ai.client import AIClient
from app.services.crm_service import CRMService
from app.services.extraction_service import ExtractionService
from app.services.notification_service import NotificationService
from app.services.transcription_service import TranscriptionService


@lru_cache
def get_ai_client() -> AIClient:
    """Get singleton AI client instance."""

    settings = get_settings()
    return AIClient(
        provider=settings.ai_provider,
        model=settings.ai_model,
        max_daily_cost_usd=settings.max_daily_cost_usd,
        timeout_seconds=settings.ai_timeout_seconds,
    )


@lru_cache
def get_meeting_repository() -> MeetingRepository:
    """Get singleton meeting repository."""

    return MeetingRepository()


@lru_cache
def get_action_item_repository() -> ActionItemRepository:
    """Get singleton action item repository."""

    return ActionItemRepository()


@lru_cache
def get_audit_repository() -> AuditRepository:
    """Get singleton audit repository."""

    return AuditRepository()


@lru_cache
def get_crm_client() -> HubSpotClientMock:
    """Get CRM client instance (mock implementation)."""

    return HubSpotClientMock()


@lru_cache
def get_slack_client() -> SlackClientMock:
    """Get Slack client instance (mock implementation)."""

    return SlackClientMock()


def get_transcription_service() -> TranscriptionService:
    """Construct transcription service."""

    return TranscriptionService()


def get_extraction_service() -> ExtractionService:
    """Construct extraction service with dependencies."""

    return ExtractionService(ai_client=get_ai_client(), audit_repository=get_audit_repository())


def get_crm_service() -> CRMService:
    """Construct CRM service."""

    return CRMService(crm_client=get_crm_client())


def get_notification_service() -> NotificationService:
    """Construct notification service."""

    settings = get_settings()
    return NotificationService(
        slack_client=get_slack_client(),
        slack_webhook_url=settings.slack_webhook_url,
        email_from=settings.email_from,
        email_to=settings.email_to,
    )


def get_meeting_repo() -> MeetingRepository:
    """FastAPI dependency provider for meeting repository."""

    return get_meeting_repository()


def get_action_repo() -> ActionItemRepository:
    """FastAPI dependency provider for action item repository."""

    return get_action_item_repository()
