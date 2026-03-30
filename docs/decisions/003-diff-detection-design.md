# ADR 003: Diff detection before CRM write

## Status

Accepted

## Context

Sales reps often fix deal amounts or stages manually. Blindly overwriting CRM records from meeting extraction would destroy good data.

## Decision

- Always **read** current deal properties from the CRM client.
- Compute **desired** properties from extraction + YAML mapping.
- Apply `_diff_properties`: only keys where `desired[key] != current[key]` (and desired value not `None`) are sent to `update_deal`.
- Keys that are unchanged are listed as `skipped_unchanged` in the CRM result for auditing.

## Algorithm

For each `(key, value)` in desired:

- If `value is None` → skip (do not clear CRM fields unintentionally).
- If `current.get(key) == value` → skip.
- Else → include in `changed` payload.

## Consequences

- Manual edits to fields not present in desired remain untouched.
- Retries on `update_deal` / `add_note` use `retry_async` with backoff + jitter for transient failures.

## Alternatives considered

- **Full replace**: rejected — too destructive.
- **Field-level timestamps from CRM**: not available on mock; optional enhancement for real HubSpot.
