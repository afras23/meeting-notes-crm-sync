"""
Pytest fixtures.

Provides shared app instance and helpers for API and unit tests.
"""

# Standard library
from __future__ import annotations

import asyncio
import os

# Third party
import pytest
from fastapi import FastAPI

# Local
from app.config import get_settings
from app.db.session import init_db, reset_engine
from app.main import create_app


@pytest.fixture(autouse=True)
def _test_env() -> None:
    """Force safe defaults for tests and initialize an in-memory database."""

    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    os.environ.setdefault("APP_ENV", "test")
    os.environ.setdefault("AI_PROVIDER", "mock")
    get_settings.cache_clear()
    reset_engine()
    asyncio.run(init_db())


@pytest.fixture
def app() -> FastAPI:
    """FastAPI app instance for tests."""

    _ = get_settings()
    return create_app()
