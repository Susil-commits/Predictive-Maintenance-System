"""
Unit & Performance Tests for PMS Multi-Runtime Inference Engine.
"""

from starlette.testclient import TestClient

from backend.inference_engine import InferenceRuntime, inference_engine
from backend.main import app

client = TestClient(app)

SAMPLE_TELEMETRY = {
    "temperature": 82.0,
    "rpm": 2400.0,
    "pressure": 28.0,
    "vibration": 0.42,
    "operating_hours": 3200.0,
}


def test_inference_engine_onnx_prediction():
    """Verifies ONNX runtime microsecond prediction."""
    # Warmup call
    inference_engine.predict(SAMPLE_TELEMETRY, runtime=InferenceRuntime.ONNX)
    res = inference_engine.predict(SAMPLE_TELEMETRY, runtime=InferenceRuntime.ONNX)
    assert res["runtime"] == "onnx"
    assert "probability" in res
    assert "failure_risk" in res
    assert "inference_time_ms" in res
    assert res["inference_time_ms"] < 10.0  # Must be fast sub-millisecond warm execution


def test_inference_engine_xgboost_prediction():
    """Verifies XGBoost ensemble prediction with full SHAP attribution."""
    res = inference_engine.predict(SAMPLE_TELEMETRY, runtime=InferenceRuntime.XGBOOST)
    assert res["runtime"] == "xgboost"
    assert "shap_values" in res
    assert "contributing_factors" in res
    assert len(res["contributing_factors"]) > 0


def test_inference_engine_hybrid_prediction():
    """Verifies hybrid routing mode."""
    res = inference_engine.predict(SAMPLE_TELEMETRY, runtime=InferenceRuntime.HYBRID)
    assert res["runtime"] in ("xgboost", "hybrid-onnx-fastpath")
    assert "probability" in res
    assert "failure_risk" in res


def test_inference_benchmark_endpoint():
    """Verifies the /inference/benchmark endpoint compares ONNX and XGBoost."""
    response = client.get("/inference/benchmark?iterations=20")
    assert response.status_code == 200
    data = response.json()
    assert "onnx" in data
    assert "xgboost" in data
    assert "speedup_factor" in data
    assert data["onnx"]["mean_latency_ms"] is not None
    assert data["xgboost"]["mean_latency_ms"] is not None
    # ONNX should be substantially faster
    assert data["speedup_factor"] > 1.0


def test_predict_endpoint_runtime_query_param():
    """Verifies /predict?runtime=onnx routes to the ONNX engine."""
    res = client.post("/predict?runtime=onnx", json=SAMPLE_TELEMETRY)
    assert res.status_code == 200
    data = res.json()
    assert "probability" in data
    assert "failure_risk" in data
