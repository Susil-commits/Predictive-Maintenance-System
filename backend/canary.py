"""
Canary Rollout Manager for PMS.
Validates newly retrained candidate models by executing side-by-side dual-scoring
for the first 50 live inference requests before safely promoting to production.
"""

import os
import json
import logging
import threading
from typing import Dict, Any, Optional, List
import numpy as np
import joblib

from .logging_config import get_request_id

logger = logging.getLogger("pms.canary")

ML_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ml")
PRIMARY_MODEL_PATH = os.path.join(ML_DIR, "model.pkl")
INFO_PATH = os.path.join(ML_DIR, "model_info.json")

class CanaryManager:
    """Manages dual-model shadow evaluation and canary rollouts."""
    def __init__(self):
        self._lock = threading.Lock()
        self.is_active: bool = False
        self.primary_version: str = "v1"
        self.canary_version: str = "v2"
        self.canary_model: Any = None
        self.canary_threshold: float = 0.50
        
        self.evaluation_window: int = 50
        self.remaining_requests: int = 50
        self.evaluated_requests: int = 0
        self.agreements: int = 0
        self.disagreements: int = 0
        
        self.side_by_side_logs: List[Dict[str, Any]] = []
        self.ready_for_promotion: bool = False
        self.auto_switch_completed: bool = False

    def start_canary(
        self,
        candidate_model_path: Optional[str] = None,
        candidate_version: Optional[str] = None,
        candidate_threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Activates canary rollout mode for the next 50 incoming requests.
        Loads the candidate model into memory alongside the primary model.
        """
        model_path = candidate_model_path or PRIMARY_MODEL_PATH
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Candidate model not found at {model_path}")

        try:
            loaded_model = joblib.load(model_path)
        except Exception as e:
            raise RuntimeError(f"Failed to load canary candidate model: {e}")

        # Read version metadata
        version = candidate_version or "candidate"
        threshold = candidate_threshold if candidate_threshold is not None else 0.22
        if os.path.exists(INFO_PATH):
            try:
                with open(INFO_PATH, "r") as f:
                    meta = json.load(f)
                    version = candidate_version or meta.get("version", "candidate")
                    threshold = candidate_threshold or float(meta.get("decision_threshold", 0.22))
            except Exception:
                pass

        with self._lock:
            self.canary_model = loaded_model
            self.canary_version = version
            self.canary_threshold = threshold
            self.is_active = True
            self.evaluation_window = 50
            self.remaining_requests = 50
            self.evaluated_requests = 0
            self.agreements = 0
            self.disagreements = 0
            self.side_by_side_logs.clear()
            self.ready_for_promotion = False
            self.auto_switch_completed = False

        logger.info(
            f"[CANARY ACTIVATED] Starting 50-request shadow evaluation for Candidate ({self.canary_version}) "
            f"vs Primary ({self.primary_version})."
        )
        return self.get_status()

    def evaluate_request(
        self,
        features_df: Any,
        primary_result: Dict[str, Any],
        request_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Scores input with canary model in shadow mode and logs side-by-side comparison.
        """
        if not self.is_active or self.canary_model is None or self.remaining_requests <= 0:
            return None

        req_id = request_id or get_request_id()

        try:
            # Score with canary model
            probabilities = self.canary_model.predict_proba(features_df)[0]
            canary_prob = float(probabilities[1])
            canary_risk = "HIGH" if canary_prob >= self.canary_threshold else "LOW"
            primary_risk = primary_result.get("failure_risk", "UNKNOWN")
            primary_prob = float(primary_result.get("probability", 0.0))

            is_match = (primary_risk == canary_risk)
            prob_delta = round(canary_prob - primary_prob, 4)

            with self._lock:
                self.evaluated_requests += 1
                self.remaining_requests -= 1
                if is_match:
                    self.agreements += 1
                else:
                    self.disagreements += 1

                log_entry = {
                    "request_id": req_id,
                    "index": self.evaluated_requests,
                    "primary": {
                        "version": self.primary_version,
                        "risk": primary_risk,
                        "probability": round(primary_prob, 4)
                    },
                    "canary": {
                        "version": self.canary_version,
                        "risk": canary_risk,
                        "probability": round(canary_prob, 4)
                    },
                    "agreement": is_match,
                    "probability_delta": prob_delta,
                    "remaining": self.remaining_requests
                }
                self.side_by_side_logs.append(log_entry)
                if len(self.side_by_side_logs) > 50:
                    self.side_by_side_logs.pop(0)

                if self.remaining_requests == 0:
                    self.ready_for_promotion = True

            logger.info(
                f"[CANARY EVALUATION req_id={req_id}] "
                f"Primary ({self.primary_version}): risk={primary_risk} (p={primary_prob:.4f}) vs "
                f"Canary ({self.canary_version}): risk={canary_risk} (p={canary_prob:.4f}) | "
                f"Agreement={is_match} (Delta: {prob_delta:+.4f}) | Remaining: {self.remaining_requests}/50"
            )

            if self.remaining_requests == 0:
                agreement_rate = (self.agreements / max(1, self.evaluated_requests)) * 100.0
                logger.info(
                    f"[CANARY EVALUATION COMPLETE] 50 requests finished. "
                    f"Overall Agreement Rate: {agreement_rate:.1f}%. Candidate is ready for full promotion."
                )

            return log_entry
        except Exception as err:
            logger.warning(f"[CANARY ERROR] Failed to evaluate shadow prediction: {err}")
            return None

    def promote_canary(self) -> Dict[str, Any]:
        """Promotes canary model to primary production model."""
        with self._lock:
            if not self.is_active or self.canary_model is None:
                return {"status": "ERROR", "message": "No active canary rollout to promote"}

            self.primary_version = self.canary_version
            self.is_active = False
            self.auto_switch_completed = True
            logger.info(f"[CANARY PROMOTED] Successfully promoted {self.canary_version} to active production primary model.")
            return {
                "status": "PROMOTED",
                "new_primary_version": self.primary_version,
                "total_shadow_evaluated": self.evaluated_requests,
                "final_agreement_rate": round(self.agreements / max(1, self.evaluated_requests), 4)
            }

    def abort_canary(self) -> Dict[str, Any]:
        """Aborts canary rollout and unloads candidate model."""
        with self._lock:
            self.is_active = False
            self.canary_model = None
            logger.warning("[CANARY ABORTED] Canary rollout aborted. Reverting exclusively to primary model.")
            return {
                "status": "ABORTED",
                "active_primary_version": self.primary_version
            }

    def get_status(self) -> Dict[str, Any]:
        """Returns current canary state and progress."""
        with self._lock:
            rate = round(self.agreements / max(1, self.evaluated_requests), 4) if self.evaluated_requests > 0 else 1.0
            return {
                "is_active": self.is_active,
                "primary_version": self.primary_version,
                "canary_version": self.canary_version,
                "evaluated_requests": self.evaluated_requests,
                "remaining_requests": self.remaining_requests,
                "agreements": self.agreements,
                "disagreements": self.disagreements,
                "agreement_rate": rate,
                "ready_for_promotion": self.ready_for_promotion,
                "auto_switch_completed": self.auto_switch_completed,
                "recent_evaluations": self.side_by_side_logs[-10:]
            }

canary_manager = CanaryManager()
