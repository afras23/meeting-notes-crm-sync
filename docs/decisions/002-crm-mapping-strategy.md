# ADR 002: CRM mapping strategy

## Status

Accepted

## Context

CRM field names differ by vendor (HubSpot `dealname` vs Salesforce equivalents). Engineering wants to avoid hardcoded property names in business logic.

## Decision

- Store mappings in **`config/crm_mapping.yaml`** under named CRM keys (`hubspot`, future `salesforce`).
- Each field declares a `source` path into the meeting JSON (`meeting.title`, `meeting.crm_updates.deal.amount`, etc.).
- `CRMService` resolves paths from `meeting.model_dump()` and builds a **desired** dict for the deal entity.
- **Per-CRM adapters** are thin: the HubSpot mock implements `get_deal`, `update_deal`, `add_note`; a real adapter would implement the same interface.

## Consequences

- Adding a field is YAML-only when the meeting model already exposes the value.
- New CRM = new YAML section + new adapter class + config key.

## Alternatives considered

- **Hardcoded mapping in Python**: fastest initially, worst for portfolio demos and multi-tenant configs — rejected.
