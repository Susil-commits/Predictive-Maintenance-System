"""
Backend interface for Remaining Useful Life (RUL) prediction engine.
Delegates to ml.rul_engine.
"""
from ml.rul_engine import predict_rul, engineer_rolling_features, get_rul_model

__all__ = ["predict_rul", "engineer_rolling_features", "get_rul_model"]
