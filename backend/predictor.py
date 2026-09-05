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
            'mechanical_power'
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
                0.5 * shap_dict.get("overstrain_index", 0.0)
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

        return {
            "failure_risk": risk,
            "probability": round(failure_prob, 4),
            "maintenance_required": maintenance_required,
            "contributing_factors": contributing_factors,
            "shap_values": shap_dict,
            "model_version": self.version,
            "decision_threshold": round(active_threshold, 4)
        }

# Global singleton
predictor = MaintenancePredictor()
