from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class PredictionInput(BaseModel):
    temperature: float = Field(..., description="Operating temperature in Celsius (°C)", example=92.4)
    rpm: float = Field(..., description="Rotational speed in RPM", example=2800)
    pressure: float = Field(..., description="Hydraulic / operating pressure in bar", example=31.5)
    vibration: float = Field(..., description="Vibration amplitude in g / mm/s", example=0.64)
    operating_hours: float = Field(..., description="Cumulative equipment operating hours", example=4820)

class ContributingFactor(BaseModel):
    factor: str
    impact: float
    importance: float
    description: str

class PredictionOutput(BaseModel):
    failure_risk: str = Field(..., description="'HIGH' or 'LOW'", example="HIGH")
    probability: float = Field(..., description="Failure probability [0.0 - 1.0]", example=0.87)
    maintenance_required: bool = Field(..., description="Whether maintenance is immediately recommended", example=True)
    contributing_factors: List[ContributingFactor] = []
    shap_values: Dict[str, float] = {}
    prediction_id: Optional[str] = None
    timestamp: Optional[str] = None

class ModelInfoResponse(BaseModel):
    model_name: str
    version: str
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
