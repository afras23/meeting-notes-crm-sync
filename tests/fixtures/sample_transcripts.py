"""
Realistic transcript snippets for parametrized extraction tests.
"""

SALES_CALL = "Speaker 1: We are moving to proposal stage next week. Next steps: send pricing."

STANDUP = "Speaker 1: Blockers: CI is red. Speaker 2: I will fix the pipeline today."

CLIENT_KICKOFF = (
    "Speaker 1: Welcome. Attendees: Alice (PM), Bob (Eng). "
    "Action: Bob to share architecture doc by Friday."
)

ONE_ON_ONE = (
    "Speaker 1: We decided to promote the internal tool. "
    "Follow-up date: 2026-05-01. Decision recorded by Manager."
)

VERY_SHORT = "Hi."

VERY_LONG_BODY = "word " * 5000

NO_ACTIONS = "Speaker 1: We had a pleasant chat with no follow-ups."

MULTILINGUAL_FR = "Résumé: accord sur le budget. Prochaine étape: signature."

TWENTY_ACTIONS = "\n".join(
    f"Speaker 1: Action {i}: owner person{i}@example.com due 2026-06-{i % 28 + 1:02d}T12:00:00+00:00"
    for i in range(25)
)
