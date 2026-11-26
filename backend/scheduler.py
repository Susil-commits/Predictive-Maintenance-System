"""
Automated MLOps Scheduler using APScheduler for PMS.
Monitors live production data drift on a scheduled interval (daily) using PSI.
If statistical feature drift exceeds threshold (PSI >= 0.25):
- Flags 'retraining recommended'
- Automatically triggers ml/train.py pipeline to generate a candidate model
- Does NOT auto-promote: logs results and prepares candidate for canary rollout
"""

import logging
import os
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import desc

from .database import SessionLocal
from .drift_detector import drift_detector
from .metrics import metrics
from .models import PredictionRecord
from .redis_client import acquire_distributed_lock, cache_get_json, cache_set_json

logger = logging.getLogger("pms.scheduler")
SCHEDULER_STATE_KEY = "pms:scheduler:state"


class DriftScheduler:
    """Manages scheduled drift checks and automated candidate retraining."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._lock = threading.Lock()
        self.state: dict[str, Any] = {
            "is_running": False,
            "last_check_timestamp": None,
            "drift_detected": False,
            "max_psi": 0.0,
            "retraining_recommended": False,
            "last_retrain_timestamp": None,
            "last_retrain_status": "IDLE",
            "candidate_version": None,
            "audit_logs": [],
        }

    def start(self) -> None:
        """Starts the APScheduler with daily drift evaluation job."""
        if not self.scheduler.running:
            # Schedule daily at 02:00 UTC, or default 24h interval (leader-locked via Redis)
            self.scheduler.add_job(
                self.scheduled_drift_check,
                trigger=IntervalTrigger(hours=24),
                id="daily_drift_monitoring",
                name="Daily Production Data Drift & Retraining Check",
                replace_existing=True,
            )
            self.scheduler.start()
            self.state["is_running"] = True
            self._sync_state_to_redis()
            logger.info("APScheduler initialized with daily drift check (every 24 hours).")

    def _sync_state_to_redis(self) -> None:
        with self._lock:
            snapshot = dict(self.state)
        cache_set_json(SCHEDULER_STATE_KEY, snapshot, ttl_seconds=86400)

    async def scheduled_drift_check(self) -> dict[str, Any]:
        """Leader-locked scheduled drift check preventing duplicate execution across workers."""
        if not acquire_distributed_lock("pms:lock:drift_check", ttl_seconds=60):
            logger.info("[Scheduler] Another worker holds the drift check leader lock; skipping duplicate tick.")
            return {"status": "SKIPPED_LOCK_HELD"}
        return await self.run_drift_check()

    def shutdown(self, wait: bool = False) -> None:
        """Gracefully shuts down APScheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=wait)
            self.state["is_running"] = False
            logger.info("APScheduler successfully stopped.")

    def log_event(self, event_msg: str) -> None:
        """Appends timestamped event to scheduler audit log."""
        timestamp = datetime.now(UTC).isoformat()
        log_entry = f"[{timestamp}] {event_msg}"
        with self._lock:
            self.state["audit_logs"].append(log_entry)
            if len(self.state["audit_logs"]) > 50:
                self.state["audit_logs"].pop(0)
        logger.info(event_msg)

    async def run_drift_check(self, window_size: int = 100) -> dict[str, Any]:
        """
        Executes drift evaluation against recent production predictions.
        If PSI exceeds threshold, flags retraining recommended and triggers training pipeline.
        """
        now_iso = datetime.now(UTC).isoformat()
        self.log_event("[Scheduler] Starting scheduled production drift evaluation...")

        # 1. Fetch recent records from database
        try:
            with SessionLocal() as db:
                records = db.query(PredictionRecord).order_by(desc(PredictionRecord.timestamp)).limit(window_size).all()
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
            self._sync_state_to_redis()

            # Trigger training pipeline in background thread to avoid blocking event loop
            threading.Thread(target=self._execute_retraining_pipeline, daemon=True).start()

            return {
                "status": "DRIFT_DETECTED",
                "retraining_recommended": True,
                "max_psi": max_psi,
                "drifted_features": drift_report.get("drifted_features", []),
                "action": "candidate_retraining_triggered",
            }
        else:
            self.log_event(f"[Scheduler] Drift check passed. Population distribution stable (max PSI = {max_psi:.4f}).")
            with self._lock:
                self.state["retraining_recommended"] = False
                self.state["last_retrain_status"] = "STABLE"
            self._sync_state_to_redis()

            return {
                "status": "HEALTHY",
                "retraining_recommended": False,
                "max_psi": max_psi,
                "message": "Distribution healthy. No retraining necessary.",
            }

    def _execute_retraining_pipeline(self) -> None:
        """Executes ml/train.py to generate a candidate model without auto-promoting."""
        if not acquire_distributed_lock("pms:lock:retrain", ttl_seconds=1800):
            logger.warning("[Scheduler Retrain] Redis retrain lock already held by another worker. Skipping.")
            return
        train_script = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "ml",
            "train.py",
        )
        lock_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".retrain.lock")
        # Multi-worker concurrency guard: prevent simultaneous retraining across multiple Uvicorn workers
        if os.path.exists(lock_file):
            try:
                mtime = os.path.getmtime(lock_file)
                if time.time() - mtime < 1800:
                    logger.warning(
                        "[Scheduler Retrain] Retraining already in progress in another worker process. Skipping redundant trigger."
                    )
                    return
            except Exception:
                pass

        try:
            with open(lock_file, "w") as f:
                f.write(f"pid={os.getpid()}\ntimestamp={time.time()}\n")
            logger.info("[Scheduler Retrain] Executing ml/train.py...")
            result = subprocess.run(
                [sys.executable, train_script],
                capture_output=True,
                text=True,
                check=True,
            )
            logger.info(f"[Scheduler Retrain] Completed successfully. Summary: {result.stdout[-300:].strip()}")
            with self._lock:
                self.state["last_retrain_timestamp"] = datetime.now(UTC).isoformat()
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
        finally:
            if os.path.exists(lock_file):
                try:
                    os.remove(lock_file)
                except Exception:
                    pass

    def get_status(self) -> dict[str, Any]:
        """Returns scheduler state and scheduled job details (merging shared Redis state if present)."""
        remote = cache_get_json(SCHEDULER_STATE_KEY)
        with self._lock:
            merged = (
                {**remote, **self.state}
                if isinstance(remote, dict) and not self.state.get("last_check_timestamp")
                else dict(self.state)
            )
            if isinstance(remote, dict) and remote.get("last_check_timestamp"):
                if not merged.get("last_check_timestamp") or str(remote["last_check_timestamp"]) > str(
                    merged["last_check_timestamp"]
                ):
                    merged.update(remote)
            jobs_info = []
            for j in self.scheduler.get_jobs():
                jobs_info.append(
                    {
                        "id": j.id,
                        "name": j.name,
                        "next_run_time": (j.next_run_time.isoformat() if j.next_run_time else None),
                    }
                )
            return {**merged, "active_jobs": jobs_info}


drift_scheduler = DriftScheduler()
