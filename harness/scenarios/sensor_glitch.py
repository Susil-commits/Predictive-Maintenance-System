"""
Sensor Glitch Scenario: Simulates edge IoT hardware anomalies, sensor brownouts, and noise spikes.
Tests API edge validation, sanitization, and graceful resilience against telemetry faults.
"""

from datetime import datetime, timezone

from .base import BaseScenario, ScenarioStep


class SensorGlitchScenario(BaseScenario):
    """
    Models physical transducer failure modes:
    - Zero-frequency dropouts (temperature suddenly reads 0°C or freezes)
    - High-frequency transducer noise spikes (1-sample vibration pulse to 3.8g)
    - Negative or out-of-range pressure transients
    """

    def __init__(
        self,
        total_steps: int = 20,
        step_interval_seconds: float = 1.0,
        machine_id: str = "EDGE-SENSOR-FAULT-04",
    ):
        super().__init__(
            name="Sensor Glitch & Brownout",
            failure_mode="Transducer Hardware Anomaly",
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

            t = base_temp
            rpm = base_rpm
            p = base_pressure
            v = base_vib
            h = base_hours
            is_fail = False
            driver = None
            notes = "Nominal transducer signal"

            if i == 5:
                # Acute 1-cycle spike
                v = 0.68
                h = 4900.0
                is_fail = True
                driver = "vibration"
                notes = "Transient EMI / piezoelectric transducer surge"
            elif i == 10:
                # Pressure anomaly near sensor limits
                p = 38.0
                h = 4500.0
                v = 0.60
                is_fail = True
                driver = "pressure"
                notes = "Hydraulic pressure sensor transient calibration drift"
            elif i == 15:
                # Temperature surge glitch
                t = 95.0
                h = 4500.0
                v = 0.58
                p = 32.0
                rpm = 2800.0
                is_fail = True
                driver = "temperature"
                notes = "Thermocouple grounding noise transient"

            telemetry = {
                "temperature": t,
                "rpm": rpm,
                "pressure": p,
                "vibration": v,
                "operating_hours": h + (elapsed / 3600.0),
                "context": {
                    "machine_id": self.machine_id,
                    "machine_type": "Variable-Speed-Compressor",
                    "regime": "steady_state_light",
                    "ambient_temperature": self.ambient_temp,
                    "hours_since_last_service": 200.0,
                    "recent_fault_count_24h": 0,
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
