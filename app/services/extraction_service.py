"""
Extraction service.

Transforms meeting transcripts into validated structured meeting data with audit logging.
"""

# Standard library
from __future__ import annotations

import asyncio
import hashlib
import html
import json
import logging
import random
import re
from datetime import UTC, date, datetime
from uuid import uuid4

# Third party
from pydantic import ValidationError as PydanticValidationError

# Local
from app.core.constants import MAX_INPUT_PREVIEW_CHARS, MAX_TRANSCRIPT_CHARS_FOR_LLM
from app.core.exceptions import ExtractionFailed, ValidationFailed
from app.models.action_item import ActionItem
from app.models.audit import AuditEntry
from app.models.extraction import Attendee, DealStageChange, Decision, MeetingExtraction
from app.models.meeting import CRMUpdates, Meeting
from app.repositories.audit_repository import AuditRepository
from app.services.ai.client import AIClient
from app.services.ai.prompts import get_prompt
from app.services.meeting_series_service import compute_meeting_series_id

logger = logging.getLogger(__name__)

_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+all\s+previous\s+instructions", re.IGNORECASE),
    re.compile(r"ignore\s+(all\s+)?(previous|above)\s+(instructions|prompts)", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"```\\s*(system|admin|root)", re.IGNORECASE),
]


def _compute_input_hash(transcript: str) -> str:
    return hashlib.sha256(transcript.encode("utf-8")).hexdigest()


def _parse_iso_datetime(value: object | None) -> datetime | None:
    if value is None or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_iso_date(value: object | None) -> date | None:
    if value is None or not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _parse_float(value: object | None) -> float:
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str) and value.strip():
        return float(value)
    return 0.0


class ExtractionService:
    """Extracts structured meeting data from transcripts."""

    def __init__(self, *, ai_client: AIClient, audit_repository: AuditRepository) -> None:
        self._ai = ai_client
        self._audit = audit_repository

    async def extract_meeting(
        self,
        *,
        transcript: str,
        deal_id: str | None,
        project_id: str | None,
        occurred_at: datetime | None = None,
        prompt_name: str = "meeting_extraction_v2",
    ) -> Meeting:
        """
        Extract meeting information from a transcript.

        Args:
            transcript: Transcript text.
            deal_id: CRM deal id for series linking.
            project_id: Project id for series linking.
            occurred_at: Meeting time if known.
            prompt_name: Prompt template name.

        Returns:
            Meeting instance containing structured fields.

        Raises:
            ValidationFailed: If transcript is invalid or contains injection patterns.
            ExtractionFailed: If AI output cannot be parsed or validated.
        """

        cleaned_transcript = self._validate_and_clean_transcript(transcript)
        input_hash = _compute_input_hash(cleaned_transcript)
        existing = await self._audit.find_by_input_hash(input_hash)
        if existing is not None:
            logger.info(
                "Duplicate transcript detected; returning cached meeting",
                extra={"input_hash": input_hash},
            )
            parsed = existing.parsed_output
            return self._meeting_from_parsed(
                parsed,
                transcript=cleaned_transcript,
                deal_id=deal_id,
                project_id=project_id,
                occurred_at=occurred_at,
            )

        transcript_for_llm = cleaned_transcript[:MAX_TRANSCRIPT_CHARS_FOR_LLM]
        system_prompt, user_prompt, prompt_version = get_prompt(
            prompt_name, transcript=transcript_for_llm
        )

        last_timeout: TimeoutError | None = None
        ai_call = None
        for attempt in range(3):
            try:
                ai_call = await self._ai.generate_json(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    prompt_name=prompt_name,
                    prompt_version=prompt_version,
                )
                break
            except TimeoutError as e:
                last_timeout = e
                if attempt < 2:
                    await asyncio.sleep(random.uniform(0.05, 0.25))
        if ai_call is None:
            raise ExtractionFailed(
                "AI request timed out after retries.",
                context={"attempts": 3},
            ) from last_timeout

        try:
            parsed_output = json.loads(ai_call.content)
        except json.JSONDecodeError as e:
            raise ExtractionFailed(
                "AI returned invalid JSON",
                context={"preview": ai_call.content[:MAX_INPUT_PREVIEW_CHARS]},
            ) from e

        meeting = self._meeting_from_parsed(
            parsed_output,
            transcript=cleaned_transcript,
            deal_id=deal_id,
            project_id=project_id,
            occurred_at=occurred_at,
        )

        audit_entry = AuditEntry(
            id=str(uuid4()),
            created_at=datetime.now(UTC),
            input_hash=input_hash,
            input_preview=cleaned_transcript[:MAX_INPUT_PREVIEW_CHARS],
            prompt_name=ai_call.prompt_name,
            prompt_version=ai_call.prompt_version,
            model=ai_call.model,
            provider=ai_call.provider,
            latency_ms=ai_call.latency_ms,
            input_tokens=ai_call.input_tokens,
            output_tokens=ai_call.output_tokens,
            cost_usd=ai_call.cost_usd,
            raw_ai_output=ai_call.content,
            parsed_output=parsed_output if isinstance(parsed_output, dict) else {},
            confidence=meeting.confidence,
        )
        await self._audit.upsert(audit_entry)

        logger.info(
            "Meeting extraction completed",
            extra={
                "input_hash": input_hash,
                "confidence": meeting.confidence,
                "prompt_version": ai_call.prompt_version,
                "cost_usd": round(ai_call.cost_usd, 8),
            },
        )

        return meeting

    def _validate_and_clean_transcript(self, transcript: str) -> str:
        transcript = transcript.strip()
        if not transcript:
            raise ValidationFailed("Transcript must be non-empty.", context={})

        for pattern in _INJECTION_PATTERNS:
            if pattern.search(transcript):
                raise ValidationFailed(
                    "Transcript contains a prohibited prompt-injection pattern.",
                    context={"pattern": pattern.pattern},
                )
        return transcript

    def _meeting_from_parsed(
        self,
        parsed: dict[str, object],
        *,
        transcript: str,
        deal_id: str | None,
        project_id: str | None,
        occurred_at: datetime | None,
    ) -> Meeting:
        if not isinstance(parsed, dict):
            raise ExtractionFailed("AI output JSON must be an object.", context={})

        meeting_id = str(uuid4())
        series_id = compute_meeting_series_id(deal_id=deal_id, project_id=project_id)

        try:
            extraction = self._build_meeting_extraction(parsed, meeting_id=meeting_id)
            crm_updates = self._build_crm_updates(parsed, extraction=extraction)

            meeting = Meeting(
                id=meeting_id,
                meeting_series_id=series_id,
                deal_id=deal_id,
                project_id=project_id,
                title=extraction.title,
                occurred_at=occurred_at,
                transcript=transcript,
                extraction=extraction,
                crm_updates=crm_updates,
                confidence=extraction.confidence,
            )
        except (ValueError, PydanticValidationError) as e:
            raise ExtractionFailed(
                "AI output failed validation.",
                context={"validation_error": str(e)[:MAX_INPUT_PREVIEW_CHARS]},
            ) from e

        return meeting

    def _build_meeting_extraction(
        self, parsed: dict[str, object], *, meeting_id: str
    ) -> MeetingExtraction:
        attendees_raw = parsed.get("attendees")
        attendees: list[Attendee] = []
        if isinstance(attendees_raw, list):
            for raw in attendees_raw:
                if not isinstance(raw, dict):
                    continue
                attendees.append(
                    Attendee(
                        name=str(raw.get("name") or "Unknown"),
                        role=str(raw["role"]) if raw.get("role") else None,
                        email=str(raw["email"]) if raw.get("email") else None,
                    )
                )

        raw_actions = parsed.get("action_items") or []
        action_items: list[ActionItem] = []
        if isinstance(raw_actions, list):
            for raw in raw_actions:
                if not isinstance(raw, dict):
                    continue
                desc_raw = str(raw.get("description") or "").strip() or "Follow up"
                action_items.append(
                    ActionItem(
                        id=str(uuid4()),
                        meeting_id=meeting_id,
                        owner=str(raw["owner"]) if raw.get("owner") else None,
                        description=html.escape(desc_raw),
                        deadline=_parse_iso_datetime(raw.get("due_date_iso")),
                        status=str(raw.get("status") or "open"),
                    )
                )

        decisions_raw = parsed.get("decisions") or []
        decisions: list[Decision] = []
        if isinstance(decisions_raw, list):
            for raw in decisions_raw:
                if not isinstance(raw, dict):
                    continue
                decisions.append(
                    Decision(
                        text=str(raw.get("text") or "").strip() or "Decision",
                        decided_by=str(raw["decided_by"]) if raw.get("decided_by") else None,
                    )
                )

        dsc_raw = parsed.get("deal_stage_change")
        deal_stage_change: DealStageChange | None = None
        if isinstance(dsc_raw, dict):
            deal_stage_change = DealStageChange(
                old_stage=str(dsc_raw["old_stage"]) if dsc_raw.get("old_stage") else None,
                new_stage=str(dsc_raw["new_stage"]) if dsc_raw.get("new_stage") else None,
            )

        follow_up_date = _parse_iso_date(parsed.get("follow_up_date"))
        next_steps = str(parsed["next_steps"]) if parsed.get("next_steps") else None
        sentiment = str(parsed["sentiment"]) if parsed.get("sentiment") else None

        confidence = _parse_float(parsed.get("confidence"))

        return MeetingExtraction(
            title=str(parsed.get("title") or "Untitled meeting"),
            summary=str(parsed.get("summary") or "No summary provided."),
            attendees=attendees,
            action_items=action_items,
            decisions=decisions,
            deal_stage_change=deal_stage_change,
            next_steps=next_steps,
            follow_up_date=follow_up_date,
            sentiment=sentiment,
            confidence=confidence,
        )

    def _build_crm_updates(
        self, parsed: dict[str, object], *, extraction: MeetingExtraction
    ) -> CRMUpdates:
        raw_crm = parsed.get("crm_updates") or {}
        crm_updates = CRMUpdates.model_validate(raw_crm if isinstance(raw_crm, dict) else {})
        if extraction.deal_stage_change and extraction.deal_stage_change.new_stage:
            crm_updates.deal.stage = extraction.deal_stage_change.new_stage
        return crm_updates
