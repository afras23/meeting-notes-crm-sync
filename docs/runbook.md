# Runbook

## Health checks

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/health` | Liveness — process up |
| `GET /api/v1/health/ready` | Readiness — DB ping + AI provider ping |
| `GET /api/v1/metrics` | Operational counters (meetings today, actions pending/overdue, cost) |

Example:

```bash
curl -s http://localhost:8000/api/v1/health | jq
curl -s http://localhost:8000/api/v1/health/ready | jq
```

## Failed CRM syncs

1. Fetch meeting detail: `GET /api/v1/meetings/{meeting_id}`.
2. Response includes `crm_sync.status`: `synced` if a CRM sync row exists for that meeting, else `pending`.
3. Check application logs for `CRM apply_updates failed` (process pipeline logs and continues with error-shaped `crm_result`).
4. Re-process is not automatic; fix CRM/mapping and submit a new process request if needed.

## Add a new CRM mapping

1. Edit `config/crm_mapping.yaml` — add a new key under `crm_mappings` (e.g. `salesforce`) with `entities.deal.fields` mapping HubSpot-style keys to `source` paths.
2. Set `CRM_MAPPING_CRM` / `crm_mapping_crm` in settings to the new key (see `app/config.py`).
3. Implement a client matching `HubSpotClientMock`’s async interface and wire it in `dependencies.py`.

## Update extraction prompts

1. Edit `app/services/ai/prompts.py` — templates are versioned (`PromptTemplate.version`).
2. Bump `version` when behavior changes; audit entries store `prompt_name` + `prompt_version` from the AI call result.

## Action items (filters)

- List: `GET /api/v1/actions?page=1&page_size=20`
- By status: `?status=open` (or `done`, `cancelled`)
- Overdue flag: `?overdue=true` (repository treats open items past deadline as overdue)
- By owner: `?owner=Name`
- By meeting: `?meeting_id=...`

## Common errors

| Symptom | Likely cause | Recovery |
|---------|--------------|----------|
| 422 on `/process` | Missing/empty body or wrong `Content-Type` | Use `application/json` with `text` or multipart with `audio` |
| 409 DUPLICATE | Same transcript hash already processed | Use new content or query existing meeting |
| 503 COST_LIMIT | AI daily budget exceeded | Raise `MAX_DAILY_COST_USD` or wait / reset |
| 500 EXTRACTION_FAILED | Invalid JSON from model or validation | Check logs, prompt, transcript length |
| DB errors on `/ready` | `DATABASE_URL` wrong or DB down | Fix connection string; Postgres: `pg_isready` |

## Settings

- `docs_enabled` (default `true`): OpenAPI at `/docs` and `/openapi.json`. Set `false` in locked-down environments.
