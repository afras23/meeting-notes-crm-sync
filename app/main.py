"""
FastAPI application entry point.

Creates the API app with middleware, dependency wiring, and routes.
"""

# Standard library
from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

# Third party
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# Local
from app.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging, correlation_id_ctx, get_correlation_id_from_headers
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

    @app.middleware("http")
    async def correlation_id_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Any]],
    ) -> Any:
        incoming_headers = {k.lower(): v for k, v in request.headers.items()}
        correlation_id = get_correlation_id_from_headers(incoming_headers) or str(uuid4())
        token = correlation_id_ctx.set(correlation_id)
        try:
            response = await call_next(request)
            response.headers["x-correlation-id"] = correlation_id
            return response
        finally:
            correlation_id_ctx.reset(token)

    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        details = exc.to_details()
        logger.warning(
            "Application error",
            extra={
                "error_code": details.error_code,
                "message": details.message,
                "context": details.context,
            },
        )
        status_map = {
            "VALIDATION_FAILED": 422,
            "RATE_LIMITED": 429,
            "COST_LIMIT": 503,
            "EXTRACTION_FAILED": 500,
        }
        return JSONResponse(
            status_code=status_map.get(details.error_code, 500),
            content={
                "error": details.error_code,
                "message": details.message,
                "details": details.context,
            },
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
