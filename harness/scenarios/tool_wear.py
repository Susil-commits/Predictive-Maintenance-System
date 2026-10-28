"""
Tool Wear Failure (TWF) Scenario: Simulates progressive flank wear and acoustic vibration degradation.
"""

from datetime import datetime, timezone

from .base import BaseScenario, ScenarioStep


class ToolWearScenario(BaseScenario):
    """
    Models continuous cutting edge degradation.
    Initial state: Nominal operating hours (3800h), vibration 0.22 g.
    Progression: Operating hours breach 4800h, flank wear causes high-frequency vibration harmonics > 0.60 g.
    """

    def __init__(
        self,
        total_steps: int = 30,
        step_interval_seconds: float = 1.0,
        machine_id: str = "MILL-TOOLWEAR-03",
    ):
        super().__init__(
            name="Tool Wear Failure (TWF)",
            failure_mode="Flank Wear & Vibration Fatigue",
            total_steps=total_steps,
            step_interval_seconds=step_interval_seconds,
            machine_id=machine_id,
            ambient_temp=24.0,
        )

    def generate(self) -> list[ScenarioStep]:
        steps = []
        base_temp = 68.0
        base_rpm = 1800.0
        base_pressure = 22.0
        base_vib = 0.22
        start_hours = 1500.0

        for i in range(self.total_steps):
            elapsed = i * self.step_interval_seconds
            t_now = datetime.now(timezone.utc).isoformat()

            progress = i / self.total_steps
            if progress < 0.5:
                curr_hours = start_hours + i * 20.0
                curr_vib = base_vib + 0.04 * progress
                curr_rpm = base_rpm
                curr_p = base_pressure
                curr_temp = base_temp
                is_fail = False
                driver = None
                notes = "Nominal wear progression"
            else:
                wear_factor = (progress - 0.5) / 0.5
                curr_hours = 4400.0 + 600.0 * wear_factor
                curr_vib = 0.40 + 0.28 * wear_factor
                curr_rpm = base_rpm + 400.0 * wear_factor
                curr_p = base_pressure + 3.0 * wear_factor
                curr_temp = base_temp + 4.0 * wear_factor
                is_fail = True
                driver = "operating_hours" if curr_hours >= 4800.0 else "vibration"
                notes = f"Accelerated wear: vib={curr_vib:.3f}g, hours={curr_hours:.0f}h"

            crest_factor = 2.1 + 2.0 * progress

            telemetry = {
                "temperature": round(curr_temp, 1),
                "rpm": round(curr_rpm, 1),
                "pressure": round(curr_p, 2),
                "vibration": round(curr_vib, 3),
                "operating_hours": round(curr_hours, 1),
                "vibration_crest_factor": round(crest_factor, 2),
                "context": {
                    "machine_id": self.machine_id,
                    "machine_type": "High-Torque-Horizontal-Mill",
                    "regime": "steady_state_heavy" if is_fail else "steady_state_light",
                    "ambient_temperature": self.ambient_temp,
                    "hours_since_last_service": round(curr_hours - 1000.0, 1),
                    "recent_fault_count_24h": 1 if is_fail else 0,
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
