import os
from typing import List, Dict, Any, Tuple, Union
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
import joblib

ML_DIR = os.path.dirname(os.path.abspath(__file__))
RUL_MODEL_PATH = os.path.join(ML_DIR, "rul_model.pkl")

def engineer_rolling_features(unit_data: pd.DataFrame, window_size: int = 20) -> pd.DataFrame:
    """
    Create time-series rolling statistical features from sensor readings.
    
    Input: DataFrame with columns [temperature, rpm, pressure, vibration]
    Output: DataFrame with rolling mean, rolling std, and rolling slope per sensor.
    """
    features_dict: Dict[str, Any] = {}
    
    for feature in ['temperature', 'rpm', 'pressure', 'vibration']:
        if feature not in unit_data.columns:
            continue
        
        series = unit_data[feature].to_numpy(dtype=float)
        s_series = pd.Series(series)
        
        # Rolling mean
        rolling_mean = s_series.rolling(window=window_size, min_periods=1).mean().to_numpy()
        features_dict[f'{feature}_rolling_mean'] = rolling_mean
        
        # Rolling std (variability)
        rolling_std = s_series.rolling(window=window_size, min_periods=1).std().to_numpy()
        features_dict[f'{feature}_rolling_std'] = np.nan_to_num(rolling_std, nan=0.0)
        
        # Rolling slope (degradation velocity)
        if len(series) > 1:
            slope = np.gradient(series)
            rolling_slope = pd.Series(slope).rolling(window=window_size, min_periods=1).mean().to_numpy()
        else:
            rolling_slope = np.zeros(len(series))
        features_dict[f'{feature}_slope'] = np.nan_to_num(rolling_slope, nan=0.0)
    
    return pd.DataFrame(features_dict)

def generate_rul_trajectories(n_units: int = 100, cycles_per_unit: int = 150) -> pd.DataFrame:
    """
    Simulate equipment degradation over time.
    Each unit has cycles_per_unit readings before failure.
    RUL = cycles remaining until failure.
    """
    np.random.seed(42)
    data = []
    
    for unit_id in range(1, n_units + 1):
        cycles = np.arange(0, cycles_per_unit)
        
        # Degradation trajectory: sensors slowly degrade and drift upwards
        temp_base = 68.0 + (unit_id % 10) * 1.5
        temp_drift = np.cumsum(np.random.normal(0.045, 0.02, len(cycles)))
        temp_trajectory = np.clip(temp_base + temp_drift, 58.0, 112.0)
        
        vibration_base = 0.22 + (unit_id % 10) * 0.015
        vibration_drift = np.cumsum(np.random.normal(0.0022, 0.0008, len(cycles)))
        vibration_trajectory = np.clip(vibration_base + vibration_drift, 0.15, 1.10)
        
        pressure_base = 22.0 + (unit_id % 5) * 1.8
        pressure_drift = np.cumsum(np.random.normal(0.028, 0.012, len(cycles)))
        pressure_trajectory = np.clip(pressure_base + pressure_drift, 18.0, 46.0)
        
        rpm = np.random.uniform(1500, 3000, len(cycles))
        
        for cycle in cycles:
            rul = cycles_per_unit - cycle  # Remaining useful life (cycles)
            data.append({
                'unit_id': unit_id,
                'cycle': cycle,
                'temperature': temp_trajectory[cycle],
                'rpm': rpm[cycle],
                'pressure': pressure_trajectory[cycle],
                'vibration': vibration_trajectory[cycle],
                'operating_hours': cycle * 0.5,  # 30 min per cycle
                'rul': rul
            })
    
    return pd.DataFrame(data)

def train_rul_model():
    """Train and serialize RUL linear regression baseline model."""
    print("Generating equipment degradation trajectories...")
    df = generate_rul_trajectories(n_units=100, cycles_per_unit=150)
    
    print(f"Total samples generated: {len(df)}")
    print(f"RUL range: {df['rul'].min()} - {df['rul'].max()} cycles")
    
    # Group by unit and engineer rolling features
    print("Engineering rolling-window features (window=20)...")
    X_list = []
    y_list = []
    feature_cols: List[str] = []
    
    for unit_id in df['unit_id'].unique():
        unit_data = df[df['unit_id'] == unit_id].reset_index(drop=True)
        rolling_features = engineer_rolling_features(unit_data, window_size=20)
        if not feature_cols:
            feature_cols = list(rolling_features.columns)
            
        X_unit = rolling_features.values
        y_unit = unit_data['rul'].values
        
        # Skip initial warm-up samples (window size)
        X_list.append(X_unit[20:])
        y_list.append(y_unit[20:])
    
    X = np.vstack(X_list)
    y = np.concatenate(y_list)
    
    print(f"Final training feature matrix shape: {X.shape}")
    print(f"Feature columns ({len(feature_cols)}): {feature_cols}")
    
    print("Fitting RUL Linear Regression model...")
    model = LinearRegression()
    model.fit(X, y)
    
    # Evaluate on held-out test unit (unit 100)
    test_unit = df[df['unit_id'] == df['unit_id'].max()].reset_index(drop=True)
    test_features = engineer_rolling_features(test_unit, window_size=20)
    test_X = test_features.values[20:]
    test_y = test_unit['rul'].values[20:]
    
    predictions = model.predict(test_X)
    mape = float(np.mean(np.abs((test_y - predictions) / np.maximum(test_y, 1))) * 100)
    rmse = float(np.sqrt(np.mean((test_y - predictions) ** 2)))
    
    print(f"RUL Test MAPE: {mape:.2f}%")
    print(f"RUL Test RMSE: {rmse:.2f} cycles")
    
    model_artifact = {
        "model": model,
        "feature_cols": feature_cols,
        "mape": mape,
        "rmse": rmse
    }
    joblib.dump(model_artifact, RUL_MODEL_PATH)
    print(f"Saved trained RUL model to {RUL_MODEL_PATH}")
    return model, mape, rmse

_cached_rul_artifact = None

def get_rul_model():
    global _cached_rul_artifact
    if _cached_rul_artifact is None:
        if not os.path.exists(RUL_MODEL_PATH):
            train_rul_model()
        _cached_rul_artifact = joblib.load(RUL_MODEL_PATH)
    return _cached_rul_artifact

def predict_rul(equipment_history: Union[List[Dict[str, Any]], pd.DataFrame]) -> Tuple[float, float]:
    """
    Predict cycles and hours remaining before equipment failure from telemetry series.
    Input: list of sensor readings or DataFrame (e.g. 5-30 readings)
    Output: (estimated_rul_cycles, confidence)
    """
    if isinstance(equipment_history, list):
        if not equipment_history:
            raise ValueError("Equipment history is empty")
        df_hist = pd.DataFrame(equipment_history)
    else:
        df_hist = equipment_history.copy()
        
    for col in ['temperature', 'rpm', 'pressure', 'vibration']:
        if col not in df_hist.columns:
            raise ValueError(f"Missing required sensor telemetry feature: {col}")
            
    artifact = get_rul_model()
    model = artifact["model"]
    feature_cols = artifact["feature_cols"]
    
    features_df = engineer_rolling_features(df_hist, window_size=20)
    latest_features = features_df[feature_cols].iloc[[-1]].values
    
    pred_rul = float(model.predict(latest_features)[0])
    pred_rul = max(1.0, pred_rul)  # Clip at minimum 1 cycle
    
    # Calculate confidence based on history length and stability
    history_len = len(df_hist)
    # Higher confidence with at least 15-20 readings
    data_completeness = min(1.0, history_len / 20.0)
    vib_arr = np.asarray(df_hist['vibration'], dtype=float)
    vib_variance = float(np.std(vib_arr)) if history_len > 1 else 0.05
    stability_penalty = min(0.20, vib_variance * 0.5)
    confidence = round(float(np.clip(0.60 + 0.35 * data_completeness - stability_penalty, 0.50, 0.96)), 2)
    
    return pred_rul, confidence

if __name__ == "__main__":
    train_rul_model()
