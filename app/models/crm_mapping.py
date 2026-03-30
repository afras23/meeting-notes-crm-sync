"""
CRM mapping models.

Defines how extracted meeting fields map into CRM entity fields via YAML configuration.
"""

# Standard library
from __future__ import annotations

# Third party
from pydantic import BaseModel, Field


class CRMFieldMapping(BaseModel):
    """Mapping from a source path to a destination CRM field."""

    source: str = Field(..., min_length=1, description="Dot-path into structured meeting data.")


class CRMEntityMapping(BaseModel):
    """Mapping configuration for a CRM entity (e.g. deal)."""

    fields: dict[str, CRMFieldMapping] = Field(
        default_factory=dict, description="CRM field mappings."
    )


class CRMMappingBundle(BaseModel):
    """Entity mappings for one CRM product (e.g. HubSpot)."""

    entities: dict[str, CRMEntityMapping] = Field(
        default_factory=dict, description="Entity mappings."
    )


class CRMMappingRoot(BaseModel):
    """Top-level file supporting multiple CRMs."""

    version: str = Field(..., description="Mapping config version.")
    crm_mappings: dict[str, CRMMappingBundle] = Field(
        default_factory=dict, description="Per-CRM mapping bundles keyed by CRM id."
    )
