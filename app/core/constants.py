"""
Application constants.

Defines stable identifiers and defaults shared across layers.
"""

# Standard library
from __future__ import annotations

from typing import Final

CORRELATION_ID_HEADER: Final[str] = "x-correlation-id"
MAX_INPUT_PREVIEW_CHARS: Final[int] = 200
# Max characters sent to the LLM prompt (full transcript still hashed for idempotency).
MAX_TRANSCRIPT_CHARS_FOR_LLM: Final[int] = 20_000
