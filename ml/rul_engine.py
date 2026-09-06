import os
from typing import List, Dict, Any, Tuple, Union
import numpy as np
import pandas as pd
from xgboost import XGBRegressor
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
    Simulate equipment degradation over time with non-linear acceleration near end-of-life.
    Each unit has cycles_per_unit readings before failure.
    RUL = cycles remaining until failure.
    """
    np.random.seed(42)
    data = []
    
    for unit_id in range(1, n_units + 1):
        cycles = np.arange(0, cycles_per_unit)
        
        # Non-linear degradation acceleration factor (bathtub curve near failure)
        progress = cycles / float(cycles_per_unit)
        # Accelerates significantly after 60% of asset life has elapsed
        accel = 1.0 + 3.2 * np.power(np.maximum(0.0, progress - 0.5) / 0.5, 2.5)
        
        # Degradation trajectory: sensors degrade with accelerating velocity
        temp_base = 68.0 + (unit_id % 10) * 1.5
        temp_step = np.random.normal(0.040, 0.015, len(cycles)) * accel
        temp_drift = np.cumsum(temp_step)
        temp_trajectory = np.clip(temp_base + temp_drift, 58.0, 115.0)
        
        vibration_base = 0.22 + (unit_id % 10) * 0.015
        vib_step = np.random.normal(0.0018, 0.0006, len(cycles)) * accel
        vibration_drift = np.cumsum(vib_step)
        vibration_trajectory = np.clip(vibration_base + vibration_drift, 0.15, 1.25)
        
        pressure_base = 22.0 + (unit_id % 5) * 1.8
        press_step = np.random.normal(0.024, 0.010, len(cycles)) * accel
        pressure_drift = np.cumsum(press_step)
        pressure_trajectory = np.clip(pressure_base + pressure_drift, 18.0, 48.0)
        
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
    """Train and serialize upgraded RUL XGBRegressor model with non-linear dynamics."""
    print("Generating equipment degradation trajectories (with non-linear acceleration)...")
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
    
    # Train-test split by units (held-out test units 91-100)
    test_mask = np.isin(df['unit_id'].values[df['cycle'].values >= 20], list(range(91, 101)))
    X_train, X_test = X[~test_mask], X[test_mask]
    y_train, y_test = y[~test_mask], y[test_mask]
    
    print("Fitting RUL XGBRegressor model (capturing non-linear acceleration)...")
    model = XGBRegressor(
        n_estimators=140,
        max_depth=4,
        learning_rate=0.04,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)
    
    predictions = model.predict(X_test)
    mape = float(np.mean(np.abs((y_test - predictions) / np.maximum(y_test, 1))) * 100)
    rmse = float(np.sqrt(np.mean((y_test - predictions) ** 2)))
    
    print(f"Upgraded RUL Test MAPE: {mape:.2f}%")
    print(f"Upgraded RUL Test RMSE: {rmse:.2f} cycles")
    
    model_artifact = {
        "model": model,
        "model_type": "XGBRegressor",
        "feature_cols": feature_cols,
        "mape": round(mape, 2),
        "rmse": round(rmse, 2)
    }
    joblib.dump(model_artifact, RUL_MODEL_PATH)
    print(f"Saved upgraded RUL model to {RUL_MODEL_PATH}")
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
