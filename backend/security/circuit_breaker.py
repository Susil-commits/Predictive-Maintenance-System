"""
PMS AI Circuit Breaker & High-Availability Resiliency Engine.

Guarantees high service uptime even when third-party LLM providers (Gemini, OpenAI)
experience rate limits (HTTP 429), network outages, or latency spikes.

Finite State Machine:
- CLOSED: Normal operation. All requests forwarded to primary AI provider.
- OPEN: Failure threshold exceeded. All traffic immediately diverted to secondary/fallback provider.
- HALF_OPEN: Recovery probe. Tests whether primary provider has recovered.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
from typing import Dict, List, Optional

logger = logging.getLogger("pms.security.circuit_breaker")


class CircuitState(str, enum.Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class AICircuitBreaker:
    """Thread-safe circuit breaker protecting downstream LLM provider quotas and latency."""

    def __init__(
        self,
        provider_name: str,
        failure_threshold: int = 3,
        recovery_timeout_seconds: float = 15.0,
    ):
        self.provider_name = provider_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0
        self._lock = threading.Lock()

    def can_execute(self) -> bool:
        """Determines if the provider should receive requests."""
        with self._lock:
            now = time.time()
            if self.state == CircuitState.CLOSED:
                return True

            if self.state == CircuitState.OPEN:
                if now - self.last_failure_time >= self.recovery_timeout_seconds:
                    logger.info(
                        f"[CircuitBreaker:{self.provider_name}] Recovery timeout expired. Transitioning OPEN -> HALF_OPEN."
                    )
                    self.state = CircuitState.HALF_OPEN
                    return True
                return False

            if self.state == CircuitState.HALF_OPEN:
                # In half-open state, allow a single probe request
                return True

            return False

    def record_success(self) -> None:
        """Records a successful LLM interaction and resets the circuit breaker."""
        with self._lock:
            if self.state in (CircuitState.HALF_OPEN, CircuitState.OPEN):
                logger.info(
                    f"[CircuitBreaker:{self.provider_name}] Provider recovered. Transitioning {self.state.value} -> CLOSED."
                )
            self.failure_count = 0
            self.state = CircuitState.CLOSED

    def record_failure(self) -> None:
        """Records an LLM failure (exception, timeout, 429, 5xx)."""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.state == CircuitState.HALF_OPEN:
                logger.warning(
                    f"[CircuitBreaker:{self.provider_name}] Probe failed in HALF_OPEN. Transitioning back to OPEN."
                )
                self.state = CircuitState.OPEN
            elif self.state == CircuitState.CLOSED and self.failure_count >= self.failure_threshold:
                logger.error(
                    f"[CircuitBreaker:{self.provider_name}] Threshold exceeded ({self.failure_count}/{self.failure_threshold}). "
                    f"Tripping circuit CLOSED -> OPEN."
                )
                self.state = CircuitState.OPEN

    def get_status(self) -> Dict[str, object]:
        """Returns diagnostic telemetry for monitoring and health dashboards."""
        with self._lock:
            return {
                "provider": self.provider_name,
                "state": self.state.value,
                "failure_count": self.failure_count,
                "failure_threshold": self.failure_threshold,
                "last_failure_time": self.last_failure_time,
                "is_available": self.state != CircuitState.OPEN,
            }


class AIFailoverManager:
    """Manages ordered multi-provider failover with individual circuit breakers."""

    def __init__(self, provider_names: Optional[List[str]] = None):
        names = provider_names or ["gemini", "openai"]
        self.breakers: Dict[str, AICircuitBreaker] = {name: AICircuitBreaker(provider_name=name) for name in names}

    def get_breaker(self, provider_name: str) -> AICircuitBreaker:
        """Retrieves or creates a circuit breaker for a given provider."""
        if provider_name not in self.breakers:
            self.breakers[provider_name] = AICircuitBreaker(provider_name=provider_name)
        return self.breakers[provider_name]

    def get_healthy_provider(self, preferred_order: Optional[List[str]] = None) -> Optional[str]:
        """Returns the first provider whose circuit breaker is not in OPEN state."""
        order = preferred_order or list(self.breakers.keys())
        for name in order:
            breaker = self.get_breaker(name)
            if breaker.can_execute():
                return name
        return None

    def all_statuses(self) -> List[Dict[str, object]]:
        """Returns operational states for all managed providers."""
        return [b.get_status() for b in self.breakers.values()]


# Global singleton instance
_failover_manager = AIFailoverManager()


def get_failover_manager() -> AIFailoverManager:
    return _failover_manager


def get_circuit_breaker(provider_name: str = "gemini") -> AICircuitBreaker:
    return _failover_manager.get_breaker(provider_name)
