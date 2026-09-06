# PMS XGBoost Classifier — Model Card

## Model Overview
- **Name**: Calibrated XGBoost Risk Classifier
- **Task**: Binary equipment failure risk classification
- **Training Data**: 10,000 telemetry records derived from UCI AI4I 2020 distribution with independent sensor noise (no feature leakage)
- **Algorithm**: Gradient Boosted Decision Trees (`XGBClassifier`) with regularized tree depth and hyperparameter tuning
- **Calibration**: Platt sigmoid calibration via 3-fold `CalibratedClassifierCV`
- **Explainability**: Local feature attribution via SHAP TreeExplainer
- **Deployment Formats**: Python (`ml/model.pkl`), ONNX Edge Runtime (`ml/model.onnx`)

## Intended Use
- Real-time operational failure risk assessment for heavy industrial machinery, motors, and hydraulic powertrains.
- Decision support for maintenance engineers and dispatch prioritization.
- **NOT suitable for**: Autonomous control shutdown or life-critical safety shutdown systems without human-in-the-loop validation.

## Performance
- **Realistic Un-leaked Baseline**:
  - **ROC-AUC**: ~0.85 ± 0.03 on stratified test set
  - **Precision**: Tuned for low false alarm rate in industrial monitoring
  - **Recall**: Optimized via Precision-Recall curve threshold tuning
  - **Brier Score Loss**: Significantly reduced via Platt sigmoid calibration (~0.02)
- **Held-Out Slice Verification**:
  - Validated across 9 held-out operational slices (Nominal, Thermal Overheat, Vibration Fatigue, Overstrain Surge, Cold Idle, Stall Strain, Highway Light Load, Extreme Breakdown).

## Limitations
- **Synthetic Noise Formulation**: Trained on high-fidelity AI4I distribution; operational domain shifts in field environments may require recalibration.
- **Binary Classification Scope**: Predicts instantaneous state risk; Remaining Useful Life (time-to-failure) is handled separately by `ml/rul_engine.py`.
- **Operating Envelope Validity**:
  - Temperature: 55.0°C – 115.0°C
  - Rotational Speed: 1,000 – 3,200 RPM
  - Hydraulic Pressure: 16.0 – 48.0 bar
  - Vibration: 0.12 – 1.25 g
  - Operating Hours: 100 – 6,500 hrs

## Uncertainty Quantification
- Predictions with calibrated probabilities in the ambiguous zone `[0.40, 0.60]` are tagged with `confidence: LOW` and flagged for manual technician inspection (`⚠️ UNCERTAIN`).
- Predictions `< 0.40` or `> 0.60` are classified with `confidence: HIGH`.

## Data Drift Monitoring
- Monitored via continuous Population Stability Index (PSI) against baseline distributions stored in `reference_stats.json`.
- Alerts triggered when feature PSI exceeds 0.25 (significant drift threshold).
