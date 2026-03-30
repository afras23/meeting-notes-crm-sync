"""
Scripted / flaky AI clients for unit tests (no real LLM calls).
"""

# Standard library
from __future__ import annotations

import json

# Local
from app.services.ai.client import AICallResult, AIClient


class ScriptedAIClient(AIClient):
    """Returns queued JSON payloads from tests; falls back to mock provider when queue empty."""

    def __init__(
        self,
        *,
        provider: str = "mock",
        model: str = "mock-llm",
        max_daily_cost_usd: float = 100.0,
        timeout_seconds: int = 30,
    ) -> None:
        super().__init__(
            provider=provider,
            model=model,
            max_daily_cost_usd=max_daily_cost_usd,
            timeout_seconds=timeout_seconds,
        )
        self._queue: list[str] = []

    def enqueue_json(self, payload: dict[str, object] | str) -> None:
        if isinstance(payload, dict):
            self._queue.append(json.dumps(payload))
        else:
            self._queue.append(payload)

    async def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        prompt_name: str,
        prompt_version: str,
    ) -> AICallResult:
        if self._queue:
            content = self._queue.pop(0)
            return AICallResult(
                content=content,
                input_tokens=1,
                output_tokens=1,
                cost_usd=0.0,
                latency_ms=0.0,
                provider=self._provider,
                model=self._model,
                prompt_name=prompt_name,
                prompt_version=prompt_version,
            )
        return await super().generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            prompt_name=prompt_name,
            prompt_version=prompt_version,
        )


class FlakyAIClient(AIClient):
    """Raises TimeoutError for the first N attempts, then delegates to mock."""

    def __init__(
        self,
        *,
        failures_before_success: int = 0,
        provider: str = "mock",
        model: str = "mock-llm",
        max_daily_cost_usd: float = 100.0,
        timeout_seconds: int = 30,
    ) -> None:
        super().__init__(
            provider=provider,
            model=model,
            max_daily_cost_usd=max_daily_cost_usd,
            timeout_seconds=timeout_seconds,
        )
        self._failures_before_success = failures_before_success
        self._attempts = 0

    async def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        prompt_name: str,
        prompt_version: str,
    ) -> AICallResult:
        if self._attempts < self._failures_before_success:
            self._attempts += 1
            raise TimeoutError("simulated timeout")
        return await super().generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            prompt_name=prompt_name,
            prompt_version=prompt_version,
        )


class AlwaysTimeoutAIClient(AIClient):
    """Always raises TimeoutError (for retry exhaustion tests)."""

    def __init__(
        self,
        *,
        provider: str = "mock",
        model: str = "mock-llm",
        max_daily_cost_usd: float = 100.0,
        timeout_seconds: int = 30,
    ) -> None:
        super().__init__(
            provider=provider,
            model=model,
            max_daily_cost_usd=max_daily_cost_usd,
            timeout_seconds=timeout_seconds,
        )

    async def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        prompt_name: str,
        prompt_version: str,
    ) -> AICallResult:
        raise TimeoutError("always timeout")
