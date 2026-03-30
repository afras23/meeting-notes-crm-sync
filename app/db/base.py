"""
Declarative base for SQLAlchemy ORM models.
"""

# Standard library
from __future__ import annotations

# Third party
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Application ORM base."""
