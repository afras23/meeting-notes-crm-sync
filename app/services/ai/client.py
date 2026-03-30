"""
AI client wrapper.

Provides a unified interface for AI calls with prompt version tracking and cost controls.
"""

# Standard library
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass

# Local
from app.core.exceptions import CostLimitExceeded, ExtractionFailed

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AICallResult:
    """Result from an AI call with tracking metadata."""

    content: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: float
    provider: str
    model: str
    prompt_name: str
    prompt_version: str


def _estimate_tokens(text: str) -> int:
    """
    Estimate tokens from text length.

    Uses a conservative heuristic (~4 chars/token) to keep cost tracking consistent
    even when using a mock provider.
    """

    return max(1, len(text) // 4)


class AIClient:
    """Unified AI client with cost tracking and daily budget enforcement."""

    def __init__(
        self,
        *,
        provider: str,
        model: str,
        max_daily_cost_usd: float,
        timeout_seconds: int,
    ) -> None:
        self._provider = provider
        self._model = model
        self._max_daily_cost_usd = max_daily_cost_usd
        self._timeout_seconds = timeout_seconds
        self._daily_cost_usd = 0.0
        self._request_count = 0

    @property
    def daily_cost_usd(self) -> float:
        """Current in-process daily cost total (USD)."""

        return self._daily_cost_usd

    @property
    def request_count(self) -> int:
        """Total number of AI requests made by this process."""

        return self._request_count

    @property
    def max_daily_cost_usd(self) -> float:
        """Daily cost budget (USD)."""

        return self._max_daily_cost_usd

    async def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        prompt_name: str,
        prompt_version: str,
    ) -> AICallResult:
        """
        Generate JSON from prompts.

        Args:
            system_prompt: System instructions for the model.
            user_prompt: User content prompt.
            prompt_name: Prompt template name.
            prompt_version: Prompt template version.

        Returns:
            AICallResult with content and cost metadata.

        Raises:
            CostLimitExceeded: If budget exhausted.
            ExtractionFailed: If provider is unsupported.
        """

        if self._daily_cost_usd >= self._max_daily_cost_usd:
            raise CostLimitExceeded(self._daily_cost_usd, self._max_daily_cost_usd)

        start = time.monotonic()
        if self._provider == "mock":
            content = self._mock_response(user_prompt=user_prompt)
        else:
            raise ExtractionFailed(
                "Only AI_PROVIDER=mock is supported in this starter rebuild.",
                context={"provider": self._provider},
            )

        latency_ms = (time.monotonic() - start) * 1000.0
        input_tokens = _estimate_tokens(system_prompt) + _estimate_tokens(user_prompt)
        output_tokens = _estimate_tokens(content)
        cost_usd = (input_tokens + output_tokens) * 0.0000005

        self._daily_cost_usd += cost_usd
        self._request_count += 1

        logger.info(
            "AI request completed",
            extra={
                "provider": self._provider,
                "model": self._model,
                "prompt_name": prompt_name,
                "prompt_version": prompt_version,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": round(cost_usd, 8),
                "latency_ms": round(latency_ms, 1),
                "daily_total_cost_usd": round(self._daily_cost_usd, 6),
            },
        )

        return AICallResult(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            provider=self._provider,
            model=self._model,
            prompt_name=prompt_name,
            prompt_version=prompt_version,
        )

    def _mock_response(self, *, user_prompt: str) -> str:
        """
        Produce a deterministic mock extraction matching MeetingExtraction schema.
        """

        lower = user_prompt.lower()
        stage = "qualification"
        old_stage = "lead"
        if "proposal" in lower:
            stage = "proposal"
            old_stage = "qualification"
        if "closed won" in lower or "won" in lower:
            stage = "closed_won"
            old_stage = "negotiation"

        amount = 10000.0 if "10k" in lower else None
        follow_up = "2026-04-15" if "follow" in lower else "2026-04-01"

        payload = {
            "title": "Sales call",
            "summary": "Discussed requirements, stakeholders, and next steps.",
            "attendees": [
                {"name": "Alex Rep", "role": "AE", "email": "rep@example.com"},
                {"name": "Jordan Buyer", "role": "champion", "email": "buyer@example.com"},
            ],
            "action_items": [
                {
                    "owner": "rep@example.com",
                    "description": "Send follow-up email with pricing",
                    "due_date_iso": "2026-04-05T17:00:00+00:00",
                    "status": "open",
                }
            ],
            "decisions": [
                {"text": "Proceed with technical review next week.", "decided_by": "Jordan Buyer"}
            ],
            "deal_stage_change": {"old_stage": old_stage, "new_stage": stage},
            "next_steps": "Schedule technical deep-dive and confirm budget.",
            "follow_up_date": follow_up,
            "sentiment": "positive",
            "crm_updates": {"deal": {"amount": amount, "stage": stage}},
            "confidence": 0.9,
        }
        return json.dumps(payload)
