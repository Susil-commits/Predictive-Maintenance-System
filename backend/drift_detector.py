import os
import json
import logging
from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

ML_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ml")
REFERENCE_STATS_PATH = os.path.join(ML_DIR, "reference_stats.json")

class DriftDetector:
    """
    Detects data and feature distribution drift between the training baseline
    and live production predictions using the Population Stability Index (PSI).

    PSI Thresholds:
      - PSI < 0.10: Stable (No Drift)
      - 0.10 <= PSI < 0.25: Moderate shift / Warning
      - PSI >= 0.25: Significant Drift (Retraining recommended)
    """

    FEATURE_NAMES = [
        "temperature",
        "rpm",
        "pressure",
        "vibration",
        "operating_hours"
    ]

    def __init__(self, stats_path: str = REFERENCE_STATS_PATH):
        self.stats_path = stats_path
        self.reference_stats: Dict[str, Any] = {}
        self.load_reference_stats()

    def load_reference_stats(self) -> bool:
        if os.path.exists(self.stats_path):
            try:
                with open(self.stats_path, "r") as f:
                    self.reference_stats = json.load(f)
                return True
            except Exception as e:
                logger.error(f"Error loading reference stats from {self.stats_path}: {e}")
                self.reference_stats = {}
                return False
        return False

    def calculate_feature_psi(self, feature_name: str, current_values: List[float]) -> Dict[str, Any]:
        """
        Calculates Population Stability Index (PSI) for a given numeric feature.
        """
        feat_ref = self.reference_stats.get("features", {}).get(feature_name)
        if not feat_ref or not current_values:
            return {
                "feature": feature_name,
                "psi": 0.0,
                "status": "NO_BASELINE",
                "severity": "LOW",
                "reference_mean": None,
                "production_mean": float(np.mean(current_values)) if current_values else None,
                "message": "Baseline statistics not available for this feature"
            }

        bin_edges = np.array(feat_ref.get("bin_edges", []))
        expected_pct = np.array(feat_ref.get("expected_pct", []))
        ref_mean = feat_ref.get("mean", 0.0)

        curr_arr = np.array(current_values, dtype=float)
        prod_mean = float(np.mean(curr_arr))

        if len(bin_edges) < 2 or len(expected_pct) == 0:
            return {
                "feature": feature_name,
                "psi": 0.0,
                "status": "INVALID_BINS",
                "severity": "LOW",
                "reference_mean": ref_mean,
                "production_mean": prod_mean
            }

        # Histogram counting into defined reference bins
        # Extend edge bounds slightly to catch out-of-range values in outer bins
        adjusted_edges = bin_edges.copy()
        adjusted_edges[0] = -np.inf
        adjusted_edges[-1] = np.inf

        counts, _ = np.histogram(curr_arr, bins=adjusted_edges)
        total_curr = len(curr_arr)

        actual_pct = counts / max(total_curr, 1)

        # Smooth to prevent zero divisions and log(0)
        epsilon = 1e-4
        actual_pct = np.where(actual_pct == 0, epsilon, actual_pct)
        expected_pct = np.where(expected_pct == 0, epsilon, expected_pct)

        # Re-normalize
        actual_pct = actual_pct / np.sum(actual_pct)
        expected_pct = expected_pct / np.sum(expected_pct)

        # PSI Formula: sum((Actual - Expected) * ln(Actual / Expected))
        psi_contributions = (actual_pct - expected_pct) * np.log(actual_pct / expected_pct)
        psi_value = float(np.sum(psi_contributions))

        if psi_value < 0.10:
            status = "NO_DRIFT"
            severity = "LOW"
        elif psi_value < 0.25:
            status = "MODERATE_DRIFT"
            severity = "MEDIUM"
        else:
            status = "SIGNIFICANT_DRIFT"
            severity = "HIGH"

        return {
            "feature": feature_name,
            "psi": round(psi_value, 4),
            "status": status,
            "severity": severity,
            "reference_mean": round(float(ref_mean), 3),
            "production_mean": round(prod_mean, 3),
            "mean_shift": round(prod_mean - float(ref_mean), 3)
        }

    def evaluate_production_data(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Evaluates drift across all features for a list of recent prediction records.
        """
        if not self.reference_stats:
            self.load_reference_stats()

        if not self.reference_stats:
            return {
                "status": "UNCONFIGURED",
                "drift_detected": False,
                "retrain_recommended": False,
                "analyzed_samples": len(records),
                "message": "Reference baseline has not been computed yet. Please run training pipeline.",
                "feature_metrics": []
            }

        min_samples = 5
        if len(records) < min_samples:
            return {
                "status": "INSUFFICIENT_DATA",
                "drift_detected": False,
                "retrain_recommended": False,
                "analyzed_samples": len(records),
                "min_samples_required": min_samples,
                "message": f"Requires at least {min_samples} production records to compute statistical drift (currently {len(records)}).",
                "feature_metrics": []
            }

        # Extract feature arrays from prediction records
        feature_data: Dict[str, List[float]] = {f: [] for f in self.FEATURE_NAMES}
        for r in records:
            inputs = r.get("input_features") or r
            for f in self.FEATURE_NAMES:
                val = inputs.get(f)
                if val is not None:
                    try:
                        feature_data[f].append(float(val))
                    except (ValueError, TypeError):
                        pass

        feature_metrics = []
        max_psi = 0.0
        drifted_features = []

        for f in self.FEATURE_NAMES:
            values = feature_data[f]
            metric = self.calculate_feature_psi(f, values)
            feature_metrics.append(metric)
            if metric["psi"] > max_psi:
                max_psi = metric["psi"]
            if metric["status"] == "SIGNIFICANT_DRIFT":
                drifted_features.append(f)

        drift_detected = len(drifted_features) > 0 or max_psi >= 0.25
        retrain_recommended = drift_detected

        if drift_detected:
            overall_status = "DRIFT_DETECTED"
        elif any(m["status"] == "MODERATE_DRIFT" for m in feature_metrics):
            overall_status = "WARNING"
        else:
            overall_status = "HEALTHY"

        return {
            "status": overall_status,
            "drift_detected": drift_detected,
            "retrain_recommended": retrain_recommended,
            "max_psi": round(max_psi, 4),
            "drifted_features": drifted_features,
            "analyzed_samples": len(records),
            "reference_version": self.reference_stats.get("model_version", "1.0.0"),
            "feature_metrics": feature_metrics
        }

# Global instance
drift_detector = DriftDetector()
