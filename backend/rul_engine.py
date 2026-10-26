"""
Backend interface for Remaining Useful Life (RUL) prediction engine.
Delegates to ml.rul_engine.
"""

from ml.rul_engine import engineer_rolling_features, get_rul_model, predict_rul

__all__ = ["engineer_rolling_features", "get_rul_model", "predict_rul"]
