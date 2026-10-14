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
- **Stratified 5-Fold Cross-Validation**:
  - **ROC-AUC (CV)**: **0.9348 ± 0.0087** across 5 stratified folds (replaces stale uncalibrated estimate)
- **Held-Out Test Set Evaluation** (Total test samples = 2,000; Test positives count = 68, Normal = 1,932):
  - **ROC-AUC**: **0.9336**
  - **Brier Score Loss**:
    - Uncalibrated XGBoost: **0.0887**
    - Calibrated XGBoost (Platt Sigmoid): **0.0263** (70.38% probabilistic error reduction)
  - **Threshold Performance Comparison**:
    - **Tuned Threshold (`0.2849`)**: **F1: 0.4277** | Precision: 0.3736 | Recall: 0.5000
    - **Default Threshold (`0.5000`)**: **F1: 0.0000** | Precision: 0.0000 | Recall: 0.0000 (highlights necessity of Precision-Recall threshold optimization under 28:1 class imbalance)
- **Held-Out Slice Verification**:
  - Validated across operational slices (Thermal Overheat, Vibration Fatigue, Overstrain Surge, Tool Wear, Power Failure).

## Limitations
- **Data Distribution & Sample Size**: AI4I-derived synthetic data; small test positive count (68 total test failures, with as few as 9 test samples for Tool Wear failure). Empirical slice metrics exhibit high variance; real-world industrial deployments require continual domain recalibration.
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
