"""
Base Scenario Engine for PMS Degradation Simulation Harness.
"""

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ScenarioStep:
    step_index: int
    elapsed_seconds: float
    timestamp: str
    telemetry: dict[str, Any]
    expected_failure: bool
    expected_dominant_driver: str | None = None
    notes: str = ""

    def to_payload(self) -> dict[str, Any]:
        """Converts step telemetry and context into a PMS API payload."""
        return dict(self.telemetry)


class BaseScenario(ABC):
    """Abstract base class for industrial degradation scenario simulations."""

    def __init__(
        self,
        name: str,
        failure_mode: str,
        total_steps: int = 50,
        step_interval_seconds: float = 1.0,
        machine_id: str = "SIM-CNC-001",
        ambient_temp: float = 24.0,
    ):
        self.name = name
        self.failure_mode = failure_mode
        self.total_steps = total_steps
        self.step_interval_seconds = step_interval_seconds
        self.machine_id = machine_id
        self.ambient_temp = ambient_temp

    @abstractmethod
    def generate(self) -> list[ScenarioStep]:
        """Generates sequence of telemetry steps modeling physical degradation."""
        pass

    def evaluate_run(self, results: list[dict[str, Any]], steps: list[ScenarioStep]) -> dict[str, Any]:
        """
        Evaluates PMS responses across the generated sequence:
        - Detection step & time to alert
        - Precision/recall on failure steps
        - Root cause attribution alignment
        """
        assert len(results) == len(steps), "Mismatch between results and scenario steps"

        first_detection_step = None
        first_detection_time = None
        correct_root_cause_hits = 0
        expected_failure_count = sum(1 for s in steps if s.expected_failure)
        detected_failure_count = 0
        false_alarms = 0

        probabilities = []

        for idx, (res, step) in enumerate(zip(results, steps)):
            prob = res.get("probability", 0.0)
            probabilities.append(prob)
            is_high = res.get("failure_risk") == "HIGH"

            if is_high:
                detected_failure_count += 1
                if first_detection_step is None:
                    first_detection_step = idx
                    first_detection_time = step.elapsed_seconds

                if not step.expected_failure:
                    false_alarms += 1

                # Check if root cause matches expected driver
                if step.expected_dominant_driver:
                    top_factor = str(res.get("top_risk_factor", "")).lower()
                    if step.expected_dominant_driver.lower() in top_factor:
                        correct_root_cause_hits += 1
            else:
                if step.expected_failure and first_detection_step is None:
                    # Missed early failure
                    pass

        detected = first_detection_step is not None
        root_cause_accuracy = (
            (correct_root_cause_hits / detected_failure_count) if detected_failure_count > 0 else 0.0
        )

        return {
            "scenario": self.name,
            "failure_mode": self.failure_mode,
            "total_steps": self.total_steps,
            "expected_failures": expected_failure_count,
            "detected_failures": detected_failure_count,
            "first_detection_step": first_detection_step,
            "time_to_detect_seconds": first_detection_time,
            "false_alarms": false_alarms,
            "root_cause_accuracy_pct": round(root_cause_accuracy * 100, 2),
            "max_probability": max(probabilities) if probabilities else 0.0,
            "min_probability": min(probabilities) if probabilities else 0.0,
            "pass": detected and (false_alarms == 0),
        }

