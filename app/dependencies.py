"""
Dependency injection providers.

Centralizes construction of services, repositories, and integration clients for testability.
"""

# Standard library
from __future__ import annotations

from functools import lru_cache

# Local
from app.config import get_settings
from app.core.circuit_breaker import CircuitBreaker
from app.db.session import get_db_session
from app.integrations.calendar_client import CalendarClientMock
from app.integrations.email_client import EmailClientMock
from app.integrations.hubspot_client import HubSpotClientMock
from app.integrations.slack_client import SlackClientMock
from app.repositories.action_item_repository import ActionItemRepository
from app.repositories.audit_repository import AuditRepository
from app.repositories.crm_sync_repository import CrmSyncRepository
from app.repositories.meeting_repository import MeetingRepository
from app.repositories.notification_repository import NotificationRepository
from app.services.ai.client import AIClient
from app.services.crm_service import CRMService
from app.services.extraction_service import ExtractionService
from app.services.notification_service import NotificationService
from app.services.process_service import MeetingProcessService
from app.services.transcription_service import LlmClient, TranscriptionService


@lru_cache
def get_ai_client() -> AIClient:
    """Get singleton AI client instance."""

    settings = get_settings()
    breaker = CircuitBreaker(
        failure_threshold=settings.ai_circuit_failure_threshold,
        recovery_seconds=settings.ai_circuit_recovery_seconds,
    )
    return AIClient(
        provider=settings.ai_provider,
        model=settings.ai_model,
        max_daily_cost_usd=settings.max_daily_cost_usd,
        timeout_seconds=settings.ai_timeout_seconds,
        circuit_breaker=breaker,
    )


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


@lru_cache
def get_email_client() -> EmailClientMock:
    """Get email client instance (mock implementation)."""

    return EmailClientMock()


@lru_cache
def get_calendar_client() -> CalendarClientMock:
    """Get calendar client instance (mock implementation)."""

    return CalendarClientMock()


def get_meeting_repository() -> MeetingRepository:
    """Construct meeting repository."""

    return MeetingRepository()


def get_action_item_repository() -> ActionItemRepository:
    """Construct action item repository."""

    return ActionItemRepository()


def get_crm_sync_repository() -> CrmSyncRepository:
    """Construct CRM sync audit repository."""

    return CrmSyncRepository()


def get_notification_repository() -> NotificationRepository:
    """Construct notification audit repository."""

    return NotificationRepository()


def get_notification_repo() -> NotificationRepository:
    """FastAPI dependency provider for notification repository."""

    return get_notification_repository()


def get_transcription_service() -> TranscriptionService:
    """Construct transcription service."""

    settings = get_settings()
    return TranscriptionService(LlmClient(ai=get_ai_client()), settings)


def get_process_service() -> MeetingProcessService:
    """Construct process orchestration service."""

    return MeetingProcessService(
        get_transcription_service(),
        get_extraction_service(),
        get_crm_service(),
        get_notification_service(),
        get_meeting_repository(),
        get_crm_sync_repository(),
        get_audit_repository(),
    )


def get_extraction_service() -> ExtractionService:
    """Construct extraction service with dependencies."""

    return ExtractionService(ai_client=get_ai_client(), audit_repository=get_audit_repository())


def get_crm_service() -> CRMService:
    """Construct CRM service."""

    settings = get_settings()
    return CRMService(
        crm_client=get_crm_client(),
        crm_key=settings.crm_mapping_crm,
    )


def get_notification_service() -> NotificationService:
    """Construct notification service."""

    settings = get_settings()
    return NotificationService(
        slack_client=get_slack_client(),
        email_client=get_email_client(),
        notification_repository=get_notification_repository(),
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


def get_crm_sync_repo() -> CrmSyncRepository:
    """FastAPI dependency for CRM sync repository."""

    return get_crm_sync_repository()


__all__ = [
    "get_action_item_repository",
    "get_action_repo",
    "get_ai_client",
    "get_audit_repository",
    "get_calendar_client",
    "get_crm_client",
    "get_crm_service",
    "get_crm_sync_repo",
    "get_crm_sync_repository",
    "get_db_session",
    "get_email_client",
    "get_extraction_service",
    "get_meeting_repo",
    "get_meeting_repository",
    "get_notification_repo",
    "get_notification_repository",
    "get_notification_service",
    "get_process_service",
    "get_slack_client",
    "get_transcription_service",
]
