"""
Unit tests for extraction evaluation metrics and report shape.
"""

# Standard library
from __future__ import annotations

import json
from pathlib import Path

import pytest

# Local
from eval.evaluate import run_evaluation
from eval.metrics import (
    action_item_detection_rate,
    attendee_detection_rate,
)

REQUIRED_REPORT_KEYS = frozenset(
    {
        "timestamp",
        "model",
        "prompt_name",
        "prompt_version",
        "test_cases",
        "overall_extraction_accuracy",
        "attendee_detection_rate",
        "action_item_detection_rate",
        "action_owner_accuracy",
        "deadline_detection_rate",
        "decision_detection_rate",
        "deal_stage_accuracy",
        "sentiment_accuracy",
        "next_steps_recall",
        "crm_mapping_accuracy",
        "crm_diff_detection_accuracy",
        "avg_latency_ms",
        "avg_cost_per_meeting_usd",
        "total_cost_usd",
        "failures",
        "report_path",
    }
)


def test_attendee_detection_rate_calculation() -> None:
    """Expected attendees fully found when names match (case-insensitive)."""

    rate = attendee_detection_rate(
        ["John Smith", "Sarah Chen"],
        ["Sarah Chen", "John Smith"],
    )
    assert rate == 1.0

    partial = attendee_detection_rate(
        ["John Smith", "Sarah Chen"],
        ["John Smith"],
    )
    assert partial == pytest.approx(0.5)


def test_action_item_detection_rate_calculation() -> None:
    """Recall: fraction of expected action descriptions matched."""

    rate = action_item_detection_rate(
        [
            {"description": "Send revised proposal", "owner": "Sarah Chen", "has_deadline": True},
        ],
        ["Send revised proposal by Friday"],
    )
    assert rate == 1.0

    low = action_item_detection_rate(
        [
            {"description": "Send revised proposal", "owner": "Sarah Chen", "has_deadline": True},
            {"description": "Schedule demo", "owner": "Alex", "has_deadline": False},
        ],
        ["Send revised proposal by Friday"],
    )
    assert low == pytest.approx(0.5)


@pytest.mark.asyncio
async def test_evaluation_report_schema_valid(tmp_path: Path) -> None:
    """End-to-end mini eval produces a report with required keys and numeric types."""

    case = {
        "transcript": "Speaker 1: Hello team. Speaker 2: Alice and Bob are here. "
        "Speaker 1: Action: Alice owns the deck. Decision: approve budget. "
        "Stage moves from proposal to negotiation. Positive sentiment. Next: ship deck.",
        "expected_attendees": ["Alice", "Bob"],
        "expected_action_items": [
            {"description": "Own the deck", "owner": "Alice", "has_deadline": False},
        ],
        "expected_decisions": ["Approve budget"],
        "expected_deal_stage_change": {"from": "proposal", "to": "negotiation"},
        "expected_sentiment": "positive",
        "expected_next_steps": ["Ship deck"],
        "category": "sales_call",
        "expected_title": "Mini eval",
        "expected_crm_fields": {"dealname": "Mini eval", "dealstage": "negotiation"},
        "run_crm_eval": True,
    }
    jsonl = tmp_path / "mini.jsonl"
    jsonl.write_text(json.dumps(case) + "\n", encoding="utf-8")
    out_dir = tmp_path / "out"
    report = await run_evaluation(str(jsonl), str(out_dir))

    assert set(report.keys()) >= REQUIRED_REPORT_KEYS
    assert isinstance(report["failures"], list)
    assert report["test_cases"] == 1
    assert Path(report["report_path"]).is_file()
    assert Path(report["report_path"]).read_text(encoding="utf-8").strip().startswith("{")
