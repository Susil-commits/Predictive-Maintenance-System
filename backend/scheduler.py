"""
Automated MLOps Scheduler using APScheduler for PMS.
Monitors live production data drift on a scheduled interval (daily) using PSI.
If statistical feature drift exceeds threshold (PSI >= 0.25):
- Flags 'retraining recommended'
- Automatically triggers ml/train.py pipeline to generate a candidate model
- Does NOT auto-promote: logs results and prepares candidate for canary rollout
"""

import os
import sys
import subprocess
import logging
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import desc

from .database import SessionLocal
from .models import PredictionRecord
from .drift_detector import drift_detector
from .metrics import metrics

logger = logging.getLogger("pms.scheduler")

class DriftScheduler:
    """Manages scheduled drift checks and automated candidate retraining."""
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._lock = threading.Lock()
        self.state: Dict[str, Any] = {
            "is_running": False,
            "last_check_timestamp": None,
            "drift_detected": False,
            "max_psi": 0.0,
            "retraining_recommended": False,
            "last_retrain_timestamp": None,
            "last_retrain_status": "IDLE",
            "candidate_version": None,
            "audit_logs": []
        }

    def start(self) -> None:
        """Starts the APScheduler with daily drift evaluation job."""
        if not self.scheduler.running:
            # Schedule daily at 02:00 UTC, or default 24h interval
            self.scheduler.add_job(
                self.run_drift_check,
                trigger=IntervalTrigger(hours=24),
                id="daily_drift_monitoring",
                name="Daily Production Data Drift & Retraining Check",
                replace_existing=True
            )
            self.scheduler.start()
            self.state["is_running"] = True
            logger.info("APScheduler initialized with daily drift check (every 24 hours).")

    def shutdown(self) -> None:
        """Gracefully shuts down APScheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            self.state["is_running"] = False
            logger.info("APScheduler successfully stopped.")

    def log_event(self, event_msg: str) -> None:
        """Appends timestamped event to scheduler audit log."""
        timestamp = datetime.now(timezone.utc).isoformat()
        log_entry = f"[{timestamp}] {event_msg}"
        with self._lock:
            self.state["audit_logs"].append(log_entry)
            if len(self.state["audit_logs"]) > 50:
                self.state["audit_logs"].pop(0)
        logger.info(event_msg)

    async def run_drift_check(self, window_size: int = 100) -> Dict[str, Any]:
        """
        Executes drift evaluation against recent production predictions.
        If PSI exceeds threshold, flags retraining recommended and triggers training pipeline.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        self.log_event("[Scheduler] Starting scheduled production drift evaluation...")
        
        # 1. Fetch recent records from database
        try:
            with SessionLocal() as db:
                records = (
                    db.query(PredictionRecord)
                    .order_by(desc(PredictionRecord.timestamp))
                    .limit(window_size)
                    .all()
                )
                formatted_records = [r.to_dict() for r in records]
        except Exception as db_err:
            msg = f"[Scheduler] Failed to query production records from database: {db_err}"
            logger.error(msg)
            return {"status": "ERROR", "message": msg}

        # 2. Evaluate drift
        drift_report = drift_detector.evaluate_production_data(formatted_records)
        max_psi = float(drift_report.get("max_psi") or 0.0)
        drift_detected = bool(drift_report.get("drift_detected", False)) or max_psi >= 0.25
        
        feature_psis = {
            m["feature"]: float(m["psi"])
            for m in drift_report.get("feature_metrics", [])
            if "feature" in m and "psi" in m
        }
        
        # Update Prometheus metrics
        metrics.update_drift(drift_detected=drift_detected, max_psi=max_psi, feature_psis=feature_psis)

        with self._lock:
            self.state["last_check_timestamp"] = now_iso
            self.state["drift_detected"] = drift_detected
            self.state["max_psi"] = max_psi

        # 3. Check if retraining threshold exceeded
        if drift_detected:
            self.log_event(
                f"[Scheduler] Significant drift detected (max PSI = {max_psi:.4f}). "
                f"Flagging 'retraining recommended' and triggering automated candidate training..."
            )
            with self._lock:
                self.state["retraining_recommended"] = True
                self.state["last_retrain_status"] = "TRIGGERED"

            # Trigger training pipeline in background thread to avoid blocking event loop
            threading.Thread(target=self._execute_retraining_pipeline, daemon=True).start()
            
            return {
                "status": "DRIFT_DETECTED",
                "retraining_recommended": True,
                "max_psi": max_psi,
                "drifted_features": drift_report.get("drifted_features", []),
                "action": "candidate_retraining_triggered"
            }
        else:
            self.log_event(f"[Scheduler] Drift check passed. Population distribution stable (max PSI = {max_psi:.4f}).")
            with self._lock:
                self.state["retraining_recommended"] = False
                self.state["last_retrain_status"] = "STABLE"
                
            return {
                "status": "HEALTHY",
                "retraining_recommended": False,
                "max_psi": max_psi,
                "message": "Distribution healthy. No retraining necessary."
            }

    def _execute_retraining_pipeline(self) -> None:
        """Executes ml/train.py to generate a candidate model without auto-promoting."""
        train_script = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ml", "train.py"
        )
        try:
            logger.info("[Scheduler Retrain] Executing ml/train.py...")
            result = subprocess.run(
                [sys.executable, train_script],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"[Scheduler Retrain] Completed successfully. Summary: {result.stdout[-300:].strip()}")
            with self._lock:
                self.state["last_retrain_timestamp"] = datetime.now(timezone.utc).isoformat()
                self.state["last_retrain_status"] = "CANDIDATE_READY"
            self.log_event(
                "[Scheduler] Automated retraining finished. Candidate model produced and flagged for canary evaluation."
            )
        except subprocess.CalledProcessError as sub_err:
            logger.error(f"[Scheduler Retrain] Pipeline error: {sub_err.stderr[-400:]}")
            with self._lock:
                self.state["last_retrain_status"] = "FAILED"
        except Exception as err:
            logger.error(f"[Scheduler Retrain] Unexpected error: {err}")
            with self._lock:
                self.state["last_retrain_status"] = "FAILED"

    def get_status(self) -> Dict[str, Any]:
        """Returns scheduler state and scheduled job details."""
        with self._lock:
            jobs_info = []
            for j in self.scheduler.get_jobs():
                jobs_info.append({
                    "id": j.id,
                    "name": j.name,
                    "next_run_time": j.next_run_time.isoformat() if j.next_run_time else None
                })
            return {
                **self.state,
                "active_jobs": jobs_info
            }

drift_scheduler = DriftScheduler()
