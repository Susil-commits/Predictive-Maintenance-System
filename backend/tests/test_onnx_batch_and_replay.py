"""
Tests for Vectorized ONNX Batch Scoring and Live Plant Telemetry Replay.
"""

import io
import os

from fastapi.testclient import TestClient

from backend.inference_engine import InferenceRuntime, inference_engine
from backend.main import app

client = TestClient(app)
ADMIN_API_KEY = (os.getenv("PMS_API_KEY") or "").strip()


def test_batch_predict_vectorized_onnx_parity_and_row_errors():
    """Verifies /batch-predict?runtime=onnx scores valid rows vectorized and isolates bad rows."""
    csv_content = (
        "temperature,rpm,pressure,vibration,operating_hours\n"
        "68.0,1500,21.0,0.22,950\n"
        "92.4,2800,31.5,0.64,4820\n"
        "999.0,2800,31.5,0.64,4820\n"
    )
    res = client.post(
        "/batch-predict?runtime=onnx",
        headers={"X-API-Key": ADMIN_API_KEY},
        files={"file": ("telemetry.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["runtime"] == "onnx"
    assert isinstance(data["elapsed_ms"], float)
    assert data["total_rows"] == 3
    assert data["processed_rows"] == 2
    assert data["error_rows"] == 1

    r0, r1, r2 = data["results"]
    assert r0["prediction"] == "LOW"
    assert r1["prediction"] == "HIGH"
    assert "error" in r2 and r2["row_index"] == 2

    # Parity against single-item ONNX inference
    single_high = inference_engine.predict(
        {"temperature": 92.4, "rpm": 2800.0, "pressure": 31.5, "vibration": 0.64, "operating_hours": 4820.0},
        runtime=InferenceRuntime.ONNX,
    )
    assert abs(r1["probability"] - single_high["probability"]) < 1e-3


def test_simulate_fleet_telemetry_stream_and_websocket_broadcast():
    """Verifies POST /fleet/simulate-stream auth, validation, persistence, and WS broadcast."""
    unauth = client.post("/fleet/simulate-stream")
    assert unauth.status_code == 401

    bad_sc = client.post(
        "/fleet/simulate-stream?scenario=unknown_mode",
        headers={"X-API-Key": ADMIN_API_KEY},
    )
    assert bad_sc.status_code == 400

    with client.websocket_connect("/ws/telemetry") as ws:
        hello = ws.receive_json()
        assert hello["type"] == "connected"

        sim_res = client.post(
            "/fleet/simulate-stream?scenario=all&steps=2&runtime=onnx",
            headers={"X-API-Key": ADMIN_API_KEY},
        )
        assert sim_res.status_code == 200
        summary = sim_res.json()
        assert summary["status"] == "completed"
        assert summary["runtime"] == "onnx"
        assert summary["events_emitted"] == 6
        assert len(summary["assets"]) == 3

        # Verify live WS frames arrived for the replayed assets
        received_assets = set()
        for _ in range(6):
            msg = ws.receive_json()
            assert msg["type"] == "prediction"
            received_assets.add(msg["asset_id"])
        assert len(received_assets) == 3

    fleet = client.get("/fleet/summary").json()
    fleet_ids = {a["asset_id"] for a in fleet["assets"]}
    for aid in summary["assets"]:
        assert aid in fleet_ids
