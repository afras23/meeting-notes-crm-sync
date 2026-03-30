"""
Audit trail models.

Captures every AI-driven decision with enough context to reproduce and debug outcomes.
"""

# Standard library
from __future__ import annotations

from datetime import datetime

# Third party
from pydantic import BaseModel, Field


class AuditEntry(BaseModel):
    """Audit entry for a single processing run."""

    id: str = Field(..., description="Audit entry identifier.")
    created_at: datetime = Field(..., description="Timestamp in UTC.")
    input_hash: str = Field(..., min_length=1, description="Stable hash of the input transcript.")
    input_preview: str = Field(..., description="First N characters of the input.")
    prompt_name: str = Field(..., description="Prompt template name.")
    prompt_version: str = Field(..., description="Prompt version used.")
    model: str = Field(..., description="AI model identifier.")
    provider: str = Field(..., description="AI provider identifier.")
    latency_ms: float = Field(..., ge=0.0, description="AI call latency in milliseconds.")
    input_tokens: int = Field(..., ge=0, description="Estimated input tokens.")
    output_tokens: int = Field(..., ge=0, description="Estimated output tokens.")
    cost_usd: float = Field(..., ge=0.0, description="Estimated cost in USD.")
    raw_ai_output: str = Field(..., description="Raw AI response content.")
    parsed_output: dict[str, object] = Field(
        default_factory=dict, description="Parsed JSON output."
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score.")
