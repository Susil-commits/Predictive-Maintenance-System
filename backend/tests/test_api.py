import os
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

def test_prediction_tuned_decision_threshold():
    # Verify model-info contains tuned decision_threshold
    info_res = client.get("/model-info")
    assert info_res.status_code == 200
    info_data = info_res.json()
    assert "decision_threshold" in info_data
    threshold = info_data["decision_threshold"]
    assert threshold is not None
    assert 0.1 <= threshold <= 0.99

    # Verify predict output exposes the tuned decision threshold and applies it correctly
    payload = {
        "temperature": 92.4,
        "rpm": 2800,
        "pressure": 31.5,
        "vibration": 0.64,
        "operating_hours": 4820
    }
    pred_res = client.post("/predict", json=payload)
    assert pred_res.status_code == 200
    pred_data = pred_res.json()
    assert "decision_threshold" in pred_data
    assert pred_data["decision_threshold"] == threshold
    expected_risk = "HIGH" if pred_data["probability"] >= threshold else "LOW"
    assert pred_data["failure_risk"] == expected_risk
    assert pred_data["maintenance_required"] == (pred_data["probability"] >= threshold)

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

def test_delete_history():
    # Calling without API key should be rejected with 401 Unauthorized
    unauth_response = client.delete("/history")
    assert unauth_response.status_code == 401
    assert "Invalid or missing API key" in unauth_response.json()["detail"]

    # Calling with valid admin API key succeeds
    response = client.delete("/history", headers={"X-API-Key": "pms-admin-secret-key"})
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "Successfully deleted" in data["message"]

    # Verify history is now empty
    hist_response = client.get("/history")
    assert hist_response.status_code == 200
    assert len(hist_response.json()) == 0

def test_predict_invalid_input():
    # Sending invalid data (e.g. string instead of float or missing fields)
    response = client.post("/predict", json={"temperature": "invalid_string"})
    assert response.status_code == 422

def test_cors_preflight_headers():
    response = client.options(
        "/predict",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "*"
    # Verify allow-credentials is not set to true when wildcard origin is returned
    assert response.headers.get("access-control-allow-credentials") != "true"

def test_retrain_endpoint(monkeypatch):
    mock_called = []
    monkeypatch.setattr("backend.main.execute_retraining", lambda: mock_called.append(True))
    
    # Missing API key should return 401
    unauth_res = client.post("/retrain")
    assert unauth_res.status_code == 401
    assert "Invalid or missing API key" in unauth_res.json()["detail"]
    assert len(mock_called) == 0

    # With valid API key should return 200
    response = client.post("/retrain", headers={"X-API-Key": "pms-admin-secret-key"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "retraining_initiated"
    assert "current_version" in data
    assert len(mock_called) == 1

def test_rate_limiter_allows_requests():
    # Verify rate limiter correctly handles request object on /predict
    payload = {
        "temperature": 70.0,
        "rpm": 1800,
        "pressure": 20.0,
        "vibration": 0.20,
        "operating_hours": 1000
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 200

def test_auth_login_seeded_admin_and_jwt():
    # Login with seeded admin account
    admin_user = os.getenv("ADMIN_USERNAME", "admin")
    admin_pass = os.getenv("ADMIN_PASSWORD", "PmsAdmin#Secure2026!")
    res = client.post("/auth/login", json={
        "username": admin_user,
        "password": admin_pass
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["role"] == "admin"

    token = data["access_token"]

    # Use JWT to access admin-only users list
    users_res = client.get("/auth/users", headers={"Authorization": f"Bearer {token}"})
    assert users_res.status_code == 200
    assert isinstance(users_res.json(), list)

def test_auth_login_invalid_credentials():
    # Unknown user
    res_unknown = client.post("/auth/login", json={
        "username": "non_existent_user_999",
        "password": "some_password"
    })
    assert res_unknown.status_code == 401
    assert "User not registered" in res_unknown.json()["detail"]

    # Wrong password for existing admin
    res_wrong = client.post("/auth/login", json={
        "username": "admin",
        "password": "wrong_password_xyz"
    })
    assert res_wrong.status_code == 401
    assert "Incorrect password" in res_wrong.json()["detail"]

def test_batch_predict_requires_auth():
    sample_csv = b"temperature,rpm,pressure,vibration,operating_hours\n85.0,1800,24.0,0.35,2100\n"
    # Unauthenticated request returns 401
    unauth = client.post(
        "/batch-predict",
        files={"file": ("test.csv", sample_csv, "text/csv")}
    )
    assert unauth.status_code == 401

    # Authenticated with X-API-Key succeeds
    auth_res = client.post(
        "/batch-predict",
        files={"file": ("test.csv", sample_csv, "text/csv")},
        headers={"X-API-Key": "pms-admin-secret-key"}
    )
    assert auth_res.status_code == 200
    data = auth_res.json()
    assert data["total_rows"] == 1
    assert data["processed_rows"] == 1

def test_batch_predict_size_limit_5mb():
    # File larger than 5MB
    large_bytes = b"0" * (5 * 1024 * 1024 + 1)
    res = client.post(
        "/batch-predict",
        files={"file": ("huge.csv", large_bytes, "text/csv")},
        headers={"X-API-Key": "pms-admin-secret-key"}
    )
    assert res.status_code == 413
    assert "File too large, max 5MB" in res.json()["detail"]

def test_batch_predict_row_limit_5000():
    # Create CSV with 5001 rows
    header = "temperature,rpm,pressure,vibration,operating_hours\n"
    row = "80.0,1500,22.0,0.25,1200\n"
    csv_content = (header + row * 5001).encode("utf-8")

    res = client.post(
        "/batch-predict",
        files={"file": ("many_rows.csv", csv_content, "text/csv")},
        headers={"X-API-Key": "pms-admin-secret-key"}
    )
    assert res.status_code == 422
    assert "Too many rows, max 5000 per batch" in res.json()["detail"]

def test_export_history_requires_auth():
    # Calling /export without auth returns 401
    unauth = client.get("/export")
    assert unauth.status_code == 401

    # Calling with valid admin API key succeeds (or 404 if history empty)
    res = client.get("/export", headers={"X-API-Key": "pms-admin-secret-key"})
    assert res.status_code in [200, 404]

def test_retrain_mutex_lock_collision():
    import backend.main
    # Simulate retraining already active
    backend.main._retraining_active = True
    try:
        response = client.post("/retrain", headers={"X-API-Key": "pms-admin-secret-key"})
        assert response.status_code == 409
        assert "already in progress" in response.json()["detail"]
    finally:
        backend.main._retraining_active = False


