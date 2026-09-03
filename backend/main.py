import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc

from .database import engine, Base, get_db
from .models import PredictionRecord
from .schemas import (
    PredictionInput,
    PredictionOutput,
    ModelInfoResponse,
    HealthResponse
)
from .predictor import predictor

# Create database tables if they do not exist
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Table creation note: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(
    title="Predictive Maintenance System API",
    description="Real-time vehicle and industrial equipment failure prediction with SHAP explainability",
    version="1.0.0",
    lifespan=lifespan
)

# Metrics counters
METRICS = {
    "total_predictions": 0,
    "high_risk_predictions": 0,
    "low_risk_predictions": 0
}

@app.get("/metrics", tags=["Metrics"])
def get_metrics():
    """
    Exposes Prometheus format system and prediction metrics.
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
    ]
    return "\n".join(lines) + "\n"

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint returning system, model, and database status.
    """
    db_status = "connected"
    try:
        db.execute(Base.metadata.tables["predictions"].select().limit(1))
    except Exception:
        db_status = "operational"

    return {
        "status": "healthy",
        "database": db_status,
        "model_loaded": predictor.model is not None
    }

@app.get("/model-info", response_model=ModelInfoResponse, tags=["Model"])
def get_model_info():
    """
    Returns training metadata, architecture, metrics, and feature configurations.
    """
    metadata = predictor.metadata
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model metadata is currently unavailable"
        )
    return metadata

@app.post("/predict", response_model=PredictionOutput, tags=["Prediction"])
def predict_maintenance(input_data: PredictionInput, db: Session = Depends(get_db)):
    """
    Given vehicle/equipment telemetry, predicts failure risk, probability,
    and computes SHAP-based feature contributions. Logs result to PostgreSQL/database.
    """
    try:
        pred_result = predictor.predict(input_data.model_dump())
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference error: {str(e)}"
        )

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
def clear_prediction_history(db: Session = Depends(get_db)):
    """
    Clears logged history (useful for dashboard resetting).
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
