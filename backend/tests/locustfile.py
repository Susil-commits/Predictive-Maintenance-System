"""
Locust load test scenario for Predictive Maintenance System (PMS).
Simulates industrial telemetry ingestion at concurrency levels of 10, 50, and 100 concurrent users.
Hits POST /predict with diverse operational telemetry profiles.
"""

import random
from locust import HttpUser, task, between

# Sample telemetry profiles matching diverse operating equipment
TELEMETRY_PROFILES = [
    # Nominal healthy asset
    {
        "temperature": 68.0,
        "rpm": 1500,
        "pressure": 21.0,
        "vibration": 0.22,
        "operating_hours": 950
    },
    # Moderate fatigue / wear
    {
        "temperature": 78.5,
        "rpm": 2100,
        "pressure": 26.0,
        "vibration": 0.42,
        "operating_hours": 3200
    },
    # High thermal stress
    {
        "temperature": 94.2,
        "rpm": 2400,
        "pressure": 28.5,
        "vibration": 0.45,
        "operating_hours": 3800
    },
    # Severe mechanical vibration & overstrain
    {
        "temperature": 89.0,
        "rpm": 2900,
        "pressure": 37.0,
        "vibration": 0.72,
        "operating_hours": 5100
    },
    # Extreme imminent breakdown
    {
        "temperature": 102.5,
        "rpm": 3200,
        "pressure": 41.0,
        "vibration": 0.92,
        "operating_hours": 5900
    }
]

class EquipmentTelemetryUser(HttpUser):
    """Simulates factory IoT gateway streaming edge telemetry to /predict."""
    wait_time = between(0.01, 0.05)  # Fast turnaround for stress testing

    @task(10)
    def predict_telemetry(self):
        """Dispatches realistic telemetry payload to /predict endpoint."""
        base_payload = random.choice(TELEMETRY_PROFILES)
        
        # Inject realistic jitter (+/- 2%)
        payload = {
            "temperature": round(base_payload["temperature"] + random.uniform(-1.0, 1.0), 1),
            "rpm": int(base_payload["rpm"] + random.randint(-40, 40)),
            "pressure": round(base_payload["pressure"] + random.uniform(-0.5, 0.5), 1),
            "vibration": round(max(0.05, base_payload["vibration"] + random.uniform(-0.02, 0.02)), 2),
            "operating_hours": int(base_payload["operating_hours"] + random.randint(0, 10))
        }

        headers = {
            "Content-Type": "application/json",
            "X-Load-Test": "bypass"
        }
        
        with self.client.post("/predict", json=payload, headers=headers, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if "failure_risk" in data and "probability" in data:
                    response.success()
                else:
                    response.failure("Malformed prediction response payload")
            elif response.status_code == 429:
                response.failure("Rate limit throttled (429)")
            else:
                response.failure(f"HTTP error status: {response.status_code}")

    @task(1)
    def check_health(self):
        """Un-throttled health check verification."""
        self.client.get("/health")
