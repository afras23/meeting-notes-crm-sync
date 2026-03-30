"""
CRM field projection for evaluation (mirrors CRMService mapping without persisting).
"""

# Standard library
from __future__ import annotations

from pathlib import Path
from typing import Any

# Third party
import yaml
from pydantic import ValidationError as PydanticValidationError

# Local
from app.core.exceptions import ValidationFailed
from app.models.crm_mapping import CRMMappingRoot
from app.models.meeting import Meeting


def _get_by_path(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for segment in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(segment)
    return current


def compute_desired_hubspot_fields(
    meeting: Meeting,
    *,
    mapping_path: str = "config/crm_mapping.yaml",
    crm_key: str = "hubspot",
) -> dict[str, Any]:
    """Return HubSpot deal fields the mapping would send (before diff with CRM)."""

    mapping_path_p = Path(mapping_path)
    if not mapping_path_p.exists():
        raise ValidationFailed("CRM mapping file not found.", context={"path": mapping_path})

    raw = yaml.safe_load(mapping_path_p.read_text(encoding="utf-8")) or {}
    try:
        mapping_root = CRMMappingRoot.model_validate(raw)
    except PydanticValidationError as e:
        raise ValidationFailed("CRM mapping file invalid.", context={"errors": e.errors()}) from e

    bundle = mapping_root.crm_mappings.get(crm_key)
    if bundle is None:
        raise ValidationFailed(
            "CRM mapping missing for configured CRM key.",
            context={"crm_key": crm_key},
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
    return desired
