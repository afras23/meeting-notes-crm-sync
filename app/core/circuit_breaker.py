"""
Simple circuit breaker for external dependency calls (AI, CRM, etc.).

Opens after consecutive failures; half-open after cooldown; closes on success.
"""

# Standard library
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class CircuitBreaker:
    """
    Sliding-window style breaker (in-process).

    Attributes:
        failure_threshold: Failures before opening the circuit.
        recovery_seconds: Seconds to wait before trying again (half-open).
    """

    failure_threshold: int = 5
    recovery_seconds: float = 30.0
    _failures: int = 0
    _opened_at: float | None = field(default=None, repr=False)

    def allow(self) -> bool:
        """Return False if circuit is open and recovery window has not elapsed."""

        return self._opened_at is None or (
            time.monotonic() - self._opened_at >= self.recovery_seconds
        )

    def record_success(self) -> None:
        """Reset breaker after a successful call."""

        self._failures = 0
        self._opened_at = None

    def record_failure(self) -> None:
        """Increment failures and open the circuit when threshold is reached."""

        self._failures += 1
        if self._failures >= self.failure_threshold:
            self._opened_at = time.monotonic()
