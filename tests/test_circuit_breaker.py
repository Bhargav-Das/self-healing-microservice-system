
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]

MODULE_PATH = (
    ROOT
    / "services"
    / "order-service"
    / "circuit_breaker.py"
)

spec = importlib.util.spec_from_file_location(
    "circuit_breaker",
    MODULE_PATH
)

module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

CircuitBreaker = module.CircuitBreaker
CircuitState = module.CircuitState
CircuitOpenError = module.CircuitOpenError


def test_initial_state():
    breaker = CircuitBreaker()

    assert breaker.state == CircuitState.CLOSED
    assert breaker.allow_request() is True


def test_opens_after_three_failures():
    breaker = CircuitBreaker(failure_threshold=3)

    breaker.record_failure()
    breaker.record_failure()

    assert breaker.state == CircuitState.CLOSED

    breaker.record_failure()

    assert breaker.state == CircuitState.OPEN

    with pytest.raises(CircuitOpenError):
        breaker.allow_request()


def test_success_resets_failure_count():
    breaker = CircuitBreaker()

    breaker.record_failure()
    breaker.record_success()

    assert breaker.failure_count == 0
    assert breaker.state == CircuitState.CLOSED


def test_half_open_recovery():
    breaker = CircuitBreaker(
        failure_threshold=1,
        recovery_timeout=0,
    )

    breaker.record_failure()

    assert breaker.state == CircuitState.OPEN

    assert breaker.allow_request() is True
    assert breaker.state == CircuitState.HALF_OPEN

    with pytest.raises(CircuitOpenError):
        breaker.allow_request()

    breaker.record_success()

    assert breaker.state == CircuitState.CLOSED


def test_failed_half_open_probe_reopens():
    breaker = CircuitBreaker(
        failure_threshold=1,
        recovery_timeout=0,
    )

    breaker.record_failure()
    breaker.allow_request()
    breaker.record_failure()

    assert breaker.state == CircuitState.OPEN
