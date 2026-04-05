"""
Unit tests for line-based heuristic speaker labeling (not audio diarisation).
"""

# Standard library
from __future__ import annotations

# Local
from app.services.heuristic_speaker_attribution import parse_heuristic_speaker_segments


def test_parse_heuristic_speaker_segments_plain_name_colon_splits_speakers() -> None:
    segs = parse_heuristic_speaker_segments("Alice: Hello\nBob: Hi there")
    assert [s.speaker_id for s in segs] == ["Alice", "Bob"]
    assert segs[0].text == "Hello"
    assert segs[1].text == "Hi there"


def test_parse_heuristic_speaker_segments_bracket_label() -> None:
    segs = parse_heuristic_speaker_segments("[Host]: Welcome\n[Guest]: Thanks")
    assert [s.speaker_id for s in segs] == ["Host", "Guest"]


def test_parse_heuristic_speaker_segments_continuation_lines_merge() -> None:
    segs = parse_heuristic_speaker_segments("A: Line one\nstill A\nB: B only")
    assert len(segs) == 2
    assert segs[0].speaker_id == "A"
    assert segs[0].text == "Line one still A"
    assert segs[1].text == "B only"


def test_parse_heuristic_speaker_segments_unlabeled_prefix_goes_to_speaker_one() -> None:
    segs = parse_heuristic_speaker_segments("Opening without marker\nCarol: Tagged")
    assert segs[0].speaker_id == "Speaker 1"
    assert segs[0].text == "Opening without marker"
    assert segs[1].speaker_id == "Carol"


def test_parse_heuristic_speaker_segments_no_markers_single_speaker_one() -> None:
    segs = parse_heuristic_speaker_segments("Just prose\nsecond line")
    assert len(segs) == 1
    assert segs[0].speaker_id == "Speaker 1"
    assert segs[0].text == "Just prose second line"


def test_parse_heuristic_speaker_segments_whitespace_only_yields_empty() -> None:
    assert parse_heuristic_speaker_segments("") == []
    assert parse_heuristic_speaker_segments("  \n\t  \n") == []
