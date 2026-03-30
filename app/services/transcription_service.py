"""
Transcription service.

Accepts pre-transcribed text and provides a placeholder interface for audio transcription.
"""

# Standard library
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass

# Local
from app.config import Settings
from app.core.exceptions import ValidationFailed
from app.models.transcription import ParsedTranscript, SpeakerSegment, TranscriptResult
from app.services.ai.client import AIClient

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


_SPEAKER_PREFIX_RE = re.compile(
    r"^\s*(?:\[(?P<bracket>[^\]]+)\]|(?P<label>[A-Za-z][A-Za-z0-9 _.-]{0,40}))\s*:\s*(?P<text>.*)$"
)


def _parse_speaker_segments(raw_text: str) -> list[SpeakerSegment]:
    lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
    segments: list[SpeakerSegment] = []
    current_speaker: str | None = None
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_speaker, current_lines
        if current_speaker is None:
            return
        text = " ".join(current_lines).strip()
        if text:
            segments.append(SpeakerSegment(speaker_id=current_speaker, text=text))
        current_speaker = None
        current_lines = []

    found_any_marker = False
    for line in lines:
        m = _SPEAKER_PREFIX_RE.match(line)
        if m:
            speaker = (m.group("bracket") or m.group("label") or "").strip()
            if speaker:
                found_any_marker = True
                flush()
                current_speaker = speaker
                current_lines = [m.group("text").strip()]
                continue

        if current_speaker is None:
            current_speaker = "Speaker 1"
        current_lines.append(line)

    flush()

    if not found_any_marker:
        collapsed = " ".join(lines).strip()
        if not collapsed:
            return []
        return [SpeakerSegment(speaker_id="Speaker 1", text=collapsed)]

    return segments


class TranscriptionService:
    """Accept audio bytes or pre-transcribed text and return structured transcript data."""

    def __init__(self, llm_client: LlmClient, settings: Settings) -> None:
        self._llm_client = llm_client
        self._settings = settings

    async def transcribe(self, audio_content: bytes, filename: str) -> TranscriptResult:
        """Accept audio file, call Whisper API mock, return transcript."""

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
        speakers = _parse_speaker_segments(raw_text)
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
        """Accept pre-transcribed text, parse into structured format."""

        text = raw_text.strip()
        if not text:
            raise ValidationFailed("Transcript text must be non-empty.", context={})
        speakers = _parse_speaker_segments(text)
        return ParsedTranscript(raw_text=text, speakers=speakers)
