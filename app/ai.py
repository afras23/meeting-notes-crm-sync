import anthropic
import os
import json

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def extract_crm_fields(notes: str):
    prompt = f"""
Extract CRM updates from sales meeting notes.

Return JSON:
- next_steps
- deal_stage_change
- competitors
- budget_signals
- summary

Notes:
{notes}
"""

    res = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}]
    )

    return json.loads(res.content[0].text)
