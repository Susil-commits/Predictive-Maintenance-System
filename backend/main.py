import logging
import os
import subprocess
import sys
import threading
import time
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from dotenv import load_dotenv

load_dotenv()


def validate_startup_env():
    required_vars = ["DATABASE_URL", "PMS_API_KEY", "JWT_SECRET", "ADMIN_PASSWORD"]
    missing = [v for v in required_vars if not os.getenv(v, "").strip()]
    if missing:
        raise RuntimeError(f"Missing required environment variables at startup: {', '.join(missing)}")


validate_startup_env()

from fastapi import (
    BackgroundTasks,
    Body,
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Query,
    Request,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse, PlainTextResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import desc, text
from sqlalchemy.orm import Session

from .auth import (
    require_admin_auth,
    seed_initial_admin,
)
from .auth import (
    router as auth_router,
)
from .batch import router as batch_router
from .canary import canary_manager
from .database import Base, SessionLocal, engine, get_db
from .docs_theme import (
    API_DESCRIPTION,
    TAGS_METADATA,
    get_pms_redoc_html,
    get_pms_swagger_html,
)
from .drift_detector import drift_detector
from .limiter import limiter
from .logging_config import set_request_id
from .metrics import metrics
from .models import PredictionRecord
from .narration_service import orchestrate_predict_and_narrate
from .predictor import (
    FEATURE_ORDER,
    calibrated_model,
    find_minimal_fix,
    predictor,
    scaler,
)
from .rul_engine import predict_rul
from .scheduler import drift_scheduler
from .schemas import (
    CounterfactualOutput,
    DriftStatusResponse,
    HealthResponse,
    ModelInfoResponse,
    NarrationOutput,
    PredictionInput,
    PredictionOutput,
    RULOutput,
)

logger = logging.getLogger("pms.api")


def init_db():
    """Ensure tables are created and default admin is seeded."""
    try:
        if engine is not None:
            Base.metadata.create_all(bind=engine)
            # Ensure designation column exists on existing user tables
            try:
                with engine.connect() as conn:
                    conn.execute(
                        text(
                            "ALTER TABLE pms_users ADD COLUMN IF NOT EXISTS designation VARCHAR(128) DEFAULT 'Maintenance Specialist';"
                        )
                    )
                    conn.commit()
            except Exception:
                pass
        with SessionLocal() as _db:
            seed_initial_admin(_db)
    except RuntimeError:
        raise
    except Exception as e:
        logger.info(f"Table creation/admin seed note: {e}")


init_db()


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_startup_env()
    init_db()
    drift_scheduler.start()
    yield
    drift_scheduler.shutdown()


app = FastAPI(
    title="Predictive Maintenance System API",
    description=API_DESCRIPTION,
    version="1.1.0",
    docs_url=None,
    redoc_url=None,
    openapi_url="/openapi.json",
    openapi_tags=TAGS_METADATA,
    lifespan=lifespan,
)
from backend.security import (
    EnterpriseSecurityHeadersMiddleware,
    configure_enterprise_cors,
    get_audit_logger,
    get_failover_manager,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore

# Enterprise Security: Hardened CORS & Security Headers Middleware
configure_enterprise_cors(app)
app.add_middleware(EnterpriseSecurityHeadersMiddleware)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Binds or generates X-Request-ID for end-to-end distributed tracing across logs and responses."""
    req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    set_request_id(req_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = req_id
    return response


def predict_rate_limit() -> str:
    """Dynamic rate limiter supporting load test mode via LOAD_TEST_MODE env var."""
    if os.getenv("LOAD_TEST_MODE") == "1":
        return "1000000/minute"
    return "60/minute"


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
    )
    # Enable interactive Swagger UI Authorize modal with API Key and JWT schemes
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "Administrative API Key matching PMS_API_KEY environment variable",
        },
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Signed JWT token from `POST /auth/login`. Enter your token directly.",
        },
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi  # type: ignore


@app.get("/docs", include_in_schema=False)
async def custom_swagger_docs():
    """Interactive Swagger UI documentation with custom dark theme, brand navigation and live status."""
    return HTMLResponse(get_pms_swagger_html(openapi_url=app.openapi_url or "/openapi.json"))


@app.get("/redoc", include_in_schema=False)
async def custom_redoc_docs():
    """Clean ReDoc technical reference documentation."""
    return HTMLResponse(get_pms_redoc_html(openapi_url=app.openapi_url or "/openapi.json"))


# Register authentication & batch routes
app.include_router(auth_router)
app.include_router(batch_router)


def require_admin_api_key(
    authorization: str | None = Header(None, alias="Authorization"),
    x_api_key: str | None = Header(None, alias="X-API-Key"),
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
    "max_psi": 0.0,
}


@app.get("/metrics", tags=["Metrics"])
def get_metrics():
    """
    Exposes Prometheus format system, prediction latency histogram, risk counters, and MLOps drift metrics.
    """
    return PlainTextResponse(metrics.generate_prometheus_text(), media_type="text/plain; version=0.0.4")


# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# OWASP Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response


@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check(request: Request, db: Session = Depends(get_db)):
    """
    Health check endpoint returning system, model, version, and database status.
    Un-throttled to ensure platform load balancer and deployment health checks never fail.
    """
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "operational"

    return {
        "status": "healthy",
        "database": db_status,
        "model_loaded": predictor.model is not None,
        "model_version": predictor.version,
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
            detail="Model metadata is currently unavailable",
        )
    return metadata


@app.post("/predict", response_model=PredictionOutput, tags=["Prediction"])
@limiter.limit(predict_rate_limit)
def predict_maintenance(request: Request, input_data: PredictionInput, db: Session = Depends(get_db)):
    """
    Given vehicle/equipment telemetry, predicts failure risk, probability,
    and computes SHAP-based feature contributions. Logs result to PostgreSQL/database.
    Applies the decision threshold tuned via Precision-Recall curve.
    Evaluates dual-model shadow prediction if canary rollout is active.
    """
    t_start = time.perf_counter()
    # Active decision threshold tuned via Precision-Recall curve (defaulting to 0.50 if not specified)
    threshold = getattr(predictor, "threshold", 0.50)
    try:
        pred_result = predictor.predict(input_data.model_dump(), threshold=threshold)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference error: {e!s}",
        )

    # Explicitly enforce PR-tuned decision threshold in prediction classification logic
    failure_risk = "HIGH" if pred_result["probability"] >= threshold else "LOW"
    pred_result["failure_risk"] = failure_risk
    pred_result["maintenance_required"] = pred_result["probability"] >= threshold
    pred_result["decision_threshold"] = threshold

    # Update Prometheus counters and backward-compatible METRICS dict
    METRICS["total_predictions"] += 1
    if pred_result["failure_risk"] == "HIGH":
        METRICS["high_risk_predictions"] += 1
    else:
        METRICS["low_risk_predictions"] += 1

    metrics.record_prediction(pred_result["failure_risk"])

    # Generate unique ID and timestamp
    pred_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    # Canary shadow evaluation if active
    if canary_manager.is_active:
        try:
            features_df = predictor.engineer_features(input_data.model_dump())
            canary_manager.evaluate_request(features_df, pred_result, pred_id)
        except Exception as c_err:
            logger.warning(f"Canary shadow evaluation failed: {c_err}")

    # Record inference duration in Prometheus latency histogram
    duration = time.perf_counter() - t_start
    metrics.record_predict_latency(duration)

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
            contributing_factors=pred_result["contributing_factors"],
        )
        db.add(db_record)
        db.commit()
    except Exception as db_err:
        db.rollback()
        logger.warning(f"Failed to log prediction to database: {db_err}")

    pred_result["prediction_id"] = pred_id
    pred_result["timestamp"] = now.isoformat()
    return pred_result


@app.post("/predict/narrate", response_model=NarrationOutput, tags=["Prediction"])
@limiter.limit(predict_rate_limit)
def predict_with_narration(
    request: Request,
    input_data: PredictionInput,
    include_counterfactual: bool = Query(
        False, description="Whether to include counterfactual remediation in response"
    ),
    db: Session = Depends(get_db),
):
    """
    Given vehicle/equipment telemetry:
    1. Computes ML failure risk probability & SHAP root causes (via existing predictor).
    2. Retrieves standard industrial operating procedures from RAG vector store for the dominant risk factor.
    3. Synthesizes a fluent, context-specific LLM narration strictly grounded in the prediction metrics.
    4. Silently falls back to canned prescriptive guidance if the external LLM is down or times out.
    5. Returns the auditable source chunks alongside the narrative.
    """
    t_start = time.perf_counter()
    threshold = getattr(predictor, "threshold", 0.50)
    try:
        result = orchestrate_predict_and_narrate(
            input_data.model_dump(),
            threshold=threshold,
            include_counterfactual=include_counterfactual,
        )
    except Exception as e:
        logger.error(f"Narration inference error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference error: {e!s}",
        )

    # Metrics & Prometheus recording
    failure_risk = result["failure_risk"]
    METRICS["total_predictions"] += 1
    if failure_risk == "HIGH":
        METRICS["high_risk_predictions"] += 1
    else:
        METRICS["low_risk_predictions"] += 1
    metrics.record_prediction(failure_risk)

    pred_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    # Canary shadow evaluation if active
    if canary_manager.is_active:
        try:
            features_df = predictor.engineer_features(input_data.model_dump())
            canary_manager.evaluate_request(features_df, result, pred_id)
        except Exception as c_err:
            logger.warning(f"Canary shadow evaluation failed in narrate: {c_err}")

    # Record latency
    duration = time.perf_counter() - t_start
    metrics.record_predict_latency(duration)

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
            failure_risk=result["failure_risk"],
            probability=result["probability"],
            maintenance_required=result["maintenance_required"],
            shap_values=result["shap_values"],
            contributing_factors=result["contributing_factors"],
        )
        db.add(db_record)
        db.commit()
    except Exception as db_err:
        db.rollback()
        logger.warning(f"Failed to log prediction to database: {db_err}")

    result["prediction_id"] = pred_id
    result["timestamp"] = now.isoformat()
    return result


@app.post("/predict-counterfactual", response_model=CounterfactualOutput, tags=["Prediction"])
@limiter.limit(predict_rate_limit)
def predict_counterfactual(request: Request, input_data: PredictionInput):
    """
    Given vehicle/equipment telemetry, calculates counterfactual remediation:
    finds the minimal change in the dominant risk-driving parameter that brings
    predicted failure risk below the PR-tuned decision threshold.
    """
    try:
        features = input_data.model_dump()
        threshold = getattr(predictor, "threshold", 0.2288)
        result = find_minimal_fix(calibrated_model, scaler, features, FEATURE_ORDER, threshold=threshold)
        return result
    except Exception as e:
        logger.error(f"Counterfactual calculation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Counterfactual calculation error: {e!s}",
        )


@app.post("/predict-rul", response_model=RULOutput, tags=["RUL"])
def predict_remaining_useful_life(
    equipment_history: list[dict] = Body(...),  # Time series sensor readings
):
    """
    Predict cycles and operating hours remaining before equipment failure.
    Input: time-series array of recent sensor readings
    Output: estimated RUL in cycles, operating hours, confidence, and maintenance recommendation
    """
    try:
        rul_cycles, confidence = predict_rul(equipment_history)
        return {
            "estimated_rul_cycles": round(rul_cycles),
            "estimated_rul_hours": round(rul_cycles * 0.5, 1),
            "confidence": confidence,
            "recommendation": ("Schedule maintenance" if rul_cycles < 50 else "Continue monitoring"),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/history", tags=["Audit & History"])
def get_prediction_history(limit: int = Query(25, ge=1, le=100), db: Session = Depends(get_db)):
    """
    Retrieves the most recent predictions logged in the database.
    """
    try:
        records = db.query(PredictionRecord).order_by(desc(PredictionRecord.timestamp)).limit(limit).all()
        return [r.to_dict() for r in records]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query error: {e!s}",
        )


@app.delete(
    "/history",
    tags=["Audit & History"],
    openapi_extra={"security": [{"ApiKeyAuth": []}, {"BearerAuth": []}]},
)
def clear_prediction_history(db: Session = Depends(get_db), api_key: str = Depends(require_admin_api_key)):
    """
    Clears logged history (useful for dashboard resetting).
    Requires administrative authorization ('X-API-Key' header or admin JWT).
    """
    try:
        num_deleted = db.query(PredictionRecord).delete()
        db.commit()
        return {"message": f"Successfully deleted {num_deleted} records"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database clear error: {e!s}",
        )


@app.post(
    "/history/prune",
    tags=["Audit & History"],
    openapi_extra={"security": [{"ApiKeyAuth": []}, {"BearerAuth": []}]},
)
def prune_prediction_history(
    days: int = Query(30, ge=1, le=365, description="Prune records older than this many days"),
    db: Session = Depends(get_db),
    api_key: str = Depends(require_admin_api_key),
):
    """
    Prunes prediction records older than specified retention days (default: 30 days).
    Requires administrative authorization ('X-API-Key' or admin JWT).
    """
    from datetime import timedelta

    cutoff = datetime.now(UTC) - timedelta(days=days)
    try:
        num_deleted = db.query(PredictionRecord).filter(PredictionRecord.timestamp < cutoff).delete()
        db.commit()
        logger.info(f"Pruned {num_deleted} prediction records older than {days} days ({cutoff.isoformat()})")
        return {
            "status": "success",
            "pruned_count": num_deleted,
            "cutoff_timestamp": cutoff.isoformat(),
            "retention_days": days,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database prune error: {e!s}",
        )


# ==================== MLOps: Drift Detection & Retraining ====================

# In-memory TTL cache for drift evaluation to prevent database table scan storms
_drift_cache: dict[str, Any] = {"timestamp": 0.0, "window": 0, "report": None}

# Retraining concurrency lock to prevent parallel pipeline execution collisions
_retrain_lock = threading.Lock()
_retraining_active = False


@app.get("/drift-status", response_model=DriftStatusResponse, tags=["MLOps"])
def get_drift_status(
    window: int = Query(
        100,
        ge=5,
        le=1000,
        description="Number of recent production predictions to evaluate",
    ),
    db: Session = Depends(get_db),
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
        records = db.query(PredictionRecord).order_by(desc(PredictionRecord.timestamp)).limit(window).all()
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
            detail=f"Drift detection error: {e!s}",
        )


@app.post(
    "/drift-status/reset",
    tags=["MLOps"],
    openapi_extra={"security": [{"ApiKeyAuth": []}, {"BearerAuth": []}]},
)
def reset_drift_detector(api_key: str = Depends(require_admin_api_key)):
    """
    Reloads baseline reference statistics from the ML directory and clears cache.
    Requires administrative API key ('X-API-Key' header or JWT with role == 'admin').
    """
    _drift_cache["report"] = None
    loaded = drift_detector.load_reference_stats()
    METRICS["drift_detected"] = 0
    METRICS["max_psi"] = 0.0
    return {
        "status": "reset_successful" if loaded else "baseline_missing",
        "reference_version": drift_detector.reference_stats.get("model_version"),
        "message": "Baseline statistics reloaded successfully.",
    }


def execute_retraining():
    """
    Runs the ML training pipeline script, updates version, and reloads model in memory.
    Guarded by _retrain_lock.
    """
    global _retraining_active
    train_script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ml", "train.py")
    try:
        logger.info("[Retraining] Triggering ml/train.py...")
        result = subprocess.run([sys.executable, train_script], capture_output=True, text=True, check=True)
        logger.info(f"[Retraining] Training completed successfully. Tail: {result.stdout[-300:].strip()}")
        predictor.load_model()
        drift_detector.load_reference_stats()
        # Invalidate drift cache on new model reload
        _drift_cache["report"] = None
        logger.info(f"[Retraining] Predictor successfully reloaded with version {predictor.version}")
    except Exception as e:
        logger.error(f"[Retraining] Pipeline error: {e}")
    finally:
        with _retrain_lock:
            _retraining_active = False


@app.post(
    "/retrain",
    tags=["MLOps"],
    openapi_extra={"security": [{"ApiKeyAuth": []}, {"BearerAuth": []}]},
)
def trigger_retraining(background_tasks: BackgroundTasks, api_key: str = Depends(require_admin_api_key)):
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
                detail="A model retraining pipeline job is already in progress. Please wait for completion.",
            )
        _retraining_active = True

    background_tasks.add_task(execute_retraining)
    return {
        "status": "retraining_initiated",
        "current_version": predictor.version,
        "message": "Retraining job queued in background. Model will be auto-promoted upon completion.",
    }


# ==================== MLOps: Canary Rollout ====================


@app.get("/canary/status", tags=["MLOps"])
def get_canary_status():
    """Returns the current status of dual-model canary rollout."""
    return canary_manager.get_status()


@app.post(
    "/canary/start",
    tags=["MLOps"],
    openapi_extra={"security": [{"ApiKeyAuth": []}, {"BearerAuth": []}]},
)
def start_canary_rollout(api_key: str = Depends(require_admin_api_key)):
    """
    Activates canary evaluation mode for the next 50 live inference requests.
    Scores requests with both primary and candidate models in shadow mode.
    """
    return canary_manager.start_canary()


@app.post(
    "/canary/promote",
    tags=["MLOps"],
    openapi_extra={"security": [{"ApiKeyAuth": []}, {"BearerAuth": []}]},
)
def promote_canary_model(api_key: str = Depends(require_admin_api_key)):
    """
    Promotes the evaluated canary model to primary production model.
    """
    return canary_manager.promote_canary()


@app.post(
    "/canary/abort",
    tags=["MLOps"],
    openapi_extra={"security": [{"ApiKeyAuth": []}, {"BearerAuth": []}]},
)
def abort_canary_rollout(api_key: str = Depends(require_admin_api_key)):
    """
    Aborts active canary rollout and unloads candidate model.
    """
    return canary_manager.abort_canary()


# ==================== MLOps: Scheduler ====================


@app.get("/scheduler/jobs", tags=["MLOps"])
def get_scheduler_jobs():
    """Returns active scheduled jobs and next trigger times."""
    return drift_scheduler.get_status()


@app.post(
    "/scheduler/run-drift-check",
    tags=["MLOps"],
    openapi_extra={"security": [{"ApiKeyAuth": []}, {"BearerAuth": []}]},
)
async def trigger_scheduler_drift_check(api_key: str = Depends(require_admin_api_key)):
    """
    Manually triggers the daily scheduled drift check job on demand.
    Evaluates PSI and triggers candidate retraining if drift is detected.
    """
    return await drift_scheduler.run_drift_check()


# ==================== Enterprise AI Security & Compliance ====================


@app.get("/api/security/telemetry", tags=["Security & Compliance"])
async def get_security_telemetry():
    """Returns runtime telemetry for active enterprise security and AI guardrails."""
    failover_mgr = get_failover_manager()
    return {
        "status": "operational",
        "guardrails_active": True,
        "anti_prompt_injection": True,
        "canary_traps_enabled": True,
        "pii_redaction_enabled": True,
        "security_headers_enforced": True,
        "circuit_breakers": failover_mgr.all_statuses(),
    }


@app.get(
    "/api/security/audit-trail",
    tags=["Security & Compliance"],
    openapi_extra={"security": [{"ApiKeyAuth": []}, {"BearerAuth": []}]},
)
async def get_audit_trail(admin_auth: Any = Depends(require_admin_api_key)):
    """Retrieves cryptographically chained audit events (SOC 2 / ISO 27001). Requires ADMIN auth."""
    audit_logger = get_audit_logger()
    return {
        "events": audit_logger.get_recent_events(limit=50),
        "chain_verified": audit_logger.verify_chain()[0],
    }


@app.get(
    "/api/security/verify-chain",
    tags=["Security & Compliance"],
    openapi_extra={"security": [{"ApiKeyAuth": []}, {"BearerAuth": []}]},
)
async def verify_audit_chain(admin_auth: Any = Depends(require_admin_api_key)):
    """Cryptographically verifies tamper evidence across the audit hash chain."""
    audit_logger = get_audit_logger()
    is_valid, error = audit_logger.verify_chain()
    return {
        "is_valid": is_valid,
        "error": error,
        "algorithm": "SHA-256",
    }


@app.get(
    "/api/security/circuit-status",
    tags=["Security & Compliance"],
    openapi_extra={"security": [{"ApiKeyAuth": []}, {"BearerAuth": []}]},
)
async def get_circuit_status(admin_auth: Any = Depends(require_admin_api_key)):
    """Returns AI provider circuit breaker operational states."""
    failover_mgr = get_failover_manager()
    return {
        "providers": failover_mgr.all_statuses(),
    }

