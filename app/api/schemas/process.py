"""
Process endpoint schemas.
"""

# Standard library
from __future__ import annotations

from typing import Literal

# Third party
from pydantic import BaseModel, Field


class ProcessRequest(BaseModel):
    text: str | None = Field(
        default=None,
        description="Pre-transcribed meeting text (when input_type=text).",
        examples=["Speaker 1: Hello\nSpeaker 2: Hi there"],
    )
    deal_id: str | None = Field(
        default=None, description="Optional CRM deal id for linking/updates."
    )
    project_id: str | None = Field(
        default=None, description="Optional project id for series linking."
    )
    input_type: Literal["text"] = Field(default="text", description="Input type discriminator.")


class ProcessResponse(BaseModel):
    meeting_id: str = Field(..., description="Meeting identifier.")
    status: Literal["accepted"] = Field(default="accepted", description="Processing status.")
