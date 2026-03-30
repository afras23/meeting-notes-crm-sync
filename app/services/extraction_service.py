"""
Extraction service.

Transforms meeting transcripts into validated structured meeting data with audit logging.
"""

from __future__ import annotations

# Standard library
import hashlib
import json
import logging
import re
from datetime import UTC, datetime
from uuid import uuid4

# Third party
from pydantic import ValidationError as PydanticValidationError

# Local
from app.core.constants import MAX_INPUT_PREVIEW_CHARS
from app.core.exceptions import ExtractionFailed, ValidationFailed
from app.models.action_item import ActionItem
from app.models.audit import AuditEntry
from app.models.meeting import CRMUpdates, Meeting
from app.repositories.audit_repository import AuditRepository
from app.services.ai.client import AIClient
from app.services.ai.prompts import get_prompt

logger = logging.getLogger(__name__)

_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+all\s+previous\s+instructions", re.IGNORECASE),
    re.compile(r"ignore\s+(all\s+)?(previous|above)\s+(instructions|prompts)", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"```\\s*(system|admin|root)", re.IGNORECASE),
]


def _compute_input_hash(transcript: str) -> str:
    return hashlib.sha256(transcript.encode("utf-8")).hexdigest()


class ExtractionService:
    """Extracts structured meeting data from transcripts."""

    def __init__(self, *, ai_client: AIClient, audit_repository: AuditRepository) -> None:
        self._ai = ai_client
        self._audit = audit_repository

    async def extract_meeting(
        self,
        *,
        transcript: str,
        prompt_name: str = "meeting_extraction_v1",
    ) -> Meeting:
        """
        Extract meeting information from a transcript.

        Args:
            transcript: Transcript text.
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
            return self._meeting_from_parsed(parsed, transcript=cleaned_transcript)

        system_prompt, user_prompt, prompt_version = get_prompt(
            prompt_name, transcript=cleaned_transcript
        )
        ai_call = await self._ai.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            prompt_name=prompt_name,
            prompt_version=prompt_version,
        )

        try:
            parsed_output = json.loads(ai_call.content)
        except json.JSONDecodeError as e:
            raise ExtractionFailed(
                "AI returned invalid JSON",
                context={"preview": ai_call.content[:MAX_INPUT_PREVIEW_CHARS]},
            ) from e

        meeting = self._meeting_from_parsed(parsed_output, transcript=cleaned_transcript)

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

    def _meeting_from_parsed(self, parsed: dict[str, object], *, transcript: str) -> Meeting:
        if not isinstance(parsed, dict):
            raise ExtractionFailed("AI output JSON must be an object.", context={})

        meeting_id = str(uuid4())
        try:
            crm_updates = CRMUpdates.model_validate(parsed.get("crm_updates") or {})
            raw_action_items = parsed.get("action_items") or []
            action_items: list[ActionItem] = []
            if isinstance(raw_action_items, list):
                for raw in raw_action_items:
                    if not isinstance(raw, dict):
                        continue
                    action_items.append(
                        ActionItem(
                            id=str(uuid4()),
                            meeting_id=meeting_id,
                            owner=str(raw.get("owner")) if raw.get("owner") else None,
                            description=str(raw.get("description") or "").strip() or "Follow up",
                            due_at=None,
                            status="open",
                        )
                    )
            raw_participants = parsed.get("participants")
            participants: list[str] = []
            if isinstance(raw_participants, list):
                participants = [str(p) for p in raw_participants]

            confidence_raw = parsed.get("confidence")
            confidence = 0.0
            if isinstance(confidence_raw, int | float):
                confidence = float(confidence_raw)
            elif isinstance(confidence_raw, str):
                confidence = float(confidence_raw) if confidence_raw.strip() else 0.0
            meeting = Meeting(
                id=meeting_id,
                title=str(parsed.get("title") or "Untitled meeting"),
                occurred_at=None,
                transcript=transcript,
                summary=str(parsed.get("summary") or "No summary provided."),
                participants=participants,
                action_items=action_items,
                crm_updates=crm_updates,
                confidence=confidence,
            )
        except (ValueError, PydanticValidationError) as e:
            raise ExtractionFailed(
                "AI output failed validation.",
                context={"validation_error": str(e)[:MAX_INPUT_PREVIEW_CHARS]},
            ) from e

        return meeting
