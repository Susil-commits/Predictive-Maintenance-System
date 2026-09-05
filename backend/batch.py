"""
backend/batch.py
================
Batch prediction endpoint: POST /batch-predict
Export endpoint:           GET  /export

Accepts CSV, JSON, Excel (.xlsx) or Parquet file uploads, fuzzy-matches
column names to expected telemetry fields, runs the ML model on every row,
and returns per-row results including SHAP feature contributions.

Errors are reported row-by-row (bad rows are skipped, not fail-all).
"""

import io
import csv
import json
from typing import Optional, List

import numpy as np
import pandas as pd
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query, Request
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from sqlalchemy import desc

from .database import get_db
from .models import PredictionRecord
from .predictor import predictor
from .limiter import limiter
from .auth import require_admin_auth as require_admin_api_key

router = APIRouter(tags=["Batch"])

# ---------------------------------------------------------------------------
# Column fuzzy-mapping -------------------------------------------------------
# ---------------------------------------------------------------------------

# Expected canonical names → acceptable variants (case-insensitive, stripped)
COLUMN_ALIASES: dict[str, list[str]] = {
    "temperature":     ["temperature", "temp", "temperature_c", "temp_c", "operating_temp", "engine_temp"],
    "rpm":             ["rpm", "rotational_speed", "rotation_speed", "rot_speed", "speed_rpm", "rev_per_min"],
    "pressure":        ["pressure", "hydraulic_pressure", "press", "bar", "pressure_bar", "sys_pressure"],
    "vibration":       ["vibration", "vib", "vibration_amplitude", "vibration_g", "vib_rms"],
    "operating_hours": ["operating_hours", "op_hours", "hours", "service_hours", "cumulative_hours", "total_hours"],
}


def _fuzzy_match_columns(df: pd.DataFrame) -> dict[str, str]:
    """
    Returns a mapping: {canonical_name: actual_df_column}
    Raises ValueError if any required field cannot be matched, explicitly detailing
    all missing fields, detected columns, and expected aliases.
    """
    df_cols_lower = {c.lower().strip().replace(" ", "_"): c for c in df.columns}
    mapping: dict[str, str] = {}
    missing_fields: list[dict] = []

    for canonical, aliases in COLUMN_ALIASES.items():
        matched = None
        for alias in aliases:
            norm = alias.lower().strip()
            if norm in df_cols_lower:
                matched = df_cols_lower[norm]
                break
        if matched is None:
            missing_fields.append({
                "canonical": canonical,
                "aliases": aliases
            })
        else:
            mapping[canonical] = matched

    if missing_fields:
        missing_names = [m["canonical"] for m in missing_fields]
        found_cols = list(df.columns)
        err_msg = (
            f"Missing {len(missing_fields)} required column(s): {', '.join(missing_names)}. "
            f"Found columns in file: {found_cols}. "
            f"Expected acceptable column names for missing fields: "
            + "; ".join([f"{m['canonical']} -> {', '.join(m['aliases'])}" for m in missing_fields])
        )
        raise ValueError(err_msg)

    return mapping


# ---------------------------------------------------------------------------
# File parsers ---------------------------------------------------------------
# ---------------------------------------------------------------------------

def _parse_file(content: bytes, filename: str) -> pd.DataFrame:
    """Detect file format from filename extension and parse into a DataFrame."""
    lower = filename.lower()
    if lower.endswith(".csv"):
        return pd.read_csv(io.BytesIO(content))
    elif lower.endswith(".json"):
        raw = json.loads(content)
        if isinstance(raw, list):
            return pd.DataFrame(raw)
        elif isinstance(raw, dict):
            return pd.DataFrame([raw])
        else:
            raise ValueError("JSON file must contain an array of objects or a single object.")
    elif lower.endswith(".xlsx") or lower.endswith(".xls"):
        return pd.read_excel(io.BytesIO(content))
    elif lower.endswith(".parquet"):
        return pd.read_parquet(io.BytesIO(content))
    else:
        # Attempt CSV as fallback
        try:
            return pd.read_csv(io.BytesIO(content))
        except Exception:
            raise ValueError(
                f"Unsupported file format: '{filename}'. "
                "Supported formats: .csv, .json, .xlsx, .parquet"
            )


# ---------------------------------------------------------------------------
# Range / type validation ----------------------------------------------------
# ---------------------------------------------------------------------------

FIELD_RANGES = {
    "temperature":     (-20.0, 250.0),
    "rpm":             (100.0, 6000.0),
    "pressure":        (1.0,   100.0),
    "vibration":       (0.01,  5.0),
    "operating_hours": (0.0,   50000.0),
}


def _coerce_and_validate_row(row: dict) -> tuple[dict | None, str | None]:
    """
    Coerce row values to float and do basic range checks.
    Returns (coerced_dict, None) on success, or (None, error_string) on failure.
    """
    result = {}
    for field, (lo, hi) in FIELD_RANGES.items():
        raw = row.get(field)
        if raw is None:
            return None, f"Field '{field}' is missing or null"
        try:
            val = float(raw)
        except (TypeError, ValueError):
            return None, f"Field '{field}' has non-numeric value: {raw!r}"

        if not np.isfinite(val):
            return None, f"Field '{field}' is NaN or Inf: {raw!r}"

        if not (lo <= val <= hi):
            return None, (
                f"Field '{field}' value {val} is out of range [{lo}, {hi}]"
            )
        result[field] = val

    return result, None


def _run_batch_inference(df_norm: pd.DataFrame, threshold: float) -> list[dict]:
    """
    Executes per-row feature validation and SHAP model inference in a threadpool worker.
    """
    results: list[dict] = []
    for idx, row_series in df_norm.iterrows():
        row_dict = row_series.to_dict()
        row_result: dict = {"row_index": int(idx)}  # type: ignore[arg-type]

        # Copy raw input for transparency
        row_result["input_data"] = {k: row_dict.get(k) for k in COLUMN_ALIASES}

        # Validate
        coerced, err = _coerce_and_validate_row(row_dict)
        if err:
            row_result["error"] = err
            results.append(row_result)
            continue

        # Inference
        try:
            pred = predictor.predict(coerced, threshold=threshold)  # type: ignore[arg-type]
        except Exception as exc:
            row_result["error"] = f"Inference failed: {exc}"
            results.append(row_result)
            continue

        row_result["prediction"]   = pred["failure_risk"]
        row_result["probability"]  = pred["probability"]
        row_result["maintenance_required"] = pred["maintenance_required"]
        row_result["shap_values"]  = pred["shap_values"]
        row_result["contributing_factors"] = pred["contributing_factors"]
        row_result["decision_threshold"] = pred["decision_threshold"]
        results.append(row_result)

    return results


# ---------------------------------------------------------------------------
# POST /batch-predict --------------------------------------------------------
# ---------------------------------------------------------------------------

@router.post("/batch-predict", summary="Batch telemetry prediction from uploaded file")
@limiter.limit("10/minute")
async def batch_predict(
    request: Request,
    file: UploadFile = File(..., description="CSV, JSON, Excel (.xlsx), or Parquet telemetry file"),
    api_key: str = Depends(require_admin_api_key),
):
    """
    Accepts a multi-row telemetry file, fuzzy-matches column names to expected
    fields (temperature, rpm, pressure, vibration, operating_hours), validates
    each row, runs inference, and returns per-row results with SHAP values.

    Malformed / out-of-range rows are reported individually — they do NOT
    abort the entire batch.
    """
    if predictor.model is None:
        raise HTTPException(status_code=503, detail="ML model is not loaded.")

    # --- Read file bytes ---
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large, max 5MB")

    # --- Parse ---
    try:
        df = _parse_file(content, file.filename or "upload")
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"File parse error: {exc}")

    if df.empty:
        raise HTTPException(status_code=422, detail="Parsed file contains no rows.")
    if len(df) > 5000:
        raise HTTPException(status_code=422, detail="Too many rows, max 5000 per batch")

    # --- Fuzzy column mapping ---
    try:
        col_map = _fuzzy_match_columns(df)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # Build a normalised frame using canonical column names
    selected_cols = [col_map[c] for c in COLUMN_ALIASES]
    df_selected = pd.DataFrame(df[selected_cols])
    df_norm = df_selected.rename(columns={v: k for k, v in col_map.items()})

    threshold = getattr(predictor, "threshold", 0.50)

    # Offload CPU-heavy inference from the main asyncio event loop to prevent freezing concurrent requests/health-checks
    results = await run_in_threadpool(_run_batch_inference, df_norm, threshold)

    # --- Summary statistics ---
    valid_rows   = [r for r in results if "error" not in r]
    error_rows   = [r for r in results if "error" in r]
    high_risk    = sum(1 for r in valid_rows if r.get("prediction") == "HIGH")
    low_risk     = len(valid_rows) - high_risk

    return {
        "total_rows":     len(results),
        "processed_rows": len(valid_rows),
        "error_rows":     len(error_rows),
        "high_risk_count": high_risk,
        "low_risk_count":  low_risk,
        "results":        results,
    }


# ---------------------------------------------------------------------------
# GET /export ----------------------------------------------------------------
# ---------------------------------------------------------------------------

@router.get("/export", summary="Export prediction history as CSV")
def export_history(
    limit: int = Query(500, ge=1, le=5000, description="Max rows to export"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD or ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD or ISO format)"),
    db: Session = Depends(get_db),
    api_key: str = Depends(require_admin_api_key),
):
    """
    Streams prediction records as a downloadable CSV file, with optional date range filtering.
    """
    from datetime import datetime

    query = db.query(PredictionRecord)

    start_dt = None
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.strip().replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid start_date format: '{start_date}'. Use YYYY-MM-DD or ISO 8601 format."
            )
        query = query.filter(PredictionRecord.timestamp >= start_dt)

    end_dt = None
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.strip().replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid end_date format: '{end_date}'. Use YYYY-MM-DD or ISO 8601 format."
            )
        query = query.filter(PredictionRecord.timestamp <= end_dt)

    if start_dt and end_dt and start_dt > end_dt:
        raise HTTPException(
            status_code=422,
            detail="start_date cannot be greater than end_date."
        )

    try:
        records = query.order_by(desc(PredictionRecord.timestamp)).limit(limit).all()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}")

    if not records:
        raise HTTPException(status_code=404, detail="No prediction history found to export.")

    output = io.StringIO()
    fieldnames = [
        "prediction_id", "timestamp", "temperature", "rpm",
        "pressure", "vibration", "operating_hours",
        "failure_risk", "probability", "maintenance_required",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for rec in records:
        writer.writerow({
            "prediction_id": rec.prediction_id,
            "timestamp": rec.timestamp.isoformat() if rec.timestamp is not None else "",
            "temperature": rec.temperature,
            "rpm": rec.rpm,
            "pressure": rec.pressure,
            "vibration": rec.vibration,
            "operating_hours": rec.operating_hours,
            "failure_risk": rec.failure_risk,
            "probability": rec.probability,
            "maintenance_required": rec.maintenance_required,
        })

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=pms_history.csv"},
    )
