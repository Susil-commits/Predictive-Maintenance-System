import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["model_loaded"] is True

def test_model_info_endpoint():
    response = client.get("/model-info")
    assert response.status_code == 200
    data = response.json()
    assert "model_name" in data
    assert "metrics" in data
    assert "roc_auc" in data["metrics"]
    assert data["metrics"]["roc_auc"] > 0.90

def test_predict_high_risk():
    payload = {
        "temperature": 92.4,
        "rpm": 2800,
        "pressure": 31.5,
        "vibration": 0.64,
        "operating_hours": 4820
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["failure_risk"] == "HIGH"
    assert data["probability"] >= 0.50
    assert data["maintenance_required"] is True
    assert "contributing_factors" in data
    assert len(data["contributing_factors"]) > 0
    # Factors should include Vibration, Temperature, Pressure in top contributing list
    factor_names = [f["factor"] for f in data["contributing_factors"]]
    assert "Vibration" in factor_names
    assert "Temperature" in factor_names
    assert "Pressure" in factor_names

def test_predict_low_risk():
    payload = {
        "temperature": 68.0,
        "rpm": 1500,
        "pressure": 21.0,
        "vibration": 0.22,
        "operating_hours": 950
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["failure_risk"] == "LOW"
    assert data["probability"] < 0.50
    assert data["maintenance_required"] is False

def test_prediction_history():
    response = client.get("/history")
    assert response.status_code == 200
    history = response.json()
    assert isinstance(history, list)
    assert len(history) >= 2
    assert "input_features" in history[0]
    assert "failure_risk" in history[0]

def test_model_versioning_and_mlflow_metadata():
    response = client.get("/model-info")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert data["version"].startswith("v") or data["version"] == "1.0.0"
    assert "mlflow_run_id" in data
    assert data["mlflow_run_id"] is not None

def test_prediction_output_includes_version():
    payload = {
        "temperature": 75.0,
        "rpm": 1600,
        "pressure": 22.0,
        "vibration": 0.25,
        "operating_hours": 1200
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "model_version" in data
    assert data["model_version"] is not None

def test_drift_status_endpoint():
    # Generate a few predictions to have samples in DB
    for _ in range(6):
        client.post("/predict", json={
            "temperature": 80.0,
            "rpm": 1550,
            "pressure": 23.0,
            "vibration": 0.28,
            "operating_hours": 1500
        })
    
    response = client.get("/drift-status?window=50")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "drift_detected" in data
    assert "retrain_recommended" in data
    assert "feature_metrics" in data
    assert len(data["feature_metrics"]) == 5

def test_drift_reset_endpoint():
    response = client.post("/drift-status/reset")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "reset_successful"

def test_prometheus_drift_metrics():
    response = client.get("/metrics")
    assert response.status_code == 200
    content = response.text
    assert "pms_drift_detected" in content
    assert "pms_drift_max_psi" in content

def test_retrain_endpoint():
    response = client.post("/retrain")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "retraining_initiated"
    assert "current_version" in data
