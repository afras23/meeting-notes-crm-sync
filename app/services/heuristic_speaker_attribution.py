"""
Heuristic speaker labeling for transcript text (not audio diarisation).

This module splits pre-formatted text into segments using **line-based rules**:
``Name:`` or ``[Label]:`` prefixes. It does **not** perform speaker diarisation
(no voice embeddings, no timestamp alignment from a diarisation backend, no
inference of who spoke from audio). Whisper output is not post-processed with a
diarisation model here; labels come only from explicit markers in the string (or
a single default speaker when none appear).

Limitations:
- One speaker per line group; continuation lines are concatenated into the
  current speaker until the next marker.
- Labels are trusted as written (no identity resolution across meetings).
- Unlabeled lines before the first marker are attributed to ``Speaker 1``.
"""

# Standard library
from __future__ import annotations

import re

# Local
from app.models.transcription import SpeakerSegment

# Line start: optional "[Any label]:" or "Word...:" then remainder of line is speech.
HEURISTIC_SPEAKER_LINE_RE = re.compile(
    r"^\s*(?:\[(?P<bracket>[^\]]+)\]|(?P<label>[A-Za-z][A-Za-z0-9 _.-]{0,40}))\s*:\s*(?P<text>.*)$"
)


def parse_heuristic_speaker_segments(raw_text: str) -> list[SpeakerSegment]:
    """
    Split ``raw_text`` into speaker segments using heuristic line-prefix rules.

    A **marker line** matches ``HEURISTIC_SPEAKER_LINE_RE``: either ``[Label]:``
    text or ``Label:`` text (label starts with a letter). Non-marker lines append
    to the current speaker; if no speaker is active yet, the default label is
    ``Speaker 1``.

    If **no** marker line appears anywhere, the entire non-empty body is a
    single segment labeled ``Speaker 1`` (whitespace-normalised to one line of
    words). Empty or whitespace-only input yields an empty list.

    This is **not** full diarisation: accuracy depends entirely on how the
    transcript was authored or pre-tagged upstream.
    """
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
        m = HEURISTIC_SPEAKER_LINE_RE.match(line)
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
