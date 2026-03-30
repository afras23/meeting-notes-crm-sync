"""
Transcription service.

Accepts pre-transcribed text and provides a placeholder interface for audio transcription.
"""

# Standard library
from __future__ import annotations

import logging

# Local
from app.core.exceptions import ValidationFailed

logger = logging.getLogger(__name__)


class TranscriptionService:
    """Converts audio to text or accepts already-transcribed content."""

    async def get_transcript(
        self,
        *,
        transcript_text: str | None,
        audio_bytes: bytes | None,
    ) -> str:
        """
        Produce a transcript.

        Args:
            transcript_text: Pre-transcribed meeting text.
            audio_bytes: Raw audio bytes (optional).

        Returns:
            Transcript text.

        Raises:
            ValidationFailed: If neither transcript_text nor audio_bytes are provided.
        """

        if transcript_text and transcript_text.strip():
            return transcript_text.strip()

        if audio_bytes is not None:
            raise ValidationFailed(
                "Audio transcription is not enabled in this starter rebuild. Provide transcript_text instead.",
                context={"audio_bytes_length": len(audio_bytes)},
            )

        raise ValidationFailed("Provide transcript_text or audio_bytes.", context={})
