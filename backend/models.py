import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Index, Integer, String

from .database import Base


class PredictionRecord(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        Index("ix_predictions_ts_risk", "timestamp", "failure_risk"),
        Index("ix_predictions_risk_prob", "failure_risk", "probability"),
        Index("ix_predictions_asset_ts", "asset_id", "timestamp"),
    )

    prediction_id = Column(String(64), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, default=lambda: datetime.now(UTC), index=True)
    asset_id = Column(String(64), nullable=True, index=True, default="CNC-MILL-01")
    regime = Column(String(32), nullable=True, default="steady_state_heavy")
    runtime = Column(String(32), nullable=True, default="xgboost")

    # Input Features
    temperature = Column(Float, nullable=False)
    rpm = Column(Float, nullable=False)
    pressure = Column(Float, nullable=False)
    vibration = Column(Float, nullable=False)
    operating_hours = Column(Float, nullable=False)

    # Prediction Results
    failure_risk = Column(String(16), nullable=False)
    probability = Column(Float, nullable=False)
    maintenance_required = Column(Boolean, nullable=False)

    # Detailed explanations (SHAP impacts and rankings)
    shap_values = Column(JSON, nullable=True)
    contributing_factors = Column(JSON, nullable=True)

    def to_dict(self):
        return {
            "prediction_id": self.prediction_id,
            "timestamp": (self.timestamp.isoformat() if self.timestamp is not None else None),
            "asset_id": getattr(self, "asset_id", None) or "CNC-MILL-01",
            "regime": getattr(self, "regime", None) or "steady_state_heavy",
            "runtime": getattr(self, "runtime", None) or "xgboost",
            "input_features": {
                "temperature": self.temperature,
                "rpm": self.rpm,
                "pressure": self.pressure,
                "vibration": self.vibration,
                "operating_hours": self.operating_hours,
            },
            "failure_risk": self.failure_risk,
            "probability": round(float(self.probability), 4) if self.probability is not None else 0.0,  # type: ignore
            "maintenance_required": self.maintenance_required,
            "contributing_factors": self.contributing_factors or [],
            "shap_values": self.shap_values or {},
        }


class User(Base):
    __tablename__ = "pms_users"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(64), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(32), default="employee", nullable=False)
    designation = Column(String(128), default="Maintenance Specialist", nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    def to_dict(self):
        role_val = str(getattr(self, "role", "employee"))
        desig_val = getattr(self, "designation", None)
        if not desig_val or (role_val == "admin" and desig_val == "Maintenance Specialist"):
            desig_val = "System Administrator" if role_val == "admin" else "Maintenance Specialist"
        created_val = getattr(self, "created_at", None)
        return {
            "id": getattr(self, "id", None),
            "username": getattr(self, "username", None),
            "role": role_val,
            "designation": desig_val,
            "created_at": created_val.isoformat() if created_val is not None else None,
        }


class WorkOrderRecord(Base):
    __tablename__ = "work_orders"
    __table_args__ = (Index("ix_work_orders_asset_status", "asset_id", "status"),)

    work_order_id = Column(String(64), primary_key=True, index=True)
    prediction_id = Column(String(64), nullable=True, index=True)
    asset_id = Column(String(64), nullable=False, index=True)
    line_id = Column(String(128), nullable=False)
    plant_location = Column(String(128), nullable=True)
    failure_mode = Column(String(128), nullable=False)
    priority = Column(String(32), nullable=False, default="HIGH")
    status = Column(String(32), nullable=False, default="DISPATCHED_TO_CMMS", index=True)
    cmms_target = Column(String(128), nullable=False)
    technician_qualification = Column(String(128), nullable=False)
    required_bom_parts = Column(JSON, nullable=False)
    safety_interlocks = Column(JSON, nullable=False)
    torque_specs_nm = Column(Float, nullable=False)
    estimated_duration_hours = Column(Float, nullable=False)
    notes = Column(String(1024), nullable=True)
    resolution_notes = Column(String(1024), nullable=True)
    actual_failure_confirmed = Column(Boolean, nullable=True)
    dispatched_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False, index=True)
    resolved_at = Column(DateTime, nullable=True)

    def to_dict(self):
        self_any: Any = self
        dispatched_val = self_any.dispatched_at
        resolved_val = self_any.resolved_at
        return {
            "work_order_id": str(self_any.work_order_id or ""),
            "prediction_id": self_any.prediction_id,
            "asset_id": str(self_any.asset_id or ""),
            "line_id": str(self_any.line_id or ""),
            "plant_location": self_any.plant_location,
            "failure_mode": str(self_any.failure_mode or ""),
            "priority": str(self_any.priority or "HIGH"),
            "status": str(self_any.status or "DISPATCHED_TO_CMMS"),
            "cmms_target": str(self_any.cmms_target or ""),
            "technician_qualification": str(self_any.technician_qualification or ""),
            "required_bom_parts": self_any.required_bom_parts or [],
            "safety_interlocks": self_any.safety_interlocks or [],
            "torque_specs_nm": float(self_any.torque_specs_nm or 0.0),
            "estimated_duration_hours": float(self_any.estimated_duration_hours or 0.0),
            "notes": self_any.notes,
            "resolution_notes": self_any.resolution_notes,
            "actual_failure_confirmed": self_any.actual_failure_confirmed,
            "dispatched_at": dispatched_val.isoformat() if dispatched_val is not None else "",
            "resolved_at": resolved_val.isoformat() if resolved_val is not None else None,
        }


class AuditEventRecord(Base):
    __tablename__ = "audit_events"

    event_index = Column(Integer, primary_key=True, autoincrement=False)
    timestamp = Column(Float, nullable=False, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    actor_id = Column(String(128), nullable=False)
    tenant_id = Column(String(128), nullable=False)
    details = Column(JSON, nullable=False)
    status = Column(String(32), nullable=False)
    prev_hash = Column(String(64), nullable=False)
    event_hash = Column(String(64), nullable=False)


class IdempotencyKeyRecord(Base):
    __tablename__ = "idempotency_keys"

    key = Column(String(255), primary_key=True)
    status_code = Column(Integer, nullable=False)
    data = Column(JSON, nullable=False)
    created_at = Column(Float, nullable=False)
    expires_at = Column(Float, nullable=False, index=True)
