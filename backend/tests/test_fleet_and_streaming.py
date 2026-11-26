"""
Tests for Multi-Asset Fleet Tracking, Per-Asset Historical RUL, and Live WebSocket Streaming.
"""

import uuid

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_per_asset_history_fleet_summary_and_real_rul():
    """Verifies per-asset persistence, /history?asset_id, /fleet/summary, and /fleet/{asset_id}/rul."""
    asset_a = f"CNC-ASSET-{uuid.uuid4().hex[:6].upper()}"
    asset_b = f"HYD-ASSET-{uuid.uuid4().hex[:6].upper()}"

    # Single reading -> insufficient for real RUL trajectory
    res_a1 = client.post(
        "/predict?runtime=xgboost",
        json={
            "temperature": 72.0,
            "rpm": 1600,
            "pressure": 22.0,
            "vibration": 0.25,
            "operating_hours": 1100,
            "context": {
                "machine_id": asset_a,
                "machine_type": "Precision-CNC",
                "regime": "steady_state_light",
                "ambient_temperature": 24.0,
            },
        },
    )
    assert res_a1.status_code == 200
    assert res_a1.json()["asset_id"] == asset_a

    rul_single = client.get(f"/fleet/{asset_a}/rul")
    assert rul_single.status_code == 200
    assert rul_single.json()["has_history"] is False
    assert rul_single.json()["history_points_used"] == 1

    # Second reading for asset_a -> enables DB-grounded RUL forecast
    res_a2 = client.post(
        "/predict?runtime=onnx",
        json={
            "temperature": 76.5,
            "rpm": 1850,
            "pressure": 24.5,
            "vibration": 0.31,
            "operating_hours": 1105,
            "context": {
                "machine_id": asset_a,
                "machine_type": "Precision-CNC",
                "regime": "steady_state_heavy",
                "ambient_temperature": 24.0,
            },
        },
    )
    assert res_a2.status_code == 200
    assert res_a2.json()["runtime"] == "onnx"

    # High-risk reading for asset_b
    res_b1 = client.post(
        "/predict?runtime=xgboost",
        json={
            "temperature": 95.0,
            "rpm": 2900,
            "pressure": 34.0,
            "vibration": 0.72,
            "operating_hours": 4900,
            "context": {
                "machine_id": asset_b,
                "machine_type": "Hydraulic-Press",
                "regime": "steady_state_heavy",
                "ambient_temperature": 27.0,
            },
        },
    )
    assert res_b1.status_code == 200
    assert res_b1.json()["failure_risk"] == "HIGH"

    # Filtered history check
    hist_a = client.get(f"/history?asset_id={asset_a}")
    assert hist_a.status_code == 200
    rows_a = hist_a.json()
    assert len(rows_a) == 2
    assert all(r["asset_id"] == asset_a for r in rows_a)
    assert {r["runtime"] for r in rows_a} == {"xgboost", "onnx"}

    # Fleet summary check
    fleet_res = client.get("/fleet/summary")
    assert fleet_res.status_code == 200
    fleet = fleet_res.json()
    assert fleet["total_assets"] >= 2
    by_id = {a["asset_id"]: a for a in fleet["assets"]}
    assert asset_a in by_id
    assert asset_b in by_id
    assert by_id[asset_a]["total_evaluations"] == 2
    assert by_id[asset_b]["latest_failure_risk"] == "HIGH"

    # Real historical RUL check for asset_a
    rul_multi = client.get(f"/fleet/{asset_a}/rul")
    assert rul_multi.status_code == 200
    rul_payload = rul_multi.json()
    assert rul_payload["has_history"] is True
    assert rul_payload["history_points_used"] == 2
    assert rul_payload["rul"]["estimated_rul_cycles"] >= 1
    assert rul_payload["rul"]["rul_p10_hours"] <= rul_payload["rul"]["estimated_rul_hours"]


def test_websocket_live_telemetry_broadcast():
    """Verifies WS /ws/telemetry pushes prediction events in real time."""
    stream_asset = f"WS-PUMP-{uuid.uuid4().hex[:6].upper()}"
    with client.websocket_connect("/ws/telemetry") as ws:
        hello = ws.receive_json()
        assert hello["type"] == "connected"

        pred_res = client.post(
            "/predict?runtime=xgboost",
            json={
                "temperature": 88.5,
                "rpm": 2500,
                "pressure": 29.0,
                "vibration": 0.55,
                "operating_hours": 3100,
                "context": {
                    "machine_id": stream_asset,
                    "regime": "steady_state_heavy",
                },
            },
        )
        assert pred_res.status_code == 200
        pred_id = pred_res.json()["prediction_id"]

        event = ws.receive_json()
        assert event["type"] == "prediction"
        assert event["prediction_id"] == pred_id
        assert event["asset_id"] == stream_asset
        assert event["runtime"] == "xgboost"
