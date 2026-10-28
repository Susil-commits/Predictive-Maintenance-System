"""
PyTest Test Suite wrapping the PMS Harness Engineering Suite.
Ensures scenario simulations, AI/RAG evaluations, and chaos fault-injection
execute automatically during CI/CD test runs.
"""

from harness.chaos.circuit_breaker_chaos import run_circuit_breaker_chaos_experiment
from harness.chaos.db_resilience_chaos import run_database_resilience_experiment
from harness.eval.eval_harness import AIEvalHarness
from harness.runner import HarnessRunner
from harness.scenarios import (
    OverstrainScenario,
    SensorGlitchScenario,
    ThermalRunawayScenario,
    ToolWearScenario,
)


def test_thermal_runaway_scenario():
    """Harness Simulation: Verifies thermal runaway failure detection."""
    runner = HarnessRunner()
    summary = runner.run_scenario(ThermalRunawayScenario())
    assert summary["pass"] is True
    assert summary["detected_failures"] > 0
    assert summary["false_alarms"] == 0


def test_overstrain_scenario():
    """Harness Simulation: Verifies mechanical overstrain detection."""
    runner = HarnessRunner()
    summary = runner.run_scenario(OverstrainScenario())
    assert summary["pass"] is True
    assert summary["detected_failures"] > 0
    assert summary["false_alarms"] == 0


def test_tool_wear_scenario():
    """Harness Simulation: Verifies tool wear flank degradation detection."""
    runner = HarnessRunner()
    summary = runner.run_scenario(ToolWearScenario())
    assert summary["pass"] is True
    assert summary["detected_failures"] > 0
    assert summary["false_alarms"] == 0


def test_sensor_glitch_scenario():
    """Harness Simulation: Verifies edge sensor glitch handling."""
    runner = HarnessRunner()
    summary = runner.run_scenario(SensorGlitchScenario())
    assert summary["pass"] is True
    assert summary["detected_failures"] > 0
    assert summary["false_alarms"] == 0


def test_ai_rag_evaluation_golden_suite():
    """AI Eval Harness: Verifies citation grounding and safety guardrails on golden incidents."""
    eval_harness = AIEvalHarness()
    results = eval_harness.run_all()
    failed_cases = [r["id"] for r in results if not r["pass"]]
    assert len(failed_cases) == 0, f"Golden evaluation failed on cases: {failed_cases}"


def test_chaos_circuit_breaker_fault_injection():
    """Chaos Harness: Verifies AI circuit breaker tripping, fast rejection, and recovery."""
    result = run_circuit_breaker_chaos_experiment()
    assert result["pass"] is True
    assert result["fast_rejection_latency_us"] < 500.0


def test_chaos_database_resilience():
    """Chaos Harness: Verifies that DB connection failure does not crash the prediction API."""
    result = run_database_resilience_experiment()
    assert result["pass"] is True

