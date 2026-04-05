"""
Transcription service.

Accepts pre-transcribed text and provides a placeholder interface for audio transcription.
"""

# Standard library
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

# Local
from app.config import Settings
from app.core.exceptions import ValidationFailed
from app.models.transcription import ParsedTranscript, TranscriptResult
from app.services.ai.client import AIClient
from app.services.heuristic_speaker_attribution import parse_heuristic_speaker_segments

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LlmClient:
    """
    Narrow interface for transcription calls.

    This wraps the existing AI client so the integration boundary stays explicit.
    """

    ai: AIClient

    async def ping(self) -> bool:
        return True


def _estimate_audio_duration_seconds(audio_content: bytes) -> float:
    # Heuristic: assume ~32KB/sec compressed audio payload.
    return max(1.0, len(audio_content) / 32_000.0)


def _estimate_transcription_cost_usd(*, duration_seconds: float) -> float:
    # Stable heuristic, roughly aligned with common Whisper pricing ($0.006/min).
    return round((duration_seconds / 60.0) * 0.006, 6)


class TranscriptionService:
    """Accept audio bytes or pre-transcribed text and return structured transcript data.

    Speaker boundaries come from :func:`parse_heuristic_speaker_segments` (line-based
    labels), not from audio speaker diarisation.
    """

    def __init__(self, llm_client: LlmClient, settings: Settings) -> None:
        self._llm_client = llm_client
        self._settings = settings

    async def transcribe(self, audio_content: bytes, filename: str) -> TranscriptResult:
        """Accept audio file, call Whisper API mock, return transcript.

        The mock returns fixed multi-speaker text; segments are still split via
        heuristic line-prefix parsing (see ``heuristic_speaker_attribution``), not
        diarisation from the audio signal.
        """

        if not audio_content:
            raise ValidationFailed("Audio content must be non-empty.", context={})
        if not filename:
            raise ValidationFailed("Filename must be provided for audio input.", context={})

        start = time.monotonic()
        duration_seconds = _estimate_audio_duration_seconds(audio_content)

        logger.info(
            "Whisper mock request",
            extra={
                "filename": filename,
                "bytes": len(audio_content),
                "duration_seconds": round(duration_seconds, 3),
                "provider": self._settings.ai_provider,
            },
        )

        raw_text = (
            "Speaker 1: Thanks everyone for joining. Today we'll review requirements and next steps.\n"
            "Speaker 2: Sounds good. We should also confirm the budget and timeline.\n"
            "Speaker 1: Agreed—I'll send a follow-up with pricing and schedule the technical deep-dive."
        )
        speakers = parse_heuristic_speaker_segments(raw_text)
        latency_ms = (time.monotonic() - start) * 1000.0
        cost_usd = _estimate_transcription_cost_usd(duration_seconds=duration_seconds)

        return TranscriptResult(
            raw_text=raw_text,
            speakers=speakers,
            duration_seconds=duration_seconds,
            source="whisper",
            cost_usd=cost_usd,
            latency_ms=latency_ms,
        )

    async def parse_transcript(self, raw_text: str) -> ParsedTranscript:
        """Parse pre-transcribed text into segments using heuristic speaker labels."""

        text = raw_text.strip()
        if not text:
            raise ValidationFailed("Transcript text must be non-empty.", context={})
        speakers = parse_heuristic_speaker_segments(text)
        return ParsedTranscript(raw_text=text, speakers=speakers)
