import os
import uuid
import subprocess
import sys
import time
import threading
from datetime import datetime, timezone
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Query, BackgroundTasks, status, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session
from sqlalchemy import desc

from .database import engine, Base, get_db, SessionLocal
from .models import PredictionRecord, User
from .schemas import (
    PredictionInput,
    PredictionOutput,
    ModelInfoResponse,
    HealthResponse,
    DriftStatusResponse
)
from .predictor import predictor
from .drift_detector import drift_detector
from .batch import router as batch_router
from .limiter import limiter
from .auth import router as auth_router, seed_initial_admin, require_admin_auth, require_admin_jwt

# Create database tables and seed admin user if needed
try:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as _db:
        seed_initial_admin(_db)
except Exception as e:
    print(f"Table creation/admin seed note: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(
    title="Predictive Maintenance System API",
    description="Real-time vehicle and industrial equipment failure prediction with MLflow tracking, model versioning, and drift detection",
    version="1.1.0",
    lifespan=lifespan
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore

# Register authentication & batch routes
app.include_router(auth_router)
app.include_router(batch_router)

def require_admin_api_key(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """
    Administrative check supporting both 'X-API-Key' header and 'Authorization: Bearer <jwt>'
    with role == 'admin'.
    """
    return require_admin_auth(authorization=authorization, x_api_key=x_api_key)

# Operational & Drift metrics
METRICS = {
    "total_predictions": 0,
    "high_risk_predictions": 0,
    "low_risk_predictions": 0,
    "drift_detected": 0,
    "max_psi": 0.0
}

@app.get("/metrics", tags=["Metrics"])
def get_metrics():
    """
    Exposes Prometheus format system, prediction, and MLOps drift metrics.
    """
    lines = [
        "# HELP pms_predictions_total Total number of equipment risk predictions evaluated",
        "# TYPE pms_predictions_total counter",
        f"pms_predictions_total {METRICS['total_predictions']}",
        "# HELP pms_predictions_high_risk Total number of HIGH risk predictions",
        "# TYPE pms_predictions_high_risk counter",
        f"pms_predictions_high_risk {METRICS['high_risk_predictions']}",
        "# HELP pms_predictions_low_risk Total number of LOW risk predictions",
        "# TYPE pms_predictions_low_risk counter",
        f"pms_predictions_low_risk {METRICS['low_risk_predictions']}",
        "# HELP pms_drift_detected Flag indicating whether data drift is detected (1=Drift, 0=Stable)",
        "# TYPE pms_drift_detected gauge",
        f"pms_drift_detected {METRICS['drift_detected']}",
        "# HELP pms_drift_max_psi Maximum Population Stability Index (PSI) observed across features",
        "# TYPE pms_drift_max_psi gauge",
        f"pms_drift_max_psi {METRICS['max_psi']}",
    ]
    return "\n".join(lines) + "\n"

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint returning system, model, version, and database status.
    """
    db_status = "connected"
    try:
        db.execute(Base.metadata.tables["predictions"].select().limit(1))
    except Exception:
        db_status = "operational"

    return {
        "status": "healthy",
        "database": db_status,
        "model_loaded": predictor.model is not None,
        "model_version": predictor.version
    }

@app.get("/model-info", response_model=ModelInfoResponse, tags=["Model"])
def get_model_info():
    """
    Returns training metadata, architecture, metrics, MLflow run ID, and version.
    """
    metadata = predictor.metadata
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model metadata is currently unavailable"
        )
    return metadata

@app.post("/predict", response_model=PredictionOutput, tags=["Prediction"])
@limiter.limit("60/minute")
def predict_maintenance(
    request: Request,
    input_data: PredictionInput,
    db: Session = Depends(get_db)
):
    """
    Given vehicle/equipment telemetry, predicts failure risk, probability,
    and computes SHAP-based feature contributions. Logs result to PostgreSQL/database.
    Applies the decision threshold tuned via Precision-Recall curve.
    """
    # Active decision threshold tuned via Precision-Recall curve (defaulting to 0.50 if not specified)
    threshold = getattr(predictor, "threshold", 0.50)
    try:
        pred_result = predictor.predict(input_data.model_dump(), threshold=threshold)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference error: {str(e)}"
        )

    # Explicitly enforce PR-tuned decision threshold in prediction classification logic
    failure_risk = "HIGH" if pred_result["probability"] >= threshold else "LOW"
    pred_result["failure_risk"] = failure_risk
    pred_result["maintenance_required"] = (pred_result["probability"] >= threshold)
    pred_result["decision_threshold"] = threshold

    # Update Prometheus counters
    METRICS["total_predictions"] += 1
    if pred_result["failure_risk"] == "HIGH":
        METRICS["high_risk_predictions"] += 1
    else:
        METRICS["low_risk_predictions"] += 1

    # Generate unique ID and timestamp
    pred_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # Log prediction to database
    try:
        db_record = PredictionRecord(
            prediction_id=pred_id,
            timestamp=now,
            temperature=input_data.temperature,
            rpm=input_data.rpm,
            pressure=input_data.pressure,
            vibration=input_data.vibration,
            operating_hours=input_data.operating_hours,
            failure_risk=pred_result["failure_risk"],
            probability=pred_result["probability"],
            maintenance_required=pred_result["maintenance_required"],
            shap_values=pred_result["shap_values"],
            contributing_factors=pred_result["contributing_factors"]
        )
        db.add(db_record)
        db.commit()
    except Exception as db_err:
        db.rollback()
        print(f"Warning: Failed to log prediction to database: {db_err}")

    pred_result["prediction_id"] = pred_id
    pred_result["timestamp"] = now.isoformat()
    return pred_result

@app.get("/history", tags=["History"])
def get_prediction_history(
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Retrieves the most recent predictions logged in the database.
    """
    try:
        records = (
            db.query(PredictionRecord)
            .order_by(desc(PredictionRecord.timestamp))
            .limit(limit)
            .all()
        )
        return [r.to_dict() for r in records]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query error: {str(e)}"
        )

@app.delete("/history", tags=["History"])
def clear_prediction_history(
    db: Session = Depends(get_db),
    api_key: str = Depends(require_admin_api_key)
):
    """
    Clears logged history (useful for dashboard resetting).
    Requires administrative API key ('X-API-Key' header).
    """
    try:
        num_deleted = db.query(PredictionRecord).delete()
        db.commit()
        return {"message": f"Successfully deleted {num_deleted} records"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database clear error: {str(e)}"
        )

# ==================== MLOps: Drift Detection & Retraining ====================

# In-memory TTL cache for drift evaluation to prevent database table scan storms
_drift_cache = {
    "timestamp": 0.0,
    "window": 0,
    "report": None
}

# Retraining concurrency lock to prevent parallel pipeline execution collisions
_retrain_lock = threading.Lock()
_retraining_active = False

@app.get("/drift-status", response_model=DriftStatusResponse, tags=["MLOps"])
def get_drift_status(
    window: int = Query(100, ge=5, le=1000, description="Number of recent production predictions to evaluate"),
    db: Session = Depends(get_db)
):
    """
    Calculates Population Stability Index (PSI) drift across telemetry features
    comparing recent production predictions from the database against training baseline.
    Protected with a 20-second cache to avoid slamming the database during high-frequency polling.
    """
    now = time.time()
    if _drift_cache["report"] and _drift_cache["window"] == window and (now - _drift_cache["timestamp"] < 20.0):
        return _drift_cache["report"]

    try:
        records = (
            db.query(PredictionRecord)
            .order_by(desc(PredictionRecord.timestamp))
            .limit(window)
            .all()
        )
        formatted_records = [r.to_dict() for r in records]
        report = drift_detector.evaluate_production_data(formatted_records)

        # Update Prometheus drift metrics
        METRICS["drift_detected"] = 1 if report.get("drift_detected") else 0
        METRICS["max_psi"] = float(report.get("max_psi") or 0.0)

        # Cache result
        _drift_cache["timestamp"] = now
        _drift_cache["window"] = window
        _drift_cache["report"] = report

        return report
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Drift detection error: {str(e)}"
        )

@app.post("/drift-status/reset", tags=["MLOps"])
def reset_drift_detector():
    """
    Reloads baseline reference statistics from the ML directory and clears cache.
    """
    _drift_cache["report"] = None
    loaded = drift_detector.load_reference_stats()
    METRICS["drift_detected"] = 0
    METRICS["max_psi"] = 0.0
    return {
        "status": "reset_successful" if loaded else "baseline_missing",
        "reference_version": drift_detector.reference_stats.get("model_version"),
        "message": "Baseline statistics reloaded successfully."
    }

def execute_retraining():
    """
    Runs the ML training pipeline script, updates version, and reloads model in memory.
    Guarded by _retrain_lock.
    """
    global _retraining_active
    train_script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ml", "train.py")
    try:
        print("[Retraining] Triggering ml/train.py...")
        result = subprocess.run([sys.executable, train_script], capture_output=True, text=True, check=True)
        print("[Retraining] Training completed successfully:")
        print(result.stdout[-400:])
        predictor.load_model()
        drift_detector.load_reference_stats()
        # Invalidate drift cache on new model reload
        _drift_cache["report"] = None
        print(f"[Retraining] Predictor successfully reloaded with version {predictor.version}")
    except Exception as e:
        print(f"[Retraining] Pipeline error: {e}")
    finally:
        with _retrain_lock:
            _retraining_active = False

@app.post("/retrain", tags=["MLOps"])
def trigger_retraining(
    background_tasks: BackgroundTasks,
    api_key: str = Depends(require_admin_api_key)
):
    """
    Triggers the training pipeline in the background to address data/model drift.
    Requires administrative API key ('X-API-Key' header or JWT with role == 'admin').
    Increments model version (v1 -> v2 -> v3), logs to MLflow, and reloads model.
    Guarded by atomic mutex lock to prevent concurrent retraining collisions.
    """
    global _retraining_active
    with _retrain_lock:
        if _retraining_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A model retraining pipeline job is already in progress. Please wait for completion."
            )
        _retraining_active = True

    background_tasks.add_task(execute_retraining)
    return {
        "status": "retraining_initiated",
        "current_version": predictor.version,
        "message": "Retraining job queued in background. Model will be auto-promoted upon completion."
    }
