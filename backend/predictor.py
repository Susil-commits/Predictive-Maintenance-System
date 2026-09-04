import os
import json
import joblib
import numpy as np
import pandas as pd
import shap

ML_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ml")
MODEL_PATH = os.path.join(ML_DIR, "model.pkl")
INFO_PATH = os.path.join(ML_DIR, "model_info.json")

class MaintenancePredictor:
    def __init__(self):
        self.model = None
        self.explainer = None
        self.metadata = {}
        self.version = "1.0.0"
        self.mlflow_run_id = None
        self.feature_names = [
            'temperature',
            'rpm',
            'pressure',
            'vibration',
            'operating_hours',
            'temp_pressure_index',
            'vibration_wear_index',
            'rpm_vibration_ratio'
        ]
        self.load_model()

    def load_model(self):
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Model file not found at {MODEL_PATH}. Please run ml/train.py first.")
        
        print(f"Loading model from {MODEL_PATH}...")
        self.model = joblib.load(MODEL_PATH)
        
        if os.path.exists(INFO_PATH):
            with open(INFO_PATH, "r") as f:
                self.metadata = json.load(f)
                if "feature_names" in self.metadata:
                    self.feature_names = self.metadata["feature_names"]
                self.version = self.metadata.get("version", "1.0.0")
                self.mlflow_run_id = self.metadata.get("mlflow_run_id")
                    
        # Initialize SHAP explainer for the tree-based model
        self.explainer = shap.TreeExplainer(self.model)
        print(f"Model ({self.version}) and SHAP explainer successfully loaded.")

    def engineer_features(self, input_dict: dict) -> pd.DataFrame:
        df = pd.DataFrame([input_dict])
        df['temp_pressure_index'] = (df['temperature'] * df['pressure']) / 100.0
        df['vibration_wear_index'] = df['vibration'] * (df['operating_hours'] / 1000.0)
        df['rpm_vibration_ratio'] = (df['rpm'] * df['vibration']) / 1000.0
        return df[self.feature_names]

    def predict(self, input_dict: dict) -> dict:
        if self.model is None:
            self.load_model()

        X = self.engineer_features(input_dict)
        probabilities = self.model.predict_proba(X)[0]
        # Probability of class 1 (Failure Risk)
        failure_prob = float(probabilities[1])
        
        # Risk thresholding
        risk = "HIGH" if failure_prob >= 0.50 else "LOW"
        maintenance_required = failure_prob >= 0.50

        # SHAP calculation for single instance
        shap_raw = self.explainer.shap_values(X)[0]
        
        # Map raw SHAP values to clean dict
        shap_dict = {}
        for feat, val in zip(self.feature_names, shap_raw):
            shap_dict[feat] = round(float(val), 4)

        # Aggregate interaction features back to primary factors for clean UI explanation
        # User requested factors: Vibration, Temperature, Pressure, RPM, Operating Hours
        factor_scores = {
            "Vibration": shap_dict.get("vibration", 0.0) + 0.6 * shap_dict.get("vibration_wear_index", 0.0) + 0.5 * shap_dict.get("rpm_vibration_ratio", 0.0),
            "Temperature": shap_dict.get("temperature", 0.0) + 0.5 * shap_dict.get("temp_pressure_index", 0.0),
            "Pressure": shap_dict.get("pressure", 0.0) + 0.5 * shap_dict.get("temp_pressure_index", 0.0),
            "RPM": shap_dict.get("rpm", 0.0) + 0.5 * shap_dict.get("rpm_vibration_ratio", 0.0),
            "Operating Hours": shap_dict.get("operating_hours", 0.0) + 0.4 * shap_dict.get("vibration_wear_index", 0.0)
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
                "impact": round(float(score), 4),
                "importance": round(abs(float(score)), 4),
                "description": factor_descriptions.get(factor_name, "")
            })

        return {
            "failure_risk": risk,
            "probability": round(failure_prob, 4),
            "maintenance_required": maintenance_required,
            "contributing_factors": contributing_factors,
            "shap_values": shap_dict,
            "model_version": self.version
        }

# Global singleton
predictor = MaintenancePredictor()
