"""
Tests for Closed-Loop Active Learning & Production Precision Telemetry.
"""

import os
import uuid

import pandas as pd
from fastapi.testclient import TestClient

from backend.active_learning import DEFAULT_FEEDBACK_CSV, export_feedback_dataset
from backend.database import SessionLocal
from backend.main import app

client = TestClient(app)
ADMIN_API_KEY = (os.getenv("PMS_API_KEY") or "").strip()


def test_active_learning_feedback_metrics_and_export():
    """
    Verifies full closed-loop lifecycle:
    Prediction -> Work Order Dispatch -> Technician Resolution -> Precision Metrics & CSV Export.
    """
    asset_id = f"CNC-AL-{uuid.uuid4().hex[:6].upper()}"

    # 1. Create two HIGH risk predictions
    pred_tp = client.post(
        "/predict?runtime=xgboost",
        json={
            "temperature": 94.0,
            "rpm": 2850,
            "pressure": 32.5,
            "vibration": 0.68,
            "operating_hours": 4850,
            "context": {"machine_id": asset_id, "regime": "steady_state_heavy"},
        },
    )
    assert pred_tp.status_code == 200
    pid_tp = pred_tp.json()["prediction_id"]

    pred_fp = client.post(
        "/predict?runtime=xgboost",
        json={
            "temperature": 91.5,
            "rpm": 2700,
            "pressure": 31.0,
            "vibration": 0.62,
            "operating_hours": 4600,
            "context": {"machine_id": asset_id, "regime": "steady_state_heavy"},
        },
    )
    assert pred_fp.status_code == 200
    pid_fp = pred_fp.json()["prediction_id"]

    # 2. Dispatch work orders linked to those predictions
    wo_tp = client.post(
        "/maintenance/dispatch-work-order",
        json={
            "prediction_id": pid_tp,
            "asset_id": asset_id,
            "failure_mode": "Thermal Runaway",
            "priority": "CRITICAL",
        },
    ).json()

    wo_fp = client.post(
        "/maintenance/dispatch-work-order",
        json={
            "prediction_id": pid_fp,
            "asset_id": asset_id,
            "failure_mode": "Vibration / Bearing Wear",
            "priority": "HIGH",
        },
    ).json()

    # 3. Resolve one as confirmed fault (TP) and one as false alarm (FP)
    assert (
        client.patch(
            f"/maintenance/work-orders/{wo_tp['work_order_id']}",
            json={"status": "RESOLVED", "actual_failure_confirmed": True},
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f"/maintenance/work-orders/{wo_fp['work_order_id']}",
            json={"status": "RESOLVED", "actual_failure_confirmed": False},
        ).status_code
        == 200
    )

    # 4. Check live production precision & confusion counts
    metrics_res = client.get("/mlops/feedback-metrics")
    assert metrics_res.status_code == 200
    m = metrics_res.json()
    assert m["resolved_with_feedback"] >= 2
    assert m["confirmed_faults"] >= 1
    assert m["false_alarms"] >= 1
    assert m["production_precision"] is not None
    assert 0.0 <= m["production_precision"] <= 1.0
    assert m["confusion_matrix"]["true_positives"] >= 1
    assert m["confusion_matrix"]["false_positives"] >= 1

    # 5. Export endpoint enforces admin auth and writes clean active-learning CSV
    unauth = client.post("/mlops/export-feedback")
    assert unauth.status_code in (401, 403)

    existed_before = os.path.exists(DEFAULT_FEEDBACK_CSV)
    try:
        auth_export = client.post("/mlops/export-feedback", headers={"X-API-Key": ADMIN_API_KEY})
        assert auth_export.status_code == 200
        exp_data = auth_export.json()
        assert exp_data["exported_samples"] >= 2
        assert os.path.exists(DEFAULT_FEEDBACK_CSV)

        df = pd.read_csv(DEFAULT_FEEDBACK_CSV)
        for col in [
            "temperature",
            "rpm",
            "pressure",
            "vibration",
            "operating_hours",
            "failure",
            "failure_type",
            "source_weight",
        ]:
            assert col in df.columns
        assert set(df["failure"].unique()).issubset({0, 1})
    finally:
        if not existed_before and os.path.exists(DEFAULT_FEEDBACK_CSV):
            os.remove(DEFAULT_FEEDBACK_CSV)


def test_export_feedback_dataset_helper_isolated(tmp_path):
    """Verifies export_feedback_dataset writes valid CSV to custom path."""
    out_csv = str(tmp_path / "fb_out.csv")
    with SessionLocal() as db:
        summary = export_feedback_dataset(db, output_path=out_csv)
    assert os.path.exists(out_csv)
    assert summary["output_path"] == out_csv
