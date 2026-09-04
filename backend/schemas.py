from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class PredictionInput(BaseModel):
    temperature: float = Field(..., description="Operating temperature in Celsius (°C)", json_schema_extra={"example": 92.4})
    rpm: float = Field(..., description="Rotational speed in RPM", json_schema_extra={"example": 2800})
    pressure: float = Field(..., description="Hydraulic / operating pressure in bar", json_schema_extra={"example": 31.5})
    vibration: float = Field(..., description="Vibration amplitude in g / mm/s", json_schema_extra={"example": 0.64})
    operating_hours: float = Field(..., description="Cumulative equipment operating hours", json_schema_extra={"example": 4820})

class ContributingFactor(BaseModel):
    factor: str
    impact: float
    importance: float
    description: str

class PredictionOutput(BaseModel):
    failure_risk: str = Field(..., description="'HIGH' or 'LOW'", json_schema_extra={"example": "HIGH"})
    probability: float = Field(..., description="Failure probability [0.0 - 1.0]", json_schema_extra={"example": 0.87})
    maintenance_required: bool = Field(..., description="Whether maintenance is immediately recommended", json_schema_extra={"example": True})
    contributing_factors: List[ContributingFactor] = []
    shap_values: Dict[str, float] = {}
    prediction_id: Optional[str] = None
    timestamp: Optional[str] = None
    model_version: Optional[str] = None

class ModelInfoResponse(BaseModel):
    model_name: str
    version: str
    mlflow_run_id: Optional[str] = None
    mlflow_experiment: Optional[str] = None
    trained_date: str
    dataset_source: str
    total_training_samples: int
    total_test_samples: int
    metrics: Dict[str, Any]
    feature_names: List[str]
    base_features: List[str]

class HealthResponse(BaseModel):
    status: str
    database: str
    model_loaded: bool
    model_version: Optional[str] = None

class FeatureDriftMetric(BaseModel):
    feature: str
    psi: float
    status: str
    severity: str
    reference_mean: Optional[float] = None
    production_mean: Optional[float] = None
    mean_shift: Optional[float] = None
    message: Optional[str] = None

class DriftStatusResponse(BaseModel):
    status: str
    drift_detected: bool
    retrain_recommended: bool
    max_psi: Optional[float] = None
    drifted_features: List[str] = []
    analyzed_samples: int
    reference_version: Optional[str] = None
    message: Optional[str] = None
    feature_metrics: List[FeatureDriftMetric] = []
