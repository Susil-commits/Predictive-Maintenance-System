from typing import Any

from pydantic import BaseModel, Field


class PredictionInput(BaseModel):
    temperature: float = Field(
        ...,
        ge=-20.0,
        le=250.0,
        description="Operating temperature in Celsius (°C)",
        json_schema_extra={"example": 92.4},
    )
    rpm: float = Field(
        ...,
        ge=100.0,
        le=6000.0,
        description="Rotational speed in RPM",
        json_schema_extra={"example": 2800},
    )
    pressure: float = Field(
        ...,
        ge=1.0,
        le=100.0,
        description="Hydraulic / operating pressure in bar",
        json_schema_extra={"example": 31.5},
    )
    vibration: float = Field(
        ...,
        ge=0.01,
        le=5.0,
        description="Vibration amplitude in g / mm/s",
        json_schema_extra={"example": 0.64},
    )
    operating_hours: float = Field(
        ...,
        ge=0.0,
        le=50000.0,
        description="Cumulative equipment operating hours",
        json_schema_extra={"example": 4820},
    )


class ContributingFactor(BaseModel):
    factor: str
    impact: float
    importance: float
    description: str


class PredictionOutput(BaseModel):
    failure_risk: str = Field(..., description="'HIGH' or 'LOW'", json_schema_extra={"example": "HIGH"})
    probability: float = Field(
        ...,
        description="Failure probability [0.0 - 1.0]",
        json_schema_extra={"example": 0.87},
    )
    maintenance_required: bool = Field(
        ...,
        description="Whether maintenance is immediately recommended",
        json_schema_extra={"example": True},
    )
    confidence: str | None = Field(
        None,
        description="Prediction certainty ('HIGH' or 'LOW')",
        json_schema_extra={"example": "HIGH"},
    )
    recommendation: str | None = Field(
        None,
        description="Actionable recommendation based on risk and uncertainty",
        json_schema_extra={"example": "🔴 HIGH RISK — Schedule maintenance"},
    )
    contributing_factors: list[ContributingFactor] = []
    shap_values: dict[str, float] = {}
    top_risk_factor: str | None = Field(
        None,
        description="The single feature contributing most to this risk score",
        json_schema_extra={"example": "vibration"},
    )
    contribution_pct: float | None = Field(
        None,
        description="Percentage of total risk attributable to top_risk_factor",
        json_schema_extra={"example": 42.5},
    )
    suggested_action: str | None = Field(
        None,
        description="Human-readable recommended action based on root cause",
        json_schema_extra={"example": "Vibration is elevated above baseline — recommend vibration analysis."},
    )
    prediction_id: str | None = None
    timestamp: str | None = None
    model_version: str | None = None
    decision_threshold: float | None = Field(
        None,
        description="Optimal decision threshold tuned via Precision-Recall curve",
        json_schema_extra={"example": 0.84},
    )


class CounterfactualOutput(BaseModel):
    already_safe: bool = Field(
        ...,
        description="Whether equipment telemetry is already below the risk threshold",
        json_schema_extra={"example": False},
    )
    feature_to_change: str | None = Field(
        None,
        description="Primary parameter identified for intervention",
        json_schema_extra={"example": "vibration"},
    )
    current_value: float | None = Field(
        None,
        description="Current telemetry reading",
        json_schema_extra={"example": 0.65},
    )
    target_value: float | None = Field(
        None,
        description="Target reading required to remediate risk",
        json_schema_extra={"example": 0.52},
    )
    reduction_needed_pct: int | None = Field(
        None,
        description="Percentage reduction required",
        json_schema_extra={"example": 20},
    )
    risk_before: float | None = Field(
        None,
        description="Risk percentage before remediation",
        json_schema_extra={"example": 41.3},
    )
    risk_after: float | None = Field(
        None,
        description="Risk percentage after remediation",
        json_schema_extra={"example": 20.4},
    )
    note: str | None = Field(
        None,
        description="Actionable note or operational guidance",
        json_schema_extra={"example": "Reducing vibration by 20% restores safe operating status."},
    )


class RULReadingInput(BaseModel):
    temperature: float = Field(..., description="Temperature in °C")
    rpm: float = Field(..., description="Rotational speed")
    pressure: float = Field(..., description="Pressure in bar")
    vibration: float = Field(..., description="Vibration amplitude in g")
    operating_hours: float | None = Field(None, description="Operating hours")
    cycle: int | None = Field(None, description="Cycle index")
    timestamp: str | None = Field(None, description="Reading timestamp")


class RULOutput(BaseModel):
    estimated_rul_cycles: int = Field(..., description="Estimated remaining cycles before failure")
    estimated_rul_hours: float = Field(..., description="Estimated remaining operating hours")
    confidence: float = Field(..., description="Model confidence score [0.0 - 1.0]")
    recommendation: str = Field(..., description="Operational recommendation based on RUL")


class ModelInfoResponse(BaseModel):
    model_name: str
    version: str
    calibration: dict[str, Any] | None = None
    mlflow_run_id: str | None = None
    mlflow_experiment: str | None = None
    trained_date: str
    dataset_source: str
    total_training_samples: int
    total_test_samples: int
    decision_threshold: float | None = None
    metrics: dict[str, Any]
    feature_names: list[str]
    base_features: list[str]
    segmented_performance: dict[str, Any] | None = None
    cv_failure_mode_performance: dict[str, Any] | None = None
    stratified_5fold_cv_per_mode: dict[str, Any] | None = None
    scenario_validation: dict[str, Any] | None = None


class HealthResponse(BaseModel):
    status: str
    database: str
    model_loaded: bool
    model_version: str | None = None


class FeatureDriftMetric(BaseModel):
    feature: str
    psi: float
    status: str
    severity: str
    reference_mean: float | None = None
    production_mean: float | None = None
    mean_shift: float | None = None
    message: str | None = None


class DriftStatusResponse(BaseModel):
    status: str
    drift_detected: bool
    retrain_recommended: bool
    max_psi: float | None = None
    drifted_features: list[str] = []
    analyzed_samples: int
    reference_version: str | None = None
    message: str | None = None
    feature_metrics: list[FeatureDriftMetric] = []


class RetrievedSourceChunk(BaseModel):
    failure_mode: str = Field(
        ...,
        description="Failure mode category (Thermal, Overstrain, Tool Wear, Power, Vibration)",
    )
    title: str = Field(..., description="Document title of the standard operating procedure")
    section: str = Field(
        ...,
        description="Specific procedure section (e.g. Diagnostic Protocol, Remediation)",
    )
    content: str = Field(..., description="Verifiable industrial procedure text chunk")
    relevance_score: float | None = Field(None, description="Retrieval similarity score / distance")


class NarrationOutput(PredictionOutput):
    narrative: str = Field(
        ...,
        description="Fluent, context-specific LLM narration strictly grounded in the prediction and retrieved procedures",
    )
    retrieved_sources: list[RetrievedSourceChunk] = Field(
        default_factory=list,
        description="Auditable procedure source chunks grounding the recommendation",
    )
    counterfactual: CounterfactualOutput | None = Field(
        None,
        description="Counterfactual minimal-fix remediation analysis if requested or computed",
    )
