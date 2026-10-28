"""
Thermal Runaway Scenario: Simulates progressive Heat Dissipation Failure (HDF).
Coolant circuit failure triggers exponential thermal gradient and acoustic secondary stress.
"""

import math
from datetime import datetime, timezone

from .base import BaseScenario, ScenarioStep


class ThermalRunawayScenario(BaseScenario):
    """
    Models exponential thermal escalation caused by coolant heat exchanger clogging.
    Initial state: Nominal operating conditions (65°C).
    Fault injection: At step 15, coolant drops 75%, temperature accelerates past 95°C.
    """

    def __init__(
        self,
        total_steps: int = 40,
        step_interval_seconds: float = 2.0,
        machine_id: str = "MILL-THERMAL-01",
    ):
        super().__init__(
            name="Thermal Runaway (HDF)",
            failure_mode="Thermal Heat Dissipation Failure",
            total_steps=total_steps,
            step_interval_seconds=step_interval_seconds,
            machine_id=machine_id,
            ambient_temp=25.0,
        )

    def generate(self) -> list[ScenarioStep]:
        steps = []
        base_temp = 68.0
        base_rpm = 1800.0
        base_pressure = 22.0
        base_vib = 0.22
        base_hours = 1500.0

        for i in range(self.total_steps):
            elapsed = i * self.step_interval_seconds
            t_now = datetime.now(timezone.utc).isoformat()

            if i < 12:
                # Nominal baseline phase
                curr_temp = base_temp + 0.4 * math.sin(i)
                curr_rpm = base_rpm
                curr_p = base_pressure
                curr_vib = base_vib
                curr_hours = base_hours
                temp_rate = 0.05
                is_fail = False
                driver = None
                notes = "Nominal thermal equilibrium"
                regime = "steady_state_light"
            else:
                # Coolant circuit loss -> exponential heat rise
                delta_steps = i - 12
                progress = min(1.0, delta_steps / 10.0)
                curr_temp = base_temp + 27.0 * progress
                curr_rpm = base_rpm + 1000.0 * progress
                curr_p = base_pressure + 10.0 * progress
                curr_vib = base_vib + 0.36 * progress
                curr_hours = base_hours + 3000.0 * progress
                temp_rate = 1.85 * math.exp(-delta_steps / 12.0) + 0.4
                is_fail = progress >= 0.7
                driver = "temperature"
                notes = "Coolant heat exchanger blocked; thermal gradient accelerating"
                regime = "steady_state_heavy"

            telemetry = {
                "temperature": round(curr_temp, 2),
                "rpm": round(curr_rpm, 1),
                "pressure": round(curr_p, 2),
                "vibration": round(curr_vib, 3),
                "operating_hours": round(curr_hours, 1),
                "temp_rate_of_change": round(temp_rate, 2),
                "context": {
                    "machine_id": self.machine_id,
                    "machine_type": "High-Precision-Spindle",
                    "regime": regime,
                    "ambient_temperature": self.ambient_temp,
                    "hours_since_last_service": 65.0,
                    "recent_fault_count_24h": 1 if i > 25 else 0,
                },
            }

            steps.append(
                ScenarioStep(
                    step_index=i,
                    elapsed_seconds=elapsed,
                    timestamp=t_now,
                    telemetry=telemetry,
                    expected_failure=is_fail,
                    expected_dominant_driver=driver,
                    notes=notes,
                )
            )

        return steps
