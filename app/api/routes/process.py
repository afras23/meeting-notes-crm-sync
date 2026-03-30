"""
Processing endpoint.

Accepts meeting transcripts, runs extraction, applies CRM updates, and triggers notifications.
"""

# Standard library
from __future__ import annotations

import logging
from typing import Literal

# Third party
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

# Local
from app.api.schemas.envelope import ResponseMetadata, SuccessEnvelope
from app.api.schemas.process import ProcessRequest, ProcessResponse
from app.core.logging import correlation_id_ctx
from app.dependencies import get_db_session, get_process_service
from app.services.process_service import DuplicateMeeting, MeetingProcessService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/process", status_code=202, response_model=SuccessEnvelope[ProcessResponse])
async def process_meeting(
    http_request: Request,
    session: AsyncSession = Depends(get_db_session),
    process_service: MeetingProcessService = Depends(get_process_service),
) -> SuccessEnvelope[ProcessResponse]:
    """Accept audio upload or pre-transcribed text and start processing."""

    correlation_id = correlation_id_ctx.get() or ""

    input_type: Literal["audio", "text"]
    content: bytes | str
    filename: str | None = None
    deal_id: str | None = None
    project_id: str | None = None

    content_type = (http_request.headers.get("content-type") or "").lower()

    if "multipart/form-data" in content_type:
        form = await http_request.form()
        audio = form.get("audio")
        if audio is not None and hasattr(audio, "read"):
            input_type = "audio"
            filename = getattr(audio, "filename", None) or "audio"
            raw = await audio.read()
            if not isinstance(raw, bytes | bytearray):
                from app.core.exceptions import ValidationFailed

                raise ValidationFailed("Audio part must be bytes.", context={})
            content = bytes(raw)
        else:
            from app.core.exceptions import ValidationFailed

            raise ValidationFailed("Multipart request must include an audio file part.", context={})
    elif "application/json" in content_type:
        body = await http_request.json()
        parsed = ProcessRequest.model_validate(body)
        if parsed.text is None or not parsed.text.strip():
            from app.core.exceptions import ValidationFailed

            raise ValidationFailed("JSON body must include non-empty text.", context={})
        input_type = "text"
        content = parsed.text.strip()
        deal_id = parsed.deal_id
        project_id = parsed.project_id
    else:
        from app.core.exceptions import ValidationFailed

        raise ValidationFailed(
            "Use multipart/form-data with audio file or application/json with text.",
            context={"content_type": content_type},
        )

    try:
        result = await process_service.process_meeting(
            session,
            content=content,
            filename=filename,
            input_type=input_type,
            deal_id=deal_id,
            project_id=project_id,
        )
        await session.commit()
    except DuplicateMeeting as e:
        # Surface as 409 via global handler.
        raise e

    logger.info(
        "Accepted meeting processing",
        extra={"meeting_id": result.meeting.id, "input_type": input_type, "deal_id": deal_id},
    )
    return SuccessEnvelope(
        data=ProcessResponse(meeting_id=result.meeting.id, status="accepted"),
        metadata=ResponseMetadata(correlation_id=correlation_id),
    )
