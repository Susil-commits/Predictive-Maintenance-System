"""
Chaos Experiment: Database Outage Resilience.
Verifies that database connection disruptions do not take down the prediction gateway.
"""

from typing import Any
from unittest.mock import patch

from starlette.testclient import TestClient

from backend.main import app

client = TestClient(app)

SAMPLE_TELEMETRY = {
    "temperature": 75.0,
    "rpm": 2200.0,
    "pressure": 24.0,
    "vibration": 0.25,
    "operating_hours": 1500.0,
}


def run_database_resilience_experiment() -> dict[str, Any]:
    """
    Simulates database server failure during inference persistence:
    1. Baseline: Standard prediction persists to DB.
    2. Chaos: Database commit throws OperationalError (simulating DB crash / connection severed).
    3. Assert: API catches DB error, logs warning, and still returns 200 OK with valid prediction.
    4. Recovery: Database restored, subsequent predictions succeed.
    """
    # Phase 1: Baseline Request
    res1 = client.post("/predict", json=SAMPLE_TELEMETRY)
    p1_pass = res1.status_code == 200

    # Phase 2 & 3: Inject DB Severing Fault
    with patch("backend.main.Session.commit", side_effect=Exception("CHAOS: PostgreSQL connection severed")):
        res2 = client.post("/predict", json=SAMPLE_TELEMETRY)
        # Even when DB fails, prediction inference must not crash with 500
        p2_pass = res2.status_code == 200
        data2 = res2.json()
        prediction_intact = "probability" in data2 and "failure_risk" in data2

    # Phase 4: Recovery Check
    res3 = client.post("/predict", json=SAMPLE_TELEMETRY)
    p3_pass = res3.status_code == 200

    all_pass = p1_pass and p2_pass and prediction_intact and p3_pass

    return {
        "experiment": "Database Outage Telemetry Resilience",
        "pass": all_pass,
        "phase_1_baseline_status": res1.status_code,
        "phase_2_chaos_resilience_status": res2.status_code,
        "inference_preserved_under_db_loss": prediction_intact,
        "phase_4_post_recovery_status": res3.status_code,
    }
