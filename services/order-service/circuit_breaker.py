
import logging
import time
from enum import Enum

logger = logging.getLogger("circuit-breaker")


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitOpenError(Exception):
    pass


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold=3,
        recovery_timeout=10,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.opened_at = None
        self.probe_in_progress = False

    def allow_request(self):
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            elapsed = time.monotonic() - self.opened_at

            if elapsed >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.probe_in_progress = False

                logger.warning(
                    "CIRCUIT_HALF_OPEN"
                )
            else:
                raise CircuitOpenError(
                    "Circuit is OPEN"
                )

        if self.state == CircuitState.HALF_OPEN:
            if self.probe_in_progress:
                raise CircuitOpenError(
                    "Half-open probe already running"
                )

            self.probe_in_progress = True
            return True

        raise CircuitOpenError("Request blocked")

    def record_success(self):
        previous_state = self.state

        self.failure_count = 0
        self.opened_at = None
        self.probe_in_progress = False
        self.state = CircuitState.CLOSED

        if previous_state != CircuitState.CLOSED:
            logger.info("CIRCUIT_CLOSED")

    def record_failure(self):
        self.failure_count += 1

        if (
            self.state == CircuitState.HALF_OPEN
            or self.failure_count >= self.failure_threshold
        ):
            self.state = CircuitState.OPEN
            self.opened_at = time.monotonic()
            self.probe_in_progress = False

            logger.error(
                "CIRCUIT_OPEN failures=%s",
                self.failure_count
            )

    def get_status(self):
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
        }
