"""
Transcription service unit tests.
"""

# Standard library
from __future__ import annotations

# Third party
import pytest

# Local
from app.config import Settings
from app.services.ai.client import AIClient
from app.services.transcription_service import LlmClient, TranscriptionService


@pytest.mark.asyncio
async def test_audio_file_calls_whisper_mock_and_returns_transcript() -> None:
    settings = Settings()
    ai = AIClient(provider="mock", model="m", max_daily_cost_usd=10.0, timeout_seconds=30)
    svc = TranscriptionService(LlmClient(ai=ai), settings)

    result = await svc.transcribe(b"\x00" * 64000, "a.mp3")
    assert result.source == "whisper"
    assert result.raw_text
    assert result.duration_seconds > 0
    assert result.latency_ms >= 0
    assert result.cost_usd >= 0
    assert len(result.speakers) >= 1


@pytest.mark.asyncio
async def test_pre_transcribed_text_parsed_with_speaker_attribution() -> None:
    settings = Settings()
    ai = AIClient(provider="mock", model="m", max_daily_cost_usd=10.0, timeout_seconds=30)
    svc = TranscriptionService(LlmClient(ai=ai), settings)

    parsed = await svc.parse_transcript("John: Hello\nSpeaker 2: Hi")
    assert parsed.raw_text.startswith("John:")
    assert len(parsed.speakers) == 2
    assert parsed.speakers[0].speaker_id in ("John", "john")


@pytest.mark.asyncio
async def test_no_speaker_markers_treated_as_single_speaker() -> None:
    settings = Settings()
    ai = AIClient(provider="mock", model="m", max_daily_cost_usd=10.0, timeout_seconds=30)
    svc = TranscriptionService(LlmClient(ai=ai), settings)

    parsed = await svc.parse_transcript("No markers here just text.")
    assert len(parsed.speakers) == 1
    assert parsed.speakers[0].speaker_id == "Speaker 1"
