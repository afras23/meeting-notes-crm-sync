# Meeting Notes → CRM Sync
## Turn sales calls into structured CRM updates (with audit + cost tracking)

> **Architecture:** Python, FastAPI, mock LLM client, mock HubSpot, Docker, CI
> **Status:** Production-grade scaffolding (mock integrations) — ready to swap in real providers

### The Problem
Sales teams lose hours each week manually translating call notes into CRM updates, and pipeline data drifts when updates are delayed or inconsistent.

### The Solution
This service accepts meeting transcripts, extracts structured fields + action items, maps them to CRM properties using `config/crm_mapping.yaml`, applies updates via a CRM client, and records an audit trail with prompt version + cost metadata.

### Key Features
- **Prompt versioning**: deterministic prompt templates in `app/services/ai/prompts.py`
- **Cost tracking**: every AI call reports estimated tokens + USD, enforces daily budget
- **Audit trail**: raw + parsed AI output stored per transcript hash
- **Mock-first integrations**: safe local runs without real API keys
- **Config-driven mapping**: change CRM field mapping without code changes

### Project Structure (high level)
```
app/
  api/routes/ (health, process, meetings, actions)
  services/    (transcription, extraction, crm, notification, ai/)
  models/      (meeting, action_item, crm_mapping, audit)
  repositories/ (in-memory repos)
  integrations/ (mock hubspot/slack/calendar)
config/
  crm_mapping.yaml
  notification_rules.yaml
eval/
scripts/
tests/
```

### How to Run (local)
```bash
python -m venv .venv
source .venv/bin/activate
make install-dev
cp .env.example .env
make run
```

### Quality Gates
```bash
make lint
make test
```

### Evaluation
```bash
make evaluate
```
