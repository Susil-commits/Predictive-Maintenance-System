"""
Overstrain Scenario: Simulates acute Overstrain Failure (OSF).
High cutting feed rate or hard workpiece inclusion creates severe torque drag and hydraulic pressure spike.
"""

import math
from datetime import datetime, timezone

from .base import BaseScenario, ScenarioStep


class OverstrainScenario(BaseScenario):
    """
    Models acute hydraulic overpressure and motor overstrain.
    Initial state: Nominal cutting cycle (pressure 22 bar, 2600 RPM).
    Fault injection: At step 10, deep feed cut stalls spindle; pressure spikes to 42+ bar.
    """

    def __init__(
        self,
        total_steps: int = 35,
        step_interval_seconds: float = 1.0,
        machine_id: str = "LATHE-OVERSTRAIN-02",
    ):
        super().__init__(
            name="Overstrain Failure (OSF)",
            failure_mode="Hydraulic & Mechanical Overstrain",
            total_steps=total_steps,
            step_interval_seconds=step_interval_seconds,
            machine_id=machine_id,
            ambient_temp=23.0,
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

            if i < 10:
                curr_pressure = base_pressure + 0.3 * math.sin(i)
                curr_rpm = base_rpm
                curr_temp = base_temp
                curr_vib = base_vib
                curr_hours = base_hours
                is_fail = False
                driver = None
                notes = "Nominal face milling pass"
            elif i < 26:
                # Heavy inclusion / overstrain event
                progress = min(1.0, (i - 10) / 4.0)
                curr_pressure = base_pressure + 16.0 * progress
                curr_rpm = base_rpm + 1000.0 * progress
                curr_temp = base_temp + 7.0 * progress
                curr_vib = base_vib + 0.40 * progress
                curr_hours = base_hours + 3000.0 * progress
                is_fail = progress >= 0.75
                driver = "pressure"
                notes = "Workpiece hard spot detected; hydraulic accumulator pressure spiking"
            else:
                # Relief valve actuation / partial recovery
                curr_pressure = 25.0
                curr_rpm = base_rpm
                curr_temp = base_temp + 2.0
                curr_vib = base_vib
                curr_hours = base_hours + 50.0
                is_fail = False
                driver = None
                notes = "De-rating active; pressure stabilized"

            telemetry = {
                "temperature": round(curr_temp, 1),
                "rpm": round(curr_rpm, 1),
                "pressure": round(curr_pressure, 2),
                "vibration": round(curr_vib, 3),
                "operating_hours": round(curr_hours, 1),
                "context": {
                    "machine_id": self.machine_id,
                    "machine_type": "5-Axis-Milling-Center",
                    "regime": "steady_state_heavy" if is_fail else "steady_state_light",
                    "ambient_temperature": self.ambient_temp,
                    "hours_since_last_service": 140.0,
                    "recent_fault_count_24h": 2 if is_fail else 0,
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

