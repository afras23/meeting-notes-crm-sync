"""
Application configuration.

Loads validated settings from environment variables for consistent behavior across environments.
"""

# Standard library
from __future__ import annotations

from functools import lru_cache

# Third party
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated application settings loaded from environment variables."""

    # Application
    app_env: str = Field(default="development", description="development|test|staging|production")
    debug: bool = Field(default=False, description="Enable debug mode (dev only).")
    log_level: str = Field(default="INFO", description="DEBUG|INFO|WARNING|ERROR|CRITICAL")
    api_prefix: str = Field(default="/api/v1", description="API route prefix.")

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./app.db",
        description="Async SQLAlchemy database URL (e.g. sqlite+aiosqlite:///./app.db).",
    )

    # AI
    ai_provider: str = Field(default="mock", description="mock|anthropic|openai")
    ai_model: str = Field(default="mock-llm", description="Model identifier for cost tracking.")
    max_daily_cost_usd: float = Field(default=5.0, ge=0.0, description="Daily AI spend limit.")
    ai_timeout_seconds: int = Field(default=30, ge=1, le=300, description="AI request timeout.")

    # CRM
    crm_provider: str = Field(default="hubspot_mock", description="hubspot_mock")
    crm_mapping_crm: str = Field(
        default="hubspot",
        description="Key under crm_mappings in config/crm_mapping.yaml.",
    )

    # Notifications
    slack_webhook_url: str = Field(default="", description="Default Slack webhook URL (optional).")
    email_from: str = Field(
        default="no-reply@example.com", description="Sender email for notifications."
    )
    email_to: str = Field(default="", description="Recipient email for notifications (optional).")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance for the current process."""

    return Settings()
