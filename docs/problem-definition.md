# Problem definition

## Business context

B2B sales teams run dozens of calls per week per rep. Each call produces valuable information: who attended, what was promised, whether the deal moved stage, risks, and next steps. That information is **contractually and commercially important** — it drives forecasting, handoffs, and follow-up.

## Current pain

- **Manual CRM entry** after calls is tedious; reps skip it during busy weeks.
- **Delayed entry** means data is entered from memory, not the conversation — fields are wrong or incomplete.
- **Pipeline reviews** rely on CRM truth; bad CRM data leads to bad forecasts and lost deals.

## What “good” looks like

- Within minutes of a call, the CRM reflects **action items with owners**, **deal stage** when discussed, **next steps**, and a **searchable summary**.
- **Human edits** in the CRM are not wiped by automation unless the meeting explicitly changes that field.
- **Managers** get **Slack** alerts on stage changes and new actions without opening the CRM.

## Evaluation methodology

The `eval/` harness runs **labeled** transcripts (`eval/test_set.jsonl`) and compares extraction output to expected fields. The default runner uses **gold JSON** produced from labels (same schema as the LLM) so CI validates metrics and reporting without live API keys. To measure a **real** model, swap `AIClient` for a provider-backed implementation and re-run `make evaluate`.

## Success metrics (examples)

- Extraction accuracy (attendees, actions, decisions, stage, sentiment).
- CRM mapping accuracy vs YAML-derived desired fields.
- Cost and latency per meeting (tokens + wall time).
