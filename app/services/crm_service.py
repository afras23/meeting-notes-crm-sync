"""
CRM service.

Applies mapping configuration to extracted meeting data and updates the CRM via integration clients.
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
from app.models.crm_mapping import CRMMappingConfig
from app.models.meeting import Meeting

logger = logging.getLogger(__name__)


def _get_by_path(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for segment in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(segment)
    return current


class CRMService:
    """Maps structured meeting data into CRM updates and applies them."""

    def __init__(
        self, *, crm_client: HubSpotClientMock, mapping_path: str = "config/crm_mapping.yaml"
    ) -> None:
        self._crm = crm_client
        self._mapping_path = mapping_path

    async def apply_updates(self, *, meeting: Meeting, deal_id: str) -> dict[str, Any]:
        """
        Apply CRM updates for a meeting.

        Args:
            meeting: Structured meeting data.
            deal_id: Deal identifier in the target CRM.

        Returns:
            Summary of applied updates.
        """

        mapping = self._load_mapping()
        meeting_payload = meeting.model_dump(mode="json")
        mapping_payload: dict[str, Any] = {"meeting": meeting_payload, **meeting_payload}

        deal_mapping = mapping.entities.get("deal")
        if deal_mapping is None:
            raise ValidationFailed("CRM mapping missing 'deal' entity.", context={})

        properties: dict[str, Any] = {}
        for field_name, field_mapping in deal_mapping.fields.items():
            value = _get_by_path(mapping_payload, field_mapping.source)
            if value is not None:
                properties[field_name] = value

        await self._crm.update_deal(deal_id, properties)
        logger.info("Applied CRM deal update", extra={"deal_id": deal_id, "properties": properties})

        return {"entity": "deal", "deal_id": deal_id, "properties": properties}

    def _load_mapping(self) -> CRMMappingConfig:
        mapping_path = Path(self._mapping_path)
        if not mapping_path.exists():
            raise ValidationFailed(
                "CRM mapping file not found.", context={"path": self._mapping_path}
            )

        content = mapping_path.read_text(encoding="utf-8")
        raw = yaml.safe_load(content) or {}
        try:
            return CRMMappingConfig.model_validate(raw)
        except PydanticValidationError as e:
            raise ValidationFailed(
                "CRM mapping file invalid.", context={"errors": e.errors()}
            ) from e
