"""
Pagination schemas.
"""

# Standard library
from __future__ import annotations

from typing import Generic, TypeVar

# Third party
from pydantic import BaseModel, Field

T = TypeVar("T")


class PageInfo(BaseModel):
    page: int = Field(..., ge=1, description="1-indexed page number.")
    page_size: int = Field(..., ge=1, le=200, description="Items per page.")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T] = Field(default_factory=list, description="Page items.")
    page_info: PageInfo
