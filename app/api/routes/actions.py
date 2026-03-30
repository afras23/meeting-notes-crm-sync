"""
Action items endpoints.

Provides access to extracted action items.
"""

# Standard library
from __future__ import annotations

# Third party
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

# Local
from app.api.schemas.actions import ActionListResponse, ActionResponse, ActionUpdateRequest
from app.api.schemas.envelope import ResponseMetadata, SuccessEnvelope
from app.api.schemas.pagination import PageInfo, PaginatedResponse
from app.core.exceptions import NotFound
from app.core.logging import correlation_id_ctx
from app.dependencies import get_action_repo, get_audit_repository, get_db_session
from app.models.audit import AuditEntry
from app.repositories.action_item_repository import ActionItemRepository
from app.repositories.audit_repository import AuditRepository

router = APIRouter()


@router.get("/actions", response_model=SuccessEnvelope[ActionListResponse])
async def list_actions(
    session: AsyncSession = Depends(get_db_session),
    action_repo: ActionItemRepository = Depends(get_action_repo),
    page: int = Query(default=1, ge=1, description="Page number."),
    page_size: int = Query(default=20, ge=1, le=200, description="Items per page."),
    owner: str | None = Query(default=None, description="Filter by owner."),
    status: str | None = Query(default=None, description="Filter by status."),
    meeting_id: str | None = Query(default=None, description="Filter by meeting id."),
    overdue: bool | None = Query(default=None, description="Filter to overdue actions when true."),
) -> SuccessEnvelope[ActionListResponse]:
    correlation_id = correlation_id_ctx.get() or ""
    actions = await action_repo.list(
        session,
        page=page,
        page_size=page_size,
        owner=owner,
        status=status,
        meeting_id=meeting_id,
        overdue=overdue,
    )
    data = ActionListResponse(
        actions=PaginatedResponse(items=actions, page_info=PageInfo(page=page, page_size=page_size))
    )
    return SuccessEnvelope(data=data, metadata=ResponseMetadata(correlation_id=correlation_id))


@router.patch("/actions/{action_id}", response_model=SuccessEnvelope[ActionResponse])
async def update_action_status(
    action_id: str,
    request: ActionUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    action_repo: ActionItemRepository = Depends(get_action_repo),
    audit_repo: AuditRepository = Depends(get_audit_repository),
) -> SuccessEnvelope[ActionResponse]:
    correlation_id = correlation_id_ctx.get() or ""
    updated = await action_repo.update_status(session, action_id, status=request.status)
    if updated is None:
        raise NotFound("Action item not found.", context={"action_id": action_id})

    # Log to audit trail (in-memory).
    from datetime import UTC, datetime
    from uuid import uuid4

    await audit_repo.upsert(
        AuditEntry(
            id=str(uuid4()),
            created_at=datetime.now(UTC),
            input_hash=f"action:{action_id}",
            input_preview="",
            prompt_name="action_status_change",
            prompt_version="1.0.0",
            model="internal",
            provider="internal",
            latency_ms=0.0,
            input_tokens=0,
            output_tokens=0,
            cost_usd=0.0,
            raw_ai_output="",
            parsed_output={"action_id": action_id, "status": request.status},
            confidence=1.0,
        )
    )

    await session.commit()
    return SuccessEnvelope(
        data=ActionResponse(action=updated),
        metadata=ResponseMetadata(correlation_id=correlation_id),
    )
