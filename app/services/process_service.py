"""
Process orchestration service.

Runs the full pipeline: transcribe/parse -> extract -> CRM sync -> notify -> persist -> audit.
"""

# Standard library
from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

# Third party
from sqlalchemy.ext.asyncio import AsyncSession

# Local
from app.core.exceptions import AppError, ValidationFailed
from app.models.audit import AuditEntry
from app.models.meeting import Meeting
from app.models.transcription import ParsedTranscript, TranscriptResult
from app.repositories.audit_repository import AuditRepository
from app.repositories.crm_sync_repository import CrmSyncRepository
from app.repositories.meeting_repository import MeetingRepository
from app.services.crm_service import CRMService
from app.services.extraction_service import ExtractionService
from app.services.notification_service import NotificationService
from app.services.transcription_service import TranscriptionService

logger = logging.getLogger(__name__)


def _hash_transcript(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class MeetingProcessResult:
    meeting: Meeting
    transcript: TranscriptResult
    parsed_transcript: ParsedTranscript
    crm_result: dict[str, Any]
    processing_ms: float


class DuplicateMeeting(AppError):
    def __init__(self, *, transcript_hash: str, meeting_id: str) -> None:
        super().__init__(
            "Transcript already processed.",
            error_code="DUPLICATE",
            context={"transcript_hash": transcript_hash, "meeting_id": meeting_id},
        )


class MeetingProcessService:
    def __init__(
        self,
        transcription_service: TranscriptionService,
        extraction_service: ExtractionService,
        crm_service: CRMService,
        notification_service: NotificationService,
        meeting_repo: MeetingRepository,
        crm_sync_repo: CrmSyncRepository,
        audit_repo: AuditRepository,
    ) -> None:
        self._transcription = transcription_service
        self._extraction = extraction_service
        self._crm = crm_service
        self._notifications = notification_service
        self._meetings = meeting_repo
        self._crm_sync = crm_sync_repo
        self._audit = audit_repo

    async def process_meeting(
        self,
        session: AsyncSession,
        *,
        content: bytes | str,
        filename: str | None,
        input_type: Literal["audio", "text"],
        deal_id: str | None,
        project_id: str | None = None,
        occurred_at: datetime | None = None,
    ) -> MeetingProcessResult:
        """Full pipeline: transcribe → extract → CRM sync → notify → persist → audit."""

        start = time.monotonic()

        if input_type == "audio":
            if not isinstance(content, bytes | bytearray):
                raise ValidationFailed("Audio input must be bytes.", context={})
            if not filename:
                raise ValidationFailed("filename is required for audio input.", context={})
            transcript = await self._transcription.transcribe(bytes(content), filename)
            parsed = await self._transcription.parse_transcript(transcript.raw_text)
        elif input_type == "text":
            if not isinstance(content, str):
                raise ValidationFailed("Text input must be a string.", context={})
            parsed = await self._transcription.parse_transcript(content)
            transcript = TranscriptResult(
                raw_text=parsed.raw_text,
                speakers=parsed.speakers,
                duration_seconds=0.0,
                source="pre_transcribed",
                cost_usd=0.0,
                latency_ms=0.0,
            )
        else:
            raise ValidationFailed("Invalid input_type.", context={"input_type": input_type})

        transcript_hash = _hash_transcript(parsed.raw_text)
        existing = await self._meetings.find_by_transcript_hash(session, transcript_hash)
        if existing is not None:
            raise DuplicateMeeting(transcript_hash=transcript_hash, meeting_id=existing.id)

        meeting = await self._extraction.extract_meeting(
            transcript=parsed.raw_text,
            deal_id=deal_id,
            project_id=project_id,
            occurred_at=occurred_at,
        )

        crm_result: dict[str, Any] = {}
        if deal_id:
            try:
                crm_result = await self._crm.apply_updates(meeting=meeting, deal_id=deal_id)
            except Exception as e:
                logger.exception("CRM apply_updates failed; continuing with meeting persist")
                crm_result = {
                    "error": str(e),
                    "changed_properties": {},
                    "previous_snapshot": {},
                }

        await self._meetings.upsert(
            session,
            meeting,
            transcript_hash=transcript_hash,
            processing_ms=(time.monotonic() - start) * 1000.0,
            cost_usd=float(transcript.cost_usd) + float(crm_result.get("cost_usd") or 0.0),
            status="processed",
        )

        changed = crm_result.get("changed_properties") or {}
        if deal_id and isinstance(changed, dict) and changed:
            await self._crm_sync.create(
                session,
                meeting_id=meeting.id,
                deal_id=deal_id,
                changed_properties=dict(changed),
                previous_snapshot=dict(crm_result.get("previous_snapshot") or {}),
            )

        await self._notifications.notify_meeting_events(
            session, meeting=meeting, crm_result=crm_result
        )

        audit_entry = AuditEntry(
            id=str(uuid4()),
            created_at=datetime.now(UTC),
            input_hash=transcript_hash,
            input_preview=parsed.raw_text[:200],
            prompt_name="meeting_process_v1",
            prompt_version="1.0.0",
            model="internal",
            provider="internal",
            latency_ms=(time.monotonic() - start) * 1000.0,
            input_tokens=0,
            output_tokens=0,
            cost_usd=float(transcript.cost_usd),
            raw_ai_output="",
            parsed_output={"meeting_id": meeting.id, "deal_id": deal_id},
            confidence=meeting.confidence,
        )
        await self._audit.upsert(audit_entry)

        processing_ms = (time.monotonic() - start) * 1000.0
        return MeetingProcessResult(
            meeting=meeting,
            transcript=transcript,
            parsed_transcript=parsed,
            crm_result=crm_result,
            processing_ms=processing_ms,
        )
