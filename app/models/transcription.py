"""
Transcription models.
"""

# Standard library
from __future__ import annotations

from typing import Literal

# Third party
from pydantic import BaseModel, Field


class SpeakerSegment(BaseModel):
    speaker_id: str = Field(
        ...,
        min_length=1,
        description=(
            "Speaker label from parsing (e.g. heuristic line prefixes); "
            "not guaranteed to be diarisation-derived identity."
        ),
    )
    text: str = Field(..., min_length=1, description="Spoken text content.")
    start_time: float | None = Field(
        default=None,
        ge=0.0,
        description="Segment start time (seconds) if known from a timed/diarised source.",
    )
    end_time: float | None = Field(
        default=None,
        ge=0.0,
        description="Segment end time (seconds) if known from a timed/diarised source.",
    )


class ParsedTranscript(BaseModel):
    raw_text: str = Field(..., min_length=1, description="Original transcript text.")
    speakers: list[SpeakerSegment] = Field(
        default_factory=list,
        description="Segments from heuristic line-based labeling unless upstream supplied labels/timestamps.",
    )


class TranscriptResult(BaseModel):
    raw_text: str = Field(..., min_length=1, description="Raw transcript text output.")
    speakers: list[SpeakerSegment] = Field(
        default_factory=list,
        description="Segments from heuristic line-based labeling unless upstream supplied labels/timestamps.",
    )
    duration_seconds: float = Field(..., ge=0.0, description="Audio duration in seconds.")
    source: Literal["whisper", "pre_transcribed"] = Field(..., description="Transcript source.")
    cost_usd: float = Field(..., ge=0.0, description="Estimated transcription cost in USD.")
    latency_ms: float = Field(..., ge=0.0, description="Transcription latency in milliseconds.")
