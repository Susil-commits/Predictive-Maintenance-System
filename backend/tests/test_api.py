import os
import uuid
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)
ADMIN_API_KEY = (os.getenv("PMS_API_KEY") or "pms-admin-secret-key").strip()

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
    assert data["metrics"]["roc_auc"] > 0.80

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
    threshold = data.get("decision_threshold", 0.20)
    assert data["probability"] >= threshold
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
    response = client.delete("/history", headers={"X-API-Key": ADMIN_API_KEY})
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
    response = client.post("/retrain", headers={"X-API-Key": ADMIN_API_KEY})
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
    admin_user = os.getenv("ADMIN_USERNAME") or "admin"
    admin_pass = os.getenv("ADMIN_PASSWORD") or "PmsAdmin#Secure2026!"
    res = client.post("/auth/login", json={
        "username": admin_user,
        "password": admin_pass
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["role"] == "admin"
    assert data["user"]["designation"] == "System Administrator"

    token = data["access_token"]

    # Use JWT to access admin-only users list
    users_res = client.get("/auth/users", headers={"Authorization": f"Bearer {token}"})
    assert users_res.status_code == 200
    assert isinstance(users_res.json(), list)

def test_auth_create_user_with_designation():
    admin_user = os.getenv("ADMIN_USERNAME") or "admin"
    admin_pass = os.getenv("ADMIN_PASSWORD") or "PmsAdmin#Secure2026!"
    login_res = client.post("/auth/login", json={"username": admin_user, "password": admin_pass})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    # Create new assessor employee with custom designation
    test_assessor = f"assessor_test_{uuid.uuid4().hex[:6]}"
    test_desig = "Senior Reliability Assessor"
    create_res = client.post(
        "/auth/users",
        json={"username": test_assessor, "password": "AssessorPass#123", "designation": test_desig},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert create_res.status_code == 201
    created_data = create_res.json()
    assert created_data["username"] == test_assessor
    assert created_data["designation"] == test_desig
    user_id = created_data["id"]

    # Login as the new assessor and verify designation in JWT payload and user dict
    emp_login = client.post("/auth/login", json={"username": test_assessor, "password": "AssessorPass#123"})
    assert emp_login.status_code == 200
    emp_data = emp_login.json()
    assert emp_data["user"]["designation"] == test_desig

    # Cleanup test user
    del_res = client.delete(f"/auth/users/{user_id}", headers={"Authorization": f"Bearer {token}"})
    assert del_res.status_code == 200

def test_auth_login_invalid_credentials():
    # Unknown user
    res_unknown = client.post("/auth/login", json={
        "username": "non_existent_user_999",
        "password": "some_password"
    })
    assert res_unknown.status_code == 401
    assert "User not registered" in res_unknown.json()["detail"]

    # Wrong password for existing admin
    admin_user = (os.getenv("ADMIN_USERNAME") or "admin").strip()
    res_wrong = client.post("/auth/login", json={
        "username": admin_user,
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
        headers={"X-API-Key": ADMIN_API_KEY}
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
        headers={"X-API-Key": ADMIN_API_KEY}
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
        headers={"X-API-Key": ADMIN_API_KEY}
    )
    assert res.status_code == 422
    assert "Too many rows, max 5000 per batch" in res.json()["detail"]

def test_export_history_requires_auth():
    # Calling /export without auth returns 401
    unauth = client.get("/export")
    assert unauth.status_code == 401

    # Calling with valid admin API key succeeds (or 404 if history empty)
    res = client.get("/export", headers={"X-API-Key": ADMIN_API_KEY})
    assert res.status_code in [200, 404]

def test_retrain_mutex_lock_collision():
    import backend.main
    # Simulate retraining already active
    backend.main._retraining_active = True
    try:
        response = client.post("/retrain", headers={"X-API-Key": ADMIN_API_KEY})
        assert response.status_code == 409
        assert "already in progress" in response.json()["detail"]
    finally:
        backend.main._retraining_active = False


def test_prediction_input_boundaries_validation():
    # Negative impossible temperature (-500°C) must be rejected with 422
    res_neg_temp = client.post("/predict", json={
        "temperature": -500.0,
        "rpm": 2000.0,
        "pressure": 30.0,
        "vibration": 0.5,
        "operating_hours": 1000.0
    })
    assert res_neg_temp.status_code == 422

    # Impossible RPM (e.g. 50 RPM or 10000 RPM)
    res_low_rpm = client.post("/predict", json={
        "temperature": 75.0,
        "rpm": 20.0,
        "pressure": 30.0,
        "vibration": 0.5,
        "operating_hours": 1000.0
    })
    assert res_low_rpm.status_code == 422

    # Negative operating hours
    res_neg_hours = client.post("/predict", json={
        "temperature": 75.0,
        "rpm": 2000.0,
        "pressure": 30.0,
        "vibration": 0.5,
        "operating_hours": -50.0
    })
    assert res_neg_hours.status_code == 422

    # Upper bound breach (e.g. 100,000 operating hours)
    res_high_hours = client.post("/predict", json={
        "temperature": 75.0,
        "rpm": 2000.0,
        "pressure": 30.0,
        "vibration": 0.5,
        "operating_hours": 99999.0
    })
    assert res_high_hours.status_code == 422


def test_batch_predict_column_matching_failure_detailed_message():
    # CSV with missing columns (only temperature and rpm provided)
    partial_csv = b"temperature,rpm\n85.0,1800\n"
    res = client.post(
        "/batch-predict",
        files={"file": ("partial.csv", partial_csv, "text/csv")},
        headers={"X-API-Key": ADMIN_API_KEY}
    )
    assert res.status_code == 422
    err_detail = res.json()["detail"]
    assert "Missing" in err_detail
    assert "pressure" in err_detail
    assert "vibration" in err_detail
    assert "operating_hours" in err_detail
    assert "Found columns in file" in err_detail
    assert "Expected acceptable column names" in err_detail


def test_export_date_range_filters_and_validation():
    # Invalid date format returns 422
    res_bad_format = client.get(
        "/export?start_date=not-a-date",
        headers={"X-API-Key": ADMIN_API_KEY}
    )
    assert res_bad_format.status_code == 422
    assert "Invalid start_date format" in res_bad_format.json()["detail"]

    # start_date > end_date returns 422
    res_bad_range = client.get(
        "/export?start_date=2026-12-31&end_date=2026-01-01",
        headers={"X-API-Key": ADMIN_API_KEY}
    )
    assert res_bad_range.status_code == 422
    assert "start_date cannot be greater than end_date" in res_bad_range.json()["detail"]

    # Valid range returns 200 or 404 (if no records match range)
    res_valid = client.get(
        "/export?start_date=2020-01-01&end_date=2030-12-31",
        headers={"X-API-Key": ADMIN_API_KEY}
    )
    assert res_valid.status_code in [200, 404]


def test_history_pruning_endpoint():
    # Unauthenticated returns 401
    res_unauth = client.post("/history/prune?days=30")
    assert res_unauth.status_code == 401

    # Authenticated call succeeds
    res_auth = client.post("/history/prune?days=30", headers={"X-API-Key": ADMIN_API_KEY})
    assert res_auth.status_code == 200
    data = res_auth.json()
    assert data["status"] == "success"
    assert "pruned_count" in data
    assert data["retention_days"] == 30


def test_predict_rul_endpoint():
    history = [
        {"temperature": 75.0 + i * 0.5, "rpm": 2200, "pressure": 24.0 + i * 0.2, "vibration": 0.25 + i * 0.01}
        for i in range(25)
    ]
    res = client.post("/predict-rul", json=history)
    assert res.status_code == 200
    data = res.json()
    assert "estimated_rul_cycles" in data
    assert "estimated_rul_hours" in data
    assert "confidence" in data
    assert "recommendation" in data
    assert data["estimated_rul_cycles"] > 0
    assert data["confidence"] > 0.0


def test_predict_with_uncertainty():
    from backend.predictor import predictor
    features = {"temperature": 72.0, "rpm": 1800, "pressure": 22.0, "vibration": 0.25, "operating_hours": 1200}
    res = predictor.predict_with_uncertainty(features)
    assert "probability" in res
    assert "confidence" in res
    assert res["confidence"] in ["HIGH", "LOW"]
    assert "recommendation" in res


def test_validate_startup_env_success():
    from backend.main import validate_startup_env
    # Current environment has all required vars set in .env / CI
    validate_startup_env()


def test_validate_startup_env_missing_single_var(monkeypatch):
    from backend.main import validate_startup_env
    monkeypatch.delenv("PMS_API_KEY", raising=False)
    with pytest.raises(RuntimeError) as exc_info:
        validate_startup_env()
    assert "PMS_API_KEY" in str(exc_info.value)
    assert "Missing required environment variables" in str(exc_info.value)


def test_validate_startup_env_missing_multiple_vars(monkeypatch):
    from backend.main import validate_startup_env
    monkeypatch.setenv("DATABASE_URL", "   ")
    monkeypatch.delenv("JWT_SECRET", raising=False)
    with pytest.raises(RuntimeError) as exc_info:
        validate_startup_env()
    err = str(exc_info.value)
    assert "DATABASE_URL" in err
    assert "JWT_SECRET" in err
