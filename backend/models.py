import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Boolean, DateTime, JSON
from .database import Base

class PredictionRecord(Base):
    __tablename__ = "predictions"

    prediction_id = Column(String(64), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
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
            "timestamp": self.timestamp.isoformat() if self.timestamp is not None else None,
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
            "shap_values": self.shap_values or {}
        }


class User(Base):
    __tablename__ = "pms_users"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(64), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(32), default="employee", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at is not None else None,
        }
