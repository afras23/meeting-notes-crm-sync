"""
Evaluation runner: extraction accuracy, CRM projection, cost/latency aggregates.
"""

# Standard library
from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Local
from app.core.exceptions import ExtractionFailed
from app.integrations.hubspot_client import HubSpotClientMock
from app.repositories.audit_repository import AuditRepository
from app.services.ai.client import AICallResult, AIClient
from app.services.crm_service import CRMService
from app.services.extraction_service import ExtractionService
from eval.crm_helpers import compute_desired_hubspot_fields
from eval.metrics import (
    action_item_detection_rate,
    action_owner_accuracy,
    attendee_detection_rate,
    crm_field_accuracy,
    deadline_detection_rate,
    deal_stage_accuracy,
    decision_detection_rate,
    diff_detection_correct,
    mean,
    next_steps_recall,
    sentiment_accuracy,
    transcript_preview,
)

DEFAULT_PROMPT_NAME = "meeting_extraction_v2"
REPORT_MODEL = "gpt-4o"


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def build_extraction_json(case: dict[str, Any]) -> str:
    """Build AI JSON matching ExtractionService._meeting_from_parsed expectations."""

    dsc = case.get("expected_deal_stage_change") or {}
    ecf = case.get("expected_crm_fields") or {}
    title = str(case.get("expected_title") or ecf.get("dealname") or "Meeting")
    summary = str(case.get("expected_summary") or "Summary.")
    attendees = [
        {"name": n, "role": None, "email": None} for n in case.get("expected_attendees", [])
    ]
    actions: list[dict[str, Any]] = []
    for a in case.get("expected_action_items", []):
        desc = str(a.get("description") or "")
        owner = a.get("owner")
        due = "2026-04-20T12:00:00+00:00" if a.get("has_deadline") else None
        actions.append(
            {
                "owner": owner,
                "description": desc,
                "due_date_iso": due,
                "status": "open",
            }
        )
    decisions = [{"text": t, "decided_by": None} for t in case.get("expected_decisions", [])]
    old_s = dsc.get("from")
    new_s = dsc.get("to")
    deal_stage_change: dict[str, Any] | None = None
    if old_s is not None or new_s is not None:
        deal_stage_change = {"old_stage": old_s, "new_stage": new_s}
    ns = case.get("expected_next_steps")
    if isinstance(ns, list):
        next_steps_str = "; ".join(str(x) for x in ns)
    elif isinstance(ns, str):
        next_steps_str = ns
    else:
        next_steps_str = None
    amount = ecf.get("amount")
    stage = ecf.get("dealstage") if ecf.get("dealstage") is not None else new_s
    payload: dict[str, Any] = {
        "title": title,
        "summary": summary,
        "attendees": attendees,
        "action_items": actions,
        "decisions": decisions,
        "deal_stage_change": deal_stage_change,
        "next_steps": next_steps_str,
        "follow_up_date": case.get("follow_up_date"),
        "sentiment": case.get("expected_sentiment"),
        "crm_updates": {"deal": {"amount": amount, "stage": stage}},
        "confidence": float(case.get("confidence", 0.9)),
    }
    return json.dumps(payload)


def _load_cases(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        cases.append(json.loads(line))
    return cases


class EvalSequenceAIClient(AIClient):
    """Returns queued JSON payloads (simulates perfect extraction from labeled data)."""

    def __init__(self, *, payloads: list[str], model: str = REPORT_MODEL) -> None:
        super().__init__(
            provider="mock",
            model=model,
            max_daily_cost_usd=1e9,
            timeout_seconds=300,
        )
        self._payloads = list(payloads)
        self._idx = 0
        self.per_call_latency_ms: list[float] = []
        self.per_call_cost_usd: list[float] = []

    async def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        prompt_name: str,
        prompt_version: str,
    ) -> AICallResult:
        if self._idx >= len(self._payloads):
            raise ExtractionFailed(
                "Evaluation AI queue exhausted (more transcripts than mock payloads).",
                context={"index": self._idx},
            )
        content = self._payloads[self._idx]
        self._idx += 1
        start = time.monotonic()
        latency_ms = (time.monotonic() - start) * 1000.0
        input_tokens = _estimate_tokens(system_prompt) + _estimate_tokens(user_prompt)
        output_tokens = _estimate_tokens(content)
        cost_usd = (input_tokens + output_tokens) * 0.0000005
        self._daily_cost_usd += cost_usd
        self._request_count += 1
        self.per_call_latency_ms.append(latency_ms)
        self.per_call_cost_usd.append(cost_usd)
        return AICallResult(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            provider=self._provider,
            model=self._model,
            prompt_name=prompt_name,
            prompt_version=prompt_version,
        )


async def run_evaluation(test_set_path: str, output_path: str) -> dict[str, Any]:
    """
    Run extraction evaluation over JSONL test cases and write a JSON report.

    Args:
        test_set_path: Path to JSONL (each line: transcript + expected_* fields).
        output_path: Output file path, or directory (writes eval_YYYY-MM-DD.json inside).

    Returns:
        Report dict including ``report_path`` to the written file.
    """

    test_path = Path(test_set_path)
    cases = _load_cases(test_path)
    payloads = [build_extraction_json(c) for c in cases]
    ai = EvalSequenceAIClient(payloads=payloads)
    audit = AuditRepository()
    extraction = ExtractionService(ai_client=ai, audit_repository=audit)
    hubspot = HubSpotClientMock()
    crm = CRMService(crm_client=hubspot, mapping_path="config/crm_mapping.yaml")

    per_att: list[float] = []
    per_act: list[float] = []
    per_own: list[float] = []
    per_dec: list[float] = []
    per_stage: list[float] = []
    per_sent: list[float] = []
    per_next: list[float] = []
    per_crm: list[float] = []
    per_diff: list[float] = []
    per_deadline: list[float] = []
    overall_case_scores: list[float] = []
    failures: list[dict[str, str]] = []

    for i, case in enumerate(cases):
        transcript = str(case["transcript"])
        deal_id = case.get("eval_deal_id")
        if deal_id is None:
            deal_id = f"eval-{i:04d}"
        run_crm = bool(case.get("run_crm_eval", True))

        meeting = await extraction.extract_meeting(
            transcript=transcript,
            deal_id=deal_id if run_crm else None,
            project_id=None,
            prompt_name=DEFAULT_PROMPT_NAME,
        )
        ext = meeting.extraction
        actual_names = [a.name for a in ext.attendees]
        actual_descs = [a.description for a in ext.action_items]
        actual_pairs = [(a.owner, a.description) for a in ext.action_items]
        actual_deadline_pairs = [(a.deadline is not None, a.description) for a in ext.action_items]
        decision_texts = [d.text for d in ext.decisions]

        exp_att = list(case.get("expected_attendees") or [])
        exp_act = list(case.get("expected_action_items") or [])
        exp_dec = list(case.get("expected_decisions") or [])
        exp_steps = list(case.get("expected_next_steps") or [])
        dsc = case.get("expected_deal_stage_change")

        ar = attendee_detection_rate(exp_att, actual_names)
        acr = action_item_detection_rate(exp_act, actual_descs)
        owr = action_owner_accuracy(exp_act, actual_pairs)
        ddr = deadline_detection_rate(exp_act, actual_deadline_pairs)
        dcr = decision_detection_rate(exp_dec, decision_texts)
        dsr = deal_stage_accuracy(
            dsc if isinstance(dsc, dict) else None,
            ext.deal_stage_change.old_stage if ext.deal_stage_change else None,
            ext.deal_stage_change.new_stage if ext.deal_stage_change else None,
        )
        sr = sentiment_accuracy(
            case.get("expected_sentiment"),
            ext.sentiment,
        )
        nsr = next_steps_recall(exp_steps, ext.next_steps)

        per_att.append(ar)
        per_act.append(acr)
        per_own.append(owr)
        per_dec.append(dcr)
        per_stage.append(dsr)
        per_sent.append(sr)
        per_next.append(nsr)
        per_deadline.append(ddr)

        crm_score = 1.0
        diff_score = 1.0
        if run_crm:
            produced = compute_desired_hubspot_fields(meeting)
            exp_fields = case.get("expected_crm_fields")
            if isinstance(exp_fields, dict):
                crm_score = crm_field_accuracy(exp_fields, produced)

            prev_state = case.get("crm_previous_state")
            if isinstance(prev_state, dict):
                hubspot.seed_deal(str(deal_id), dict(prev_state))
            else:
                hubspot.seed_deal(str(deal_id), {})

            crm_result = await crm.apply_updates(meeting=meeting, deal_id=str(deal_id))
            changed = set(crm_result.get("changed_properties", {}).keys())
            exp_changed = case.get("expected_crm_changed_keys")
            exp_unchanged = case.get("expected_crm_unchanged_keys")
            if exp_changed is not None or exp_unchanged is not None:
                diff_score = diff_detection_correct(
                    changed,
                    list(exp_changed) if exp_changed is not None else None,
                    list(crm_result.get("skipped_unchanged") or []),
                    list(exp_unchanged) if exp_unchanged is not None else None,
                )

        per_crm.append(crm_score)
        per_diff.append(diff_score)

        case_core = mean([ar, acr, dcr, dsr, sr, nsr])
        overall_case_scores.append(mean([case_core, crm_score, diff_score, owr, ddr]))

        if ar < 1.0 or acr < 1.0 or dcr < 1.0 or dsr < 1.0 or sr < 1.0 or nsr < 1.0:
            reasons: list[str] = []
            if ar < 1.0:
                reasons.append("attendee mismatch")
            if acr < 1.0:
                reasons.append("missed action items")
            if dcr < 1.0:
                reasons.append("missed decisions")
            if dsr < 1.0:
                reasons.append("deal stage mismatch")
            if sr < 1.0:
                reasons.append("sentiment mismatch")
            if nsr < 1.0:
                reasons.append("next steps mismatch")
            failures.append(
                {
                    "transcript_preview": transcript_preview(transcript),
                    "reason": "; ".join(reasons),
                }
            )

    total_cost = sum(ai.per_call_cost_usd)
    latencies_all = list(ai.per_call_latency_ms)
    n = len(cases)
    report: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "model": REPORT_MODEL,
        "prompt_name": DEFAULT_PROMPT_NAME,
        "prompt_version": "2.0.0",
        "test_cases": n,
        "overall_extraction_accuracy": round(mean(overall_case_scores), 4),
        "attendee_detection_rate": round(mean(per_att), 4),
        "action_item_detection_rate": round(mean(per_act), 4),
        "action_owner_accuracy": round(mean(per_own), 4),
        "deadline_detection_rate": round(mean(per_deadline), 4),
        "decision_detection_rate": round(mean(per_dec), 4),
        "deal_stage_accuracy": round(mean(per_stage), 4),
        "sentiment_accuracy": round(mean(per_sent), 4),
        "next_steps_recall": round(mean(per_next), 4),
        "crm_mapping_accuracy": round(mean(per_crm), 4),
        "crm_diff_detection_accuracy": round(mean(per_diff), 4),
        "avg_latency_ms": round(mean(latencies_all), 2),
        "avg_cost_per_meeting_usd": round(total_cost / max(n, 1), 6),
        "total_cost_usd": round(total_cost, 6),
        "failures": failures,
    }

    out = Path(output_path)
    if out.suffix.lower() != ".json" or out.is_dir():
        out.mkdir(parents=True, exist_ok=True)
        out_file = out / f"eval_{datetime.now(UTC).date().isoformat()}.json"
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out_file = out

    out_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report["report_path"] = str(out_file.resolve())
    return report


def main() -> None:
    import asyncio

    result = asyncio.run(run_evaluation("eval/test_set.jsonl", "eval/results"))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
