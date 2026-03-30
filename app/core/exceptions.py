"""
Application exception hierarchy.

Defines consistent, structured errors used for API responses and observability.
"""

# Standard library
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorDetails:
    """Structured details for application errors."""

    error_code: str
    message: str
    context: dict[str, object]


class AppError(Exception):
    """Base application error with stable error code and structured context."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str = "INTERNAL_ERROR",
        context: dict[str, object] | None = None,
    ) -> None:
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        super().__init__(message)

    def to_details(self) -> ErrorDetails:
        """Convert error into serializable error details."""

        return ErrorDetails(error_code=self.error_code, message=self.message, context=self.context)


class ValidationFailed(AppError):
    """Input or AI output validation failure."""

    def __init__(self, message: str, *, context: dict[str, object] | None = None) -> None:
        super().__init__(message, error_code="VALIDATION_FAILED", context=context)


class ExtractionFailed(AppError):
    """AI extraction failed after retries or returned unusable output."""

    def __init__(self, message: str, *, context: dict[str, object] | None = None) -> None:
        super().__init__(message, error_code="EXTRACTION_FAILED", context=context)


class RateLimited(AppError):
    """External provider rate limited the request."""

    def __init__(self, message: str, *, retry_after_seconds: float | None = None) -> None:
        context: dict[str, object] = {}
        if retry_after_seconds is not None:
            context["retry_after_seconds"] = retry_after_seconds
        super().__init__(message, error_code="RATE_LIMITED", context=context)


class CostLimitExceeded(AppError):
    """Daily AI cost budget exceeded."""

    def __init__(self, current_cost_usd: float, limit_usd: float) -> None:
        super().__init__(
            "Daily AI cost budget exceeded",
            error_code="COST_LIMIT",
            context={"current_cost_usd": current_cost_usd, "limit_usd": limit_usd},
        )
