"""
Pytest fixtures.

Provides shared app instance and helpers for API and unit tests.
"""

# Standard library
from __future__ import annotations

import os

# Third party
import pytest
from fastapi import FastAPI

# Local
from app.config import get_settings
from app.main import create_app


@pytest.fixture(autouse=True)
def _test_env() -> None:
    """Force safe defaults for tests."""

    os.environ.setdefault("APP_ENV", "test")
    os.environ.setdefault("AI_PROVIDER", "mock")


@pytest.fixture
def app() -> FastAPI:
    """FastAPI app instance for tests."""

    _ = get_settings()
    return create_app()
