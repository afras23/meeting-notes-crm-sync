"""
FastAPI application entry point.

Creates the API app with middleware, dependency wiring, and routes.
"""

# Standard library
from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

# Third party
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# Local
from app.api.schemas.envelope import ErrorBody, ErrorEnvelope, ResponseMetadata
from app.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging, correlation_id_ctx
from app.core.middleware.correlation import correlation_id_middleware
from app.core.middleware.rate_limit import RateLimiter, build_rate_limit_middleware
from app.core.middleware.request_logging import request_logging_middleware
from app.db.session import init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Application startup/shutdown lifecycle."""

    settings = get_settings()
    configure_logging(log_level=settings.log_level)
    logger.info("Application starting", extra={"env": settings.app_env})
    if settings.app_env in ("development", "test"):
        await init_db()
    yield
    logger.info("Application shutting down")


def create_app() -> FastAPI:
    """Create FastAPI app instance."""

    settings = get_settings()
    app = FastAPI(title="Meeting Notes → CRM Sync", version="1.0.0", lifespan=lifespan)

    limiter = RateLimiter(requests_per_minute=settings.rate_limit_requests_per_minute)
    app.middleware("http")(build_rate_limit_middleware(limiter=limiter, enabled=True))
    app.middleware("http")(correlation_id_middleware)
    app.middleware("http")(request_logging_middleware)

    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        details = exc.to_details()
        logger.warning(
            "Application error",
            extra={
                "error_code": details.error_code,
                "error_message": details.message,
                "error_context": details.context,
            },
        )
        status_map = {
            "VALIDATION_FAILED": 422,
            "RATE_LIMITED": 429,
            "COST_LIMIT": 503,
            "EXTRACTION_FAILED": 500,
            "TOO_MANY_REQUESTS": 429,
            "DUPLICATE": 409,
            "NOT_FOUND": 404,
        }
        correlation_id = correlation_id_ctx.get() or ""
        return JSONResponse(
            status_code=status_map.get(details.error_code, 500),
            content=ErrorEnvelope(
                error=ErrorBody(code=details.error_code, message=details.message),
                metadata=ResponseMetadata(correlation_id=correlation_id),
            ).model_dump(mode="json"),
        )

    # Routes
    from app.api.routes.actions import router as actions_router
    from app.api.routes.health import router as health_router
    from app.api.routes.meetings import router as meetings_router
    from app.api.routes.process import router as process_router

    app.include_router(health_router, prefix=settings.api_prefix, tags=["health"])
    app.include_router(process_router, prefix=settings.api_prefix, tags=["process"])
    app.include_router(meetings_router, prefix=settings.api_prefix, tags=["meetings"])
    app.include_router(actions_router, prefix=settings.api_prefix, tags=["actions"])

    return app


app = create_app()
