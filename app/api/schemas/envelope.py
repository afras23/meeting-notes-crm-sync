"""
Consistent API response envelopes.
"""

# Standard library
from __future__ import annotations

from typing import Generic, TypeVar

# Third party
from pydantic import BaseModel, Field

T = TypeVar("T")


class ResponseMetadata(BaseModel):
    correlation_id: str = Field(..., description="Request correlation identifier.")


class SuccessEnvelope(BaseModel, Generic[T]):
    status: str = Field(default="success", description="success")
    data: T
    metadata: ResponseMetadata


class ErrorBody(BaseModel):
    code: str = Field(..., description="Stable error code.")
    message: str = Field(..., description="Human readable error message.")


class ErrorEnvelope(BaseModel):
    status: str = Field(default="error", description="error")
    error: ErrorBody
    metadata: ResponseMetadata
