"""
Async SQLAlchemy engine and session factory.
"""

# Standard library
from __future__ import annotations

from collections.abc import AsyncIterator

# Third party
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Local
from app.config import get_settings
from app.db.base import Base

import app.db.tables  # noqa: F401  # register ORM models with Base.metadata

_engine = None
_session_factory = None


def reset_engine() -> None:
    """Reset singleton engine (tests)."""

    global _engine, _session_factory
    _engine = None
    _session_factory = None


def get_engine() -> AsyncEngine:
    """Return singleton async engine."""

    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(settings.database_url, echo=False)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return singleton session factory."""

    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return _session_factory


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding an async session."""

    factory = get_session_factory()
    async with factory() as session:
        yield session


async def init_db() -> None:
    """Create tables (tests/dev without Alembic)."""

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
