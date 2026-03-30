"""Unit tests for the AI circuit breaker helper."""

from __future__ import annotations

import time

from app.core.circuit_breaker import CircuitBreaker


def test_circuit_opens_after_failures() -> None:
    b = CircuitBreaker(failure_threshold=2, recovery_seconds=60.0)
    assert b.allow() is True
    b.record_failure()
    assert b.allow() is True
    b.record_failure()
    assert b.allow() is False


def test_circuit_closes_on_success() -> None:
    b = CircuitBreaker(failure_threshold=2, recovery_seconds=0.01)
    b.record_failure()
    b.record_success()
    assert b.allow() is True


def test_circuit_half_open_after_recovery() -> None:
    b = CircuitBreaker(failure_threshold=1, recovery_seconds=0.2)
    b.record_failure()
    assert b.allow() is False
    time.sleep(0.25)
    assert b.allow() is True
