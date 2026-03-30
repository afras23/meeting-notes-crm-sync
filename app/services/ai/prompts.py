"""
Prompt templates with versioning.

Centralizes prompt content so behavior changes are tracked and auditable.
"""

# Standard library
from __future__ import annotations

from dataclasses import dataclass
from string import Template


@dataclass(frozen=True)
class PromptTemplate:
    """A versioned prompt template definition."""

    name: str
    version: str
    system: str
    user_template: Template


MEETING_EXTRACTION_V2 = PromptTemplate(
    name="meeting_extraction_v2",
    version="2.0.0",
    system=(
        "You are a meeting analysis system. Extract structured data from meeting transcripts. "
        "Return ONLY valid JSON. Never invent values not present in the transcript. "
        "If a field cannot be determined, use null or an empty list."
    ),
    user_template=Template(
        "Extract a rich meeting schema from the transcript.\n\n"
        "Return JSON with keys:\n"
        "- title (string)\n"
        "- summary (string)\n"
        "- attendees (array of {name, role, email})\n"
        "- action_items (array of {owner, description, due_date_iso, status})\n"
        "- decisions (array of {text, decided_by})\n"
        "- deal_stage_change (object: {old_stage, new_stage} or null)\n"
        "- next_steps (string or null)\n"
        "- follow_up_date (ISO date string or null)\n"
        "- sentiment (string or null)\n"
        "- crm_updates (object: deal: {amount, stage})\n"
        "- confidence (number 0.0-1.0)\n\n"
        "Transcript:\n"
        "${transcript}\n"
    ),
)


PROMPTS: dict[str, PromptTemplate] = {
    MEETING_EXTRACTION_V2.name: MEETING_EXTRACTION_V2,
}


def get_prompt(prompt_name: str, *, transcript: str) -> tuple[str, str, str]:
    """
    Render a prompt by name.

    Args:
        prompt_name: Name of prompt template.
        transcript: Meeting transcript content.

    Returns:
        (system_prompt, user_prompt, prompt_version)

    Raises:
        KeyError: If prompt_name is unknown.
    """

    prompt = PROMPTS[prompt_name]
    return prompt.system, prompt.user_template.substitute(transcript=transcript), prompt.version
