"""
Chaos Experiment: AI Circuit Breaker Outage & FSM Transition Verification.
Injects synthetic provider outages, network timeouts, and recovers downstream health.
"""

import time
from typing import Any

from backend.security.circuit_breaker import AICircuitBreaker, CircuitState


def run_circuit_breaker_chaos_experiment() -> dict[str, Any]:
    """
    Executes a structured fault injection test against AICircuitBreaker FSM:
    Phase 1: Baseline health (state == CLOSED, can_execute == True).
    Phase 2: Outage injection (3 consecutive simulated failures).
    Phase 3: Verify OPEN state (can_execute == False, fast rejection).
    Phase 4: Recovery timer expiration (transition OPEN -> HALF_OPEN).
    Phase 5: Recovery probe success (transition HALF_OPEN -> CLOSED).
    """
    breaker = AICircuitBreaker(
        provider_name="chaos_mock_llm",
        failure_threshold=3,
        recovery_timeout_seconds=0.5,  # Accelerated for test harness
    )

    # Phase 1: Baseline
    p1_pass = (breaker.state == CircuitState.CLOSED) and (breaker.can_execute() is True)

    # Phase 2: Inject Outages
    for _ in range(3):
        breaker.record_failure()

    # Phase 3: Assert OPEN state
    p3_pass = (breaker.state == CircuitState.OPEN) and (breaker.can_execute() is False)

    # Measure rejection latency
    t_start = time.perf_counter()
    rejection_result = breaker.can_execute()
    rejection_latency_us = round((time.perf_counter() - t_start) * 1_000_000, 2)
    fast_rejection_pass = (rejection_result is False) and (rejection_latency_us < 500.0)

    # Phase 4: Wait for recovery timeout
    time.sleep(0.55)
    p4_pass = breaker.can_execute() is True
    half_open_pass = breaker.state == CircuitState.HALF_OPEN

    # Phase 5: Probe success restores CLOSED state
    breaker.record_success()
    p5_pass = (breaker.state == CircuitState.CLOSED) and (breaker.can_execute() is True)

    all_pass = p1_pass and p3_pass and fast_rejection_pass and p4_pass and half_open_pass and p5_pass

    return {
        "experiment": "AI Circuit Breaker Fault Injection",
        "pass": all_pass,
        "phase_1_baseline_closed": p1_pass,
        "phase_3_tripped_open": p3_pass,
        "fast_rejection_latency_us": rejection_latency_us,
        "phase_4_half_open_probe": p4_pass and half_open_pass,
        "phase_5_healed_closed": p5_pass,
    }

