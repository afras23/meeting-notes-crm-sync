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


class CRMMappingConfig(BaseModel):
    """Top-level CRM mapping configuration."""

    version: str = Field(..., description="Mapping config version.")
    crm: str = Field(..., description="CRM identifier.")
    entities: dict[str, CRMEntityMapping] = Field(
        default_factory=dict, description="Entity mappings."
    )
