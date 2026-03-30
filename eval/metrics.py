"""
Pure metric helpers for extraction evaluation (unit-tested, no I/O).
"""

# Standard library
from __future__ import annotations

import re
from typing import Any


def _norm(text: str) -> str:
    return " ".join(text.lower().split())


def attendee_detection_rate(expected_names: list[str], actual_names: list[str]) -> float:
    """Fraction of expected attendees found in actual (fuzzy name match)."""

    if not expected_names:
        return 1.0
    hits = 0
    for exp in expected_names:
        if _attendee_found(exp, actual_names):
            hits += 1
    return hits / len(expected_names)


def _attendee_found(expected: str, actuals: list[str]) -> bool:
    ne = _norm(expected)
    for a in actuals:
        na = _norm(a)
        if ne == na or ne in na or na in ne:
            return True
    return False


def action_item_detection_rate(
    expected: list[dict[str, Any]],
    actual_descriptions: list[str],
) -> float:
    """Recall: fraction of expected action descriptions matched to an actual item."""

    if not expected:
        return 1.0
    hits = 0
    for item in expected:
        desc = str(item.get("description") or "")
        if _match_action_description(desc, actual_descriptions):
            hits += 1
    return hits / len(expected)


def _match_action_description(expected_desc: str, actuals: list[str]) -> bool:
    key = _norm(expected_desc)
    if not key:
        return False
    for a in actuals:
        na = _norm(a)
        if key in na or na in key:
            return True
    return False


def action_owner_accuracy(
    expected: list[dict[str, Any]],
    actual_pairs: list[tuple[str | None, str]],
) -> float:
    """
    Owner accuracy over expected items that specify an owner.

    actual_pairs: (owner, description) per extracted action.
    """

    scored = 0
    total = 0
    for item in expected:
        owner = item.get("owner")
        if owner is None or str(owner).strip() == "":
            continue
        desc = str(item.get("description") or "")
        total += 1
        match = _find_action_pair(desc, actual_pairs)
        if match is None:
            continue
        ao, _ = match
        if ao is not None and _norm(str(owner)) == _norm(str(ao)):
            scored += 1
    if total == 0:
        return 1.0
    return scored / total


def _find_action_pair(
    description: str, actual_pairs: list[tuple[str | None, str]]
) -> tuple[str | None, str] | None:
    key = _norm(description)
    for owner, desc in actual_pairs:
        if key in _norm(desc) or _norm(desc) in key:
            return (owner, desc)
    return None


def deadline_detection_rate(
    expected: list[dict[str, Any]],
    actual_pairs: list[tuple[bool, str]],
) -> float:
    """
    For items with has_deadline true, fraction where a deadline was detected.

    actual_pairs: (has_deadline_bool, description) per extracted action.
    """

    need = 0
    ok = 0
    for item in expected:
        if not item.get("has_deadline"):
            continue
        desc = str(item.get("description") or "")
        need += 1
        match = _find_deadline_pair(desc, actual_pairs)
        if match is not None and match[0]:
            ok += 1
    if need == 0:
        return 1.0
    return ok / need


def _find_deadline_pair(
    description: str, actual_pairs: list[tuple[bool, str]]
) -> tuple[bool, str] | None:
    key = _norm(description)
    for has_dl, desc in actual_pairs:
        if key in _norm(desc) or _norm(desc) in key:
            return (has_dl, desc)
    return None


def decision_detection_rate(expected_texts: list[str], actual_texts: list[str]) -> float:
    """Recall for decision strings."""

    if not expected_texts:
        return 1.0
    hits = 0
    for exp in expected_texts:
        if _match_decision(exp, actual_texts):
            hits += 1
    return hits / len(expected_texts)


def _match_decision(expected: str, actuals: list[str]) -> bool:
    key = _norm(expected)
    return any(key in _norm(a) or _norm(a) in key for a in actuals)


def deal_stage_accuracy(
    expected: dict[str, Any] | None,
    old_stage: str | None,
    new_stage: str | None,
) -> float:
    """1.0 if expected from/to match actual old/new; 1.0 if both expected absent."""

    if not expected:
        return 1.0
    ef = expected.get("from")
    et = expected.get("to")
    if ef is None and et is None:
        return 1.0
    ok_from = ef is None or _norm(str(ef)) == _norm(str(old_stage or ""))
    ok_to = et is None or _norm(str(et)) == _norm(str(new_stage or ""))
    return 1.0 if ok_from and ok_to else 0.0


def sentiment_accuracy(expected: str | None, actual: str | None) -> float:
    """1.0 if both None or normalized strings equal."""

    if expected is None:
        return 1.0
    if actual is None:
        return 0.0
    return 1.0 if _norm(str(expected)) == _norm(str(actual)) else 0.0


def next_steps_recall(expected_steps: list[str], next_steps: str | None) -> float:
    """Fraction of expected step phrases found in the next_steps string."""

    if not expected_steps:
        return 1.0
    blob = _norm(next_steps or "")
    hits = 0
    for step in expected_steps:
        if _norm(step) in blob:
            hits += 1
    return hits / len(expected_steps)


def crm_field_accuracy(
    expected: dict[str, Any] | None,
    produced: dict[str, Any],
) -> float:
    """
    Fraction of non-null expected keys whose values match produced HubSpot fields.

    Only keys present in `expected` are scored.
    """

    if not expected:
        return 1.0
    checks = 0
    ok = 0
    for key, ev in expected.items():
        if ev is None:
            continue
        checks += 1
        pv = produced.get(key)
        if isinstance(ev, int | float) and isinstance(pv, int | float):
            if float(ev) == float(pv):
                ok += 1
        elif _norm(str(ev)) == _norm(str(pv or "")):
            ok += 1
    if checks == 0:
        return 1.0
    return ok / checks


def diff_detection_correct(
    changed_keys: set[str],
    expected_changed: list[str] | None,
    skipped_unchanged: list[str],
    expected_unchanged: list[str] | None,
) -> float:
    """
    1.0 if changed keys match expected and all expected_unchanged keys were skipped.

    If expected lists are None, returns 1.0 (not evaluated).
    """

    score = 1.0
    if expected_changed is not None:
        score *= 1.0 if set(expected_changed) == changed_keys else 0.0
    if expected_unchanged is not None:
        skipped = set(skipped_unchanged)
        for k in expected_unchanged:
            if k not in skipped:
                score = 0.0
                break
    return score


def mean(values: list[float]) -> float:
    return sum(values) / max(len(values), 1)


def transcript_preview(transcript: str, max_len: int = 120) -> str:
    t = re.sub(r"\s+", " ", transcript.strip())
    return t if len(t) <= max_len else t[: max_len - 3] + "..."
