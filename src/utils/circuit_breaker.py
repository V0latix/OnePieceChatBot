"""Circuit breaker simple pour proteger les appels aux services externes."""

from __future__ import annotations

import time
from enum import Enum


class State(Enum):
    CLOSED = "closed"        # Nominal — les requetes passent
    OPEN = "open"            # En panne — requetes bloquees immediatement
    HALF_OPEN = "half_open"  # Test — une requete de sonde autorisee


class CircuitBreakerOpen(Exception):
    """Levee quand le circuit est ouvert (service indisponible)."""

    def __init__(self, service: str, retry_in: float) -> None:
        self.service = service
        self.retry_in = retry_in
        super().__init__(f"Circuit ouvert pour '{service}'. Retry dans {retry_in:.0f}s.")


class CircuitBreaker:
    """Circuit breaker thread-safe (GIL suffit pour ce projet mono-worker).

    Transitions:
        CLOSED  --(failure_threshold echecs consecutifs)--> OPEN
        OPEN    --(recovery_timeout ecoule)             --> HALF_OPEN
        HALF_OPEN --(succes)                            --> CLOSED
        HALF_OPEN --(echec)                             --> OPEN
    """

    def __init__(
        self,
        service: str,
        failure_threshold: int = 3,
        recovery_timeout: float = 60.0,
    ) -> None:
        self.service = service
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

        self._state = State.CLOSED
        self._failure_count = 0
        self._opened_at: float | None = None

    @property
    def state(self) -> State:
        if self._state == State.OPEN and self._opened_at is not None:
            if time.monotonic() - self._opened_at >= self.recovery_timeout:
                self._state = State.HALF_OPEN
        return self._state

    def _retry_in(self) -> float:
        if self._opened_at is None:
            return 0.0
        elapsed = time.monotonic() - self._opened_at
        return max(0.0, self.recovery_timeout - elapsed)

    def before_call(self) -> None:
        """Appeler avant chaque tentative. Leve CircuitBreakerOpen si ouvert."""
        current = self.state
        if current == State.OPEN:
            raise CircuitBreakerOpen(self.service, self._retry_in())

    def on_success(self) -> None:
        """Appeler apres un succes."""
        self._failure_count = 0
        self._state = State.CLOSED
        self._opened_at = None

    def on_failure(self) -> None:
        """Appeler apres un echec."""
        self._failure_count += 1
        if self._state == State.HALF_OPEN or self._failure_count >= self.failure_threshold:
            self._state = State.OPEN
            self._opened_at = time.monotonic()
            self._failure_count = 0
