# Changelog

All notable changes to this project are documented here.

## Phase 6 — Documentation & polish

- README case study, architecture doc, ADRs (001–003), runbook, problem definition.
- `docs_enabled` setting for OpenAPI; graceful DB engine dispose on shutdown.
- AI circuit breaker; retry with jitter (LLM timeouts, CRM writes, Slack webhook).
- Docker Compose: Postgres `DATABASE_URL` for app service; `asyncpg` dependency.
- Sample fixtures under `tests/fixtures/sample_inputs/`.

## Phase 5 — Evaluation pipeline

- `eval/test_set.jsonl` (27+ cases), `make evaluate`, `eval/results/` JSON reports.
- Metric helpers in `eval/metrics.py`.

## Phase 4 — API & processing

- `/api/v1/process`, meetings, actions, health; `MeetingProcessService` orchestration.
- Idempotency via transcript hash; duplicate detection.

## Phase 3 — Data layer

- SQLAlchemy models, Alembic migrations, repositories.

## Phase 2 — Domain & integrations

- CRM mapping YAML, HubSpot mock, Slack/email mocks, notification rules.

## Phase 1 — Foundation

- FastAPI app, `AIClient` mock, extraction service, Pydantic schemas.
