"""
Evaluation runner.

Runs the extraction pipeline against a JSONL test set and writes a timestamped report.
"""

# Standard library
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

# Local
from app.repositories.audit_repository import AuditRepository
from app.services.ai.client import AIClient
from app.services.extraction_service import ExtractionService


@dataclass(frozen=True)
class EvalCase:
    """Single evaluation case."""

    input_text: str
    expected: dict[str, object]


def _load_cases(path: Path) -> list[EvalCase]:
    cases: list[EvalCase] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        raw = json.loads(line)
        cases.append(
            EvalCase(input_text=str(raw["input"]), expected=dict(raw.get("expected") or {}))
        )
    return cases


def _get_nested(payload: dict[str, object], path: str) -> object | None:
    current: object = payload
    for segment in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(segment)
    return current


async def _run_eval() -> dict[str, object]:
    test_set_path = Path("eval/test_set.jsonl")
    results_dir = Path("eval/results")
    results_dir.mkdir(parents=True, exist_ok=True)

    ai_client = AIClient(
        provider="mock", model="mock-llm", max_daily_cost_usd=100.0, timeout_seconds=30
    )
    service = ExtractionService(ai_client=ai_client, audit_repository=AuditRepository())

    cases = _load_cases(test_set_path)
    checks = ["crm_updates.deal.amount", "crm_updates.deal.stage"]

    total_checks = 0
    correct_checks = 0
    per_check: dict[str, dict[str, int]] = {c: {"correct": 0, "total": 0} for c in checks}

    for case in cases:
        meeting = await service.extract_meeting(
            transcript=case.input_text,
            deal_id=None,
            project_id=None,
        )
        actual = meeting.model_dump(mode="json")
        for check in checks:
            expected_value = _get_nested(case.expected, check)
            if expected_value is None:
                continue
            total_checks += 1
            per_check[check]["total"] += 1
            actual_value = _get_nested(actual, check)
            if actual_value == expected_value:
                correct_checks += 1
                per_check[check]["correct"] += 1

    report = {
        "timestamp": datetime.now(UTC).isoformat(),
        "cases": len(cases),
        "accuracy": round(correct_checks / max(total_checks, 1), 3),
        "per_check_accuracy": {
            k: round(v["correct"] / max(v["total"], 1), 3) for k, v in per_check.items()
        },
        "ai": {
            "provider": "mock",
            "model": "mock-llm",
            "daily_cost_usd": round(ai_client.daily_cost_usd, 6),
            "requests": ai_client.request_count,
        },
    }

    output_path = results_dir / f"eval_{datetime.now(UTC).date().isoformat()}.json"
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return {"report_path": str(output_path), **report}


def main() -> None:
    report = asyncio.run(_run_eval())
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
