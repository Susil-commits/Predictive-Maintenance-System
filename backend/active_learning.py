"""
Closed-Loop Active Learning & Production Precision Telemetry for PMS.

Bridges resolved CMMS work orders (technician ground-truth labels) back to:
1. Live production precision & false-alarm monitoring (GET /mlops/feedback-metrics).
2. Active-learning dataset export (data/production_feedback.csv) consumed by ml/train.py
   during retraining without contaminating the held-out benchmark test split.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from .models import PredictionRecord, WorkOrderRecord

logger = logging.getLogger("pms.active_learning")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_FEEDBACK_CSV = os.path.join(PROJECT_ROOT, "data", "production_feedback.csv")


def _normalize_failure_type(failure_mode: str | None, confirmed: bool) -> str:
    if not confirmed:
        return "Normal"
    mode = (failure_mode or "").lower()
    if "therm" in mode or "heat" in mode:
        return "Heat Dissipation Failure"
    if "strain" in mode or "press" in mode:
        return "Overstrain Failure"
    if "power" in mode or "rpm" in mode:
        return "Power Failure"
    if "wear" in mode or "vib" in mode or "bearing" in mode:
        return "Tool Wear Failure"
    return "Random Failures"


def compute_feedback_metrics(db: Session) -> dict[str, Any]:
    """Computes live production precision, false-alarm rate, and confusion counts from resolved work orders."""
    all_orders = db.query(WorkOrderRecord).all()
    total_orders = len(all_orders)

    labeled_orders = [wo for wo in all_orders if getattr(wo, "actual_failure_confirmed", None) is not None]
    pred_ids = [str(getattr(wo, "prediction_id")) for wo in labeled_orders if getattr(wo, "prediction_id", None)]

    preds_by_id: dict[str, PredictionRecord] = {}
    if pred_ids:
        matched_preds = db.query(PredictionRecord).filter(PredictionRecord.prediction_id.in_(pred_ids)).all()
        for p in matched_preds:
            preds_by_id[str(getattr(p, "prediction_id"))] = p

    confirmed_faults = 0
    false_alarms = 0
    tp = 0
    fp = 0
    fn = 0
    tn = 0
    labeled_with_telemetry = 0
    mode_breakdown: dict[str, dict[str, int]] = {}

    for wo in labeled_orders:
        wo_any: Any = wo
        confirmed = bool(wo_any.actual_failure_confirmed)
        if confirmed:
            confirmed_faults += 1
        else:
            false_alarms += 1

        mode_key = str(wo_any.failure_mode or "Unspecified")
        if mode_key not in mode_breakdown:
            mode_breakdown[mode_key] = {"confirmed": 0, "false_alarm": 0}
        if confirmed:
            mode_breakdown[mode_key]["confirmed"] += 1
        else:
            mode_breakdown[mode_key]["false_alarm"] += 1

        pid = wo_any.prediction_id
        pred = preds_by_id.get(str(pid)) if pid else None
        if pred is not None:
            labeled_with_telemetry += 1
            pred_any: Any = pred
            predicted_high = str(pred_any.failure_risk) == "HIGH"
        else:
            # Work orders dispatched from high-risk alerts default to predicted positive if unlinked
            predicted_high = str(wo_any.priority or "").upper() in ("CRITICAL", "HIGH")

        if predicted_high and confirmed:
            tp += 1
        elif predicted_high and not confirmed:
            fp += 1
        elif not predicted_high and confirmed:
            fn += 1
        else:
            tn += 1

    positives_pred = tp + fp
    prod_precision = round(tp / positives_pred, 4) if positives_pred > 0 else None
    false_alarm_rate = round(fp / positives_pred, 4) if positives_pred > 0 else None

    return {
        "total_work_orders": total_orders,
        "resolved_with_feedback": len(labeled_orders),
        "labeled_with_telemetry": labeled_with_telemetry,
        "confirmed_faults": confirmed_faults,
        "false_alarms": false_alarms,
        "confusion_matrix": {
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "true_negatives": tn,
        },
        "production_precision": prod_precision,
        "false_alarm_rate": false_alarm_rate,
        "failure_mode_breakdown": mode_breakdown,
    }


def export_feedback_dataset(db: Session, output_path: str = DEFAULT_FEEDBACK_CSV) -> dict[str, Any]:
    """
    Exports ground-truth labeled PredictionRecord + WorkOrderRecord pairs to CSV
    for active-learning retraining.
    """
    labeled_orders = db.query(WorkOrderRecord).filter(WorkOrderRecord.actual_failure_confirmed.isnot(None)).all()
    pred_ids = [str(getattr(wo, "prediction_id")) for wo in labeled_orders if getattr(wo, "prediction_id", None)]

    preds_by_id: dict[str, PredictionRecord] = {}
    if pred_ids:
        matched_preds = db.query(PredictionRecord).filter(PredictionRecord.prediction_id.in_(pred_ids)).all()
        for p in matched_preds:
            preds_by_id[str(getattr(p, "prediction_id"))] = p

    rows: list[dict[str, Any]] = []
    for wo in labeled_orders:
        wo_any: Any = wo
        pid = wo_any.prediction_id
        if not pid or str(pid) not in preds_by_id:
            continue
        pred_any: Any = preds_by_id[str(pid)]
        confirmed = bool(wo_any.actual_failure_confirmed)
        rows.append(
            {
                "temperature": float(pred_any.temperature),
                "rpm": float(pred_any.rpm),
                "pressure": float(pred_any.pressure),
                "vibration": float(pred_any.vibration),
                "operating_hours": float(pred_any.operating_hours),
                "failure": 1 if confirmed else 0,
                "failure_type": _normalize_failure_type(wo_any.failure_mode, confirmed),
                "source_weight": 2.5,
            }
        )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df = pd.DataFrame(
        rows,
        columns=[
            "temperature",
            "rpm",
            "pressure",
            "vibration",
            "operating_hours",
            "failure",
            "failure_type",
            "source_weight",
        ],
    )
    df.to_csv(output_path, index=False)
    logger.info(f"[ActiveLearning] Exported {len(rows)} labeled production samples to {output_path}")
    return {
        "exported_samples": len(rows),
        "confirmed_faults": sum(1 for r in rows if r["failure"] == 1),
        "false_alarms": sum(1 for r in rows if r["failure"] == 0),
        "output_path": output_path,
    }
