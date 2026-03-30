"""
CRM service.

Maps extraction output to CRM fields, applies only diffs, and records audit metadata.
"""

# Standard library
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

# Third party
import yaml
from pydantic import ValidationError as PydanticValidationError

# Local
from app.core.exceptions import ValidationFailed
from app.integrations.hubspot_client import HubSpotClientMock
from app.models.crm_mapping import CRMMappingRoot
from app.models.meeting import Meeting

logger = logging.getLogger(__name__)


def _get_by_path(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for segment in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(segment)
    return current


def _diff_properties(
    current: dict[str, Any], desired: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    """Return (changed_properties, skipped_unchanged_keys)."""

    changed: dict[str, Any] = {}
    skipped: list[str] = []
    for key, value in desired.items():
        if value is None:
            skipped.append(key)
            continue
        if current.get(key) != value:
            changed[key] = value
        else:
            skipped.append(key)
    return changed, skipped


class CRMService:
    """Maps structured meeting data into CRM updates with diff detection."""

    def __init__(
        self,
        *,
        crm_client: HubSpotClientMock,
        mapping_path: str = "config/crm_mapping.yaml",
        crm_key: str = "hubspot",
    ) -> None:
        self._crm = crm_client
        self._mapping_path = mapping_path
        self._crm_key = crm_key

    async def apply_updates(self, *, meeting: Meeting, deal_id: str) -> dict[str, Any]:
        """
        Apply CRM updates for a meeting (only changed fields).

        Args:
            meeting: Structured meeting data.
            deal_id: Deal identifier in the target CRM.

        Returns:
            Summary including diff, skipped fields, and optional note id.
        """

        mapping_root = self._load_mapping()
        bundle = mapping_root.crm_mappings.get(self._crm_key)
        if bundle is None:
            raise ValidationFailed(
                "CRM mapping missing for configured CRM key.",
                context={"crm_key": self._crm_key},
            )

        deal_mapping = bundle.entities.get("deal")
        if deal_mapping is None:
            raise ValidationFailed("CRM mapping missing 'deal' entity.", context={})

        meeting_payload = meeting.model_dump(mode="json")
        mapping_payload: dict[str, Any] = {"meeting": meeting_payload, **meeting_payload}

        desired: dict[str, Any] = {}
        for field_name, field_mapping in deal_mapping.fields.items():
            value = _get_by_path(mapping_payload, field_mapping.source)
            if value is not None:
                desired[field_name] = value

        previous = await self._crm.get_deal(deal_id) or {}
        changed, skipped = _diff_properties(previous, desired)

        note_id: str | None = None
        if changed:
            await self._crm.update_deal(deal_id, changed)
            note_body = f"Meeting: {meeting.title}\nSummary: {meeting.extraction.summary[:400]}"
            note_id = await self._crm.add_note(deal_id=deal_id, body=note_body)
            logger.info(
                "Applied CRM deal diff",
                extra={
                    "deal_id": deal_id,
                    "changed_keys": list(changed.keys()),
                    "skipped_keys": skipped,
                },
            )
        else:
            logger.info(
                "No CRM deal fields changed; skipping update",
                extra={"deal_id": deal_id, "skipped_keys": skipped},
            )

        return {
            "entity": "deal",
            "deal_id": deal_id,
            "changed_properties": changed,
            "skipped_unchanged": skipped,
            "previous_snapshot": dict(previous),
            "note_id": note_id,
        }

    def _load_mapping(self) -> CRMMappingRoot:
        mapping_path = Path(self._mapping_path)
        if not mapping_path.exists():
            raise ValidationFailed(
                "CRM mapping file not found.", context={"path": self._mapping_path}
            )

        content = mapping_path.read_text(encoding="utf-8")
        raw = yaml.safe_load(content) or {}
        try:
            return CRMMappingRoot.model_validate(raw)
        except PydanticValidationError as e:
            raise ValidationFailed(
                "CRM mapping file invalid.", context={"errors": e.errors()}
            ) from e
