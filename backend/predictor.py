import os
import json
import logging
from typing import Optional, Dict, Any, List
import joblib
import numpy as np
import pandas as pd
import shap

logger = logging.getLogger("pms.predictor")

ML_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ml")
MODEL_PATH = os.path.join(ML_DIR, "model.pkl")
INFO_PATH = os.path.join(ML_DIR, "model_info.json")

FEATURE_GUIDANCE = {
    "temperature": {
        "high": "Temperature is elevated above baseline — inspect cooling system, check coolant levels, verify airflow around heat exchangers.",
        "low": "Temperature reading is unusually low — verify sensor calibration."
    },
    "vibration": {
        "high": "Vibration is elevated above baseline — likely bearing wear, misalignment, or imbalance. Recommend vibration analysis and bearing inspection.",
        "low": "Vibration reading is unusually low — verify sensor is functioning."
    },
    "pressure": {
        "high": "Pressure is above normal range — check for blockages or valve malfunction downstream.",
        "low": "Pressure is below normal range — check for leaks or pump degradation."
    },
    "rpm": {
        "high": "Rotational speed is elevated — verify load conditions match expected operating profile.",
        "low": "Rotational speed is below expected range — check drive system and load coupling."
    },
    "operating_hours": {
        "high": "Equipment has accumulated significant operating hours — schedule preventive maintenance per manufacturer service interval.",
        "low": None  # not typically a risk driver on its own
    }
}

def generate_root_cause_guidance(shap_values: dict, feature_values: Optional[dict] = None) -> dict:
    """
    shap_values: {feature_name: shap_contribution} for this single prediction
    feature_values: {feature_name: raw_value} for this single prediction
    Returns the top contributing factor + a human-readable suggested action.
    """
    if not shap_values:
        return {"top_risk_factor": None, "contribution_pct": None, "suggested_action": None}

    # Normalize engineered/interaction feature names to base physical driver
    feature_to_base = {
        "temp_pressure_index": "temperature",
        "thermal_excess": "temperature",
        "vibration_wear_index": "vibration",
        "rpm_vibration_ratio": "vibration",
        "overstrain_index": "pressure",
        "mechanical_power": "rpm",
        "vib_dominant_freq": "vibration",
        "vib_spectral_energy_low": "vibration",
        "vib_spectral_energy_high": "vibration",
        "vib_spectral_centroid": "vibration",
        "operating hours": "operating_hours",
        "vibration": "vibration",
        "temperature": "temperature",
        "pressure": "pressure",
        "rpm": "rpm",
        "operating_hours": "operating_hours"
    }

    # Aggregate contributions into 5 base physical drivers
    aggregated_shap: Dict[str, float] = {}
    for feat, val in shap_values.items():
        base = feature_to_base.get(feat.lower().strip(), feat.lower().strip())
        aggregated_shap[base] = aggregated_shap.get(base, 0.0) + float(val)

    total_abs = sum(abs(v) for v in aggregated_shap.values())

    # Sort by absolute SHAP contribution, descending
    sorted_features = sorted(aggregated_shap.items(), key=lambda x: abs(x[1]), reverse=True)
    top_feature, top_contribution = sorted_features[0]

    direction = "high" if top_contribution >= 0 else "low"
    guidance = FEATURE_GUIDANCE.get(top_feature, {}).get(direction)

    pct = round(abs(top_contribution) / total_abs * 100, 1) if total_abs > 0 else 0.0

    return {
        "top_risk_factor": top_feature,
        "contribution_pct": pct,
        "suggested_action": guidance or f"{top_feature.replace('_', ' ').capitalize()} is the dominant risk driver — recommend manual inspection."
    }

class MaintenancePredictor:
    def __init__(self):
        self.model = None
        self.explainer = None
        self.metadata = {}
        self.version = "1.0.0"
        self.threshold = 0.50
        self.mlflow_run_id = None
        self.feature_names = [
            'temperature',
            'rpm',
            'pressure',
            'vibration',
            'operating_hours',
            'temp_pressure_index',
            'vibration_wear_index',
            'rpm_vibration_ratio',
            'thermal_excess',
            'overstrain_index',
            'mechanical_power',
            'vib_dominant_freq',
            'vib_spectral_energy_low',
            'vib_spectral_energy_high',
            'vib_spectral_centroid'
        ]
        self.load_model()

    def load_model(self):
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Model file not found at {MODEL_PATH}. Please run ml/train.py first.")
        
        logger.info(f"Loading model from {MODEL_PATH}...")
        self.model = joblib.load(MODEL_PATH)
        
        if os.path.exists(INFO_PATH):
            with open(INFO_PATH, "r") as f:
                self.metadata = json.load(f)
                if "feature_names" in self.metadata:
                    self.feature_names = self.metadata["feature_names"]
                self.version = self.metadata.get("version", "1.0.0")
                self.mlflow_run_id = self.metadata.get("mlflow_run_id")
                self.threshold = float(self.metadata.get("decision_threshold", 0.50))
                    
        # Initialize SHAP explainer for the tree-based model (extract base estimator if calibrated)
        tree_model = self.model
        if hasattr(self.model, "calibrated_classifiers_") and self.model.calibrated_classifiers_:
            tree_model = self.model.calibrated_classifiers_[0].estimator
        elif hasattr(self.model, "estimator"):
            tree_model = self.model.estimator

        self.explainer = shap.TreeExplainer(tree_model)
        logger.info(f"Model ({self.version}) and SHAP explainer successfully loaded (Decision Threshold: {self.threshold:.4f}).")

    def engineer_features(self, input_dict: dict) -> pd.DataFrame:
        df = pd.DataFrame([input_dict])
        df['temp_pressure_index'] = (df['temperature'] * df['pressure']) / 100.0
        df['vibration_wear_index'] = df['vibration'] * (df['operating_hours'] / 1000.0)
        df['rpm_vibration_ratio'] = (df['rpm'] * df['vibration']) / 1000.0
        df['thermal_excess'] = (df['temperature'] - 86.0).clip(lower=0.0)
        df['overstrain_index'] = (df['pressure'] / 25.0) * (df['vibration'] - 0.35).clip(lower=0.0)
        df['mechanical_power'] = (df['rpm'] * df['pressure']) / 1000.0

        # Frequency-domain vibration feature extraction via scipy.fft
        if "raw_waveform" in input_dict and isinstance(input_dict["raw_waveform"], (list, np.ndarray)) and len(input_dict["raw_waveform"]) >= 64:
            from scipy.fft import rfft, rfftfreq
            sig = np.asarray(input_dict["raw_waveform"], dtype=float)
            fs = float(input_dict.get("sampling_rate", 2048.0))
            N = len(sig)
            freqs = rfftfreq(N, 1.0 / fs)
            pwr = np.abs(rfft(sig)) ** 2 / float(N)
            dom_idx = int(np.argmax(pwr[1:]) + 1) if len(pwr) > 1 else 0
            df['vib_dominant_freq'] = float(freqs[dom_idx])
            df['vib_spectral_energy_low'] = float(np.sum(pwr[(freqs >= 10.0) & (freqs <= 100.0)]))
            df['vib_spectral_energy_high'] = float(np.sum(pwr[(freqs >= 300.0) & (freqs <= 1000.0)]))
            tot_pwr = float(np.sum(pwr)) + 1e-8
            df['vib_spectral_centroid'] = float(np.sum(pwr * freqs) / tot_pwr)
        else:
            from scipy.fft import rfft, rfftfreq
            rpm_val = float(df['rpm'].iloc[0])
            vib_val = float(df['vibration'].iloc[0])
            press_val = float(df['pressure'].iloc[0])
            hours_val = float(df['operating_hours'].iloc[0])

            fs, N = 2048, 512
            f0 = max(10.0, rpm_val / 60.0)
            t = np.arange(N) / float(fs)
            a1 = vib_val * 0.65
            a2 = vib_val * 0.25 * (press_val / 25.0)
            f_res = 450.0 + min(1.0, hours_val / 6000.0) * 350.0
            a_hf = vib_val * 0.35 * min(1.5, hours_val / 3000.0)

            signal = (a1 * np.sin(2.0 * np.pi * f0 * t) +
                      a2 * np.sin(2.0 * np.pi * 2.0 * f0 * t) +
                      a_hf * np.sin(2.0 * np.pi * f_res * t))
            freqs = rfftfreq(N, 1.0 / fs)
            pwr = np.abs(rfft(signal)) ** 2 / float(N)
            dom_idx = int(np.argmax(pwr[1:]) + 1) if len(pwr) > 1 else 0

            df['vib_dominant_freq'] = round(float(freqs[dom_idx]), 1)
            df['vib_spectral_energy_low'] = round(float(np.sum(pwr[(freqs >= 10.0) & (freqs <= 100.0)])), 2)
            df['vib_spectral_energy_high'] = round(float(np.sum(pwr[(freqs >= 300.0) & (freqs <= 1000.0)])), 2)
            tot_pwr = float(np.sum(pwr)) + 1e-8
            df['vib_spectral_centroid'] = round(float(np.sum(pwr * freqs) / tot_pwr), 1)

        return pd.DataFrame(df[self.feature_names])

    def predict(self, input_dict: dict, threshold: Optional[float] = None) -> dict:
        if self.model is None or self.explainer is None:
            self.load_model()
        if self.model is None or self.explainer is None:
            raise RuntimeError("Model or SHAP explainer failed to load")

        active_threshold = self.threshold if threshold is None else threshold

        X = self.engineer_features(input_dict)
        probabilities = self.model.predict_proba(X)[0]
        # Probability of class 1 (Failure Risk)
        failure_prob = float(probabilities[1])
        
        # Risk thresholding tuned via Precision-Recall curve
        risk = "HIGH" if failure_prob >= active_threshold else "LOW"
        maintenance_required = failure_prob >= active_threshold

        # SHAP calculation for single instance
        shap_raw = self.explainer.shap_values(X)[0]
        
        # Map raw SHAP values to clean dict
        shap_dict = {}
        for feat, val in zip(self.feature_names, shap_raw):
            shap_dict[feat] = round(float(val), 4)

        # Aggregate interaction features back to primary factors for clean UI explanation
        # User requested factors: Vibration, Temperature, Pressure, RPM, Operating Hours
        factor_scores = {
            "Vibration": (
                shap_dict.get("vibration", 0.0) +
                0.6 * shap_dict.get("vibration_wear_index", 0.0) +
                0.5 * shap_dict.get("rpm_vibration_ratio", 0.0) +
                0.5 * shap_dict.get("overstrain_index", 0.0) +
                0.4 * shap_dict.get("vib_dominant_freq", 0.0) +
                0.4 * shap_dict.get("vib_spectral_energy_low", 0.0) +
                0.5 * shap_dict.get("vib_spectral_energy_high", 0.0) +
                0.3 * shap_dict.get("vib_spectral_centroid", 0.0)
            ),
            "Temperature": (
                shap_dict.get("temperature", 0.0) +
                0.5 * shap_dict.get("temp_pressure_index", 0.0) +
                1.0 * shap_dict.get("thermal_excess", 0.0)
            ),
            "Pressure": (
                shap_dict.get("pressure", 0.0) +
                0.5 * shap_dict.get("temp_pressure_index", 0.0) +
                0.5 * shap_dict.get("overstrain_index", 0.0) +
                0.5 * shap_dict.get("mechanical_power", 0.0)
            ),
            "RPM": (
                shap_dict.get("rpm", 0.0) +
                0.5 * shap_dict.get("rpm_vibration_ratio", 0.0) +
                0.5 * shap_dict.get("mechanical_power", 0.0)
            ),
            "Operating Hours": (
                shap_dict.get("operating_hours", 0.0) +
                0.4 * shap_dict.get("vibration_wear_index", 0.0)
            )
        }

        # Human friendly descriptions
        factor_descriptions = {
            "Vibration": "Harmonic oscillation and mechanical instability",
            "Temperature": "Thermal stress on cooling and lubrication circuits",
            "Pressure": "Hydraulic / pneumatic system pressure loading",
            "RPM": "Rotational speed and dynamic rotor stresses",
            "Operating Hours": "Cumulative service wear and fatigue aging"
        }

        # Rank factors by absolute impact
        contributing_factors = []
        for factor_name, score in sorted(factor_scores.items(), key=lambda x: abs(x[1]), reverse=True):
            contributing_factors.append({
                "factor": factor_name,
                "impact": round(score, 4),
                "importance": round(abs(score), 4),
                "description": factor_descriptions.get(factor_name, "")
            })

        # Uncertainty quantification
        if 0.40 <= failure_prob <= 0.60:
            confidence = "LOW"
            recommendation = "⚠️ UNCERTAIN — Recommend manual inspection"
        elif failure_prob < 0.40:
            confidence = "HIGH"
            recommendation = "✓ Operating normally"
        else:
            confidence = "HIGH"
            recommendation = "🔴 HIGH RISK — Schedule maintenance"

        # Root-cause guidance based on SHAP contributions
        root_cause = generate_root_cause_guidance(shap_dict, input_dict)

        return {
            "failure_risk": risk,
            "probability": round(failure_prob, 4),
            "confidence": confidence,
            "recommendation": recommendation,
            "maintenance_required": maintenance_required,
            "contributing_factors": contributing_factors,
            "shap_values": shap_dict,
            "top_risk_factor": root_cause["top_risk_factor"],
            "contribution_pct": root_cause["contribution_pct"],
            "suggested_action": root_cause["suggested_action"],
            "model_version": self.version,
            "decision_threshold": round(active_threshold, 4)
        }

    def predict_with_uncertainty(self, input_dict: dict) -> dict:
        """
        Return risk + uncertainty flag.
        If prediction confidence is ambiguous (0.4-0.6), flag for manual review.
        """
        if self.model is None:
            self.load_model()
        if self.model is None:
            raise RuntimeError("Model failed to load")
        X = self.engineer_features(input_dict)
        prob = float(self.model.predict_proba(X)[0, 1])

        if 0.4 <= prob <= 0.6:
            confidence = "LOW"
            recommendation = "⚠️ UNCERTAIN — Recommend manual inspection"
        elif prob < 0.4:
            confidence = "HIGH"
            recommendation = "✓ Operating normally"
        else:
            confidence = "HIGH"
            recommendation = "🔴 HIGH RISK — Schedule maintenance"

        return {
            "probability": round(prob, 4),
            "confidence": confidence,
            "recommendation": recommendation
        }

# Hardcoded held-out operational scenarios for validation & inference testing (not used in training data)
HELD_OUT_TEST_SCENARIOS = [
    {
        "name": "Target Sample [High-Risk Wear]",
        "inputs": {"temperature": 92.4, "rpm": 2800, "pressure": 31.5, "vibration": 0.64, "operating_hours": 4820},
        "expected": "HIGH"
    },
    {
        "name": "Nominal Baseline [Healthy State]",
        "inputs": {"temperature": 68.0, "rpm": 1500, "pressure": 21.0, "vibration": 0.22, "operating_hours": 950},
        "expected": "LOW"
    },
    {
        "name": "Thermal Overheat [Acute Temperature Failure]",
        "inputs": {"temperature": 97.2, "rpm": 2300, "pressure": 27.8, "vibration": 0.42, "operating_hours": 3100},
        "expected": "HIGH"
    },
    {
        "name": "Vibration & Fatigue [Severe Mechanical Wear]",
        "inputs": {"temperature": 79.5, "rpm": 3100, "pressure": 33.0, "vibration": 0.72, "operating_hours": 5300},
        "expected": "HIGH"
    },
    {
        "name": "Cold Idle Normal [Healthy Low Power]",
        "inputs": {"temperature": 65.0, "rpm": 1200, "pressure": 20.0, "vibration": 0.18, "operating_hours": 500},
        "expected": "LOW"
    },
    {
        "name": "Overstrain Pressure Surge [Heavy Hydraulic Load]",
        "inputs": {"temperature": 85.0, "rpm": 2900, "pressure": 38.0, "vibration": 0.58, "operating_hours": 4200},
        "expected": "HIGH"
    },
    {
        "name": "High Speed Light Load [Highway / Idle Spin]",
        "inputs": {"temperature": 72.0, "rpm": 3200, "pressure": 19.5, "vibration": 0.28, "operating_hours": 1100},
        "expected": "LOW"
    },
    {
        "name": "Low RPM Heavy Strain [Stall / Overload Failure]",
        "inputs": {"temperature": 88.0, "rpm": 1100, "pressure": 39.0, "vibration": 0.70, "operating_hours": 4900},
        "expected": "HIGH"
    },
    {
        "name": "Extreme Breakdown [All High]",
        "inputs": {"temperature": 105.0, "rpm": 3300, "pressure": 42.0, "vibration": 0.95, "operating_hours": 5800},
        "expected": "HIGH"
    }
]

# Global singleton
predictor = MaintenancePredictor()

# Core feature ordering and model handles for counterfactual analysis
FEATURE_ORDER = ['temperature', 'rpm', 'pressure', 'vibration', 'operating_hours']
calibrated_model = predictor.model
scaler = None  # Tree-based pipeline directly consumes engineered features without standard scaler

def find_minimal_fix(
    model: Any = None,
    scaler: Any = None,
    current_features: Optional[dict] = None,
    feature_order: Optional[List[str]] = None,
    threshold: Optional[float] = None
) -> dict:
    """
    Grid-search the top SHAP-driving feature to find the smallest change
    that flips predicted risk below the decision threshold.
    """
    if current_features is None:
        raise ValueError("current_features dictionary is required")

    active_threshold = threshold if threshold is not None else getattr(predictor, "threshold", 0.2288)

    # Get current prediction
    current_pred = predictor.predict(current_features, threshold=active_threshold)
    current_risk = current_pred["probability"]

    if current_risk < active_threshold:
        return {
            "already_safe": True,
            "feature_to_change": None,
            "current_value": None,
            "target_value": None,
            "reduction_needed_pct": None,
            "risk_before": round(current_risk * 100, 1),
            "risk_after": round(current_risk * 100, 1),
            "note": "Telemetry is already within safe operating baseline."
        }

    # Identify top SHAP feature
    root_cause = generate_root_cause_guidance(current_pred.get("shap_values", {}), current_features)
    top_feature_name = root_cause.get("top_risk_factor") or "vibration"

    # Prioritize top feature, then other controllable parameters if top feature cannot flip
    candidate_features = [top_feature_name]
    for feat in ["pressure", "vibration", "temperature", "rpm"]:
        if feat not in candidate_features and feat in current_features:
            candidate_features.append(feat)

    # Grid search: try reducing the feature by 5%, 10%, ..., 50%
    for feat in candidate_features:
        if feat not in current_features or feat == "operating_hours":
            continue
        original_value = float(current_features[feat])
        if original_value <= 0:
            continue

        for pct_reduction in [5, 10, 15, 20, 25, 30, 40, 50]:
            test_features = dict(current_features)
            test_features[feat] = original_value * (1.0 - pct_reduction / 100.0)

            test_pred = predictor.predict(test_features, threshold=active_threshold)
            test_risk = test_pred["probability"]

            if test_risk < active_threshold:
                return {
                    "already_safe": False,
                    "feature_to_change": feat,
                    "current_value": round(original_value, 2),
                    "target_value": round(test_features[feat], 2),
                    "reduction_needed_pct": pct_reduction,
                    "risk_before": round(current_risk * 100, 1),
                    "risk_after": round(test_risk * 100, 1),
                    "note": f"Reducing {feat} by {pct_reduction}% restores safe operating status."
                }

    return {
        "already_safe": False,
        "feature_to_change": top_feature_name,
        "current_value": round(float(current_features.get(top_feature_name, 0.0)), 2),
        "target_value": None,
        "reduction_needed_pct": None,
        "risk_before": round(current_risk * 100, 1),
        "risk_after": None,
        "note": "No single-feature fix within tested range — recommend full inspection."
    }


