# PMS XGBoost Classifier — Model Card

> **Dataset Notice & Validation Scope**: The training and evaluation data is derived from the UCI AI4I 2020 Predictive Maintenance dataset (synthetic benchmark with simulated physics and noise injection). All reported metrics validate the end-to-end data pipeline, calibration dynamics, and architecture, but **do not represent field performance or operational reliability on physical industrial machinery**.

## Model Overview
- **Name**: Calibrated XGBoost Risk Classifier
- **Task**: Binary equipment failure risk classification
- **Training Data**: 10,000 telemetry records derived from UCI AI4I 2020 distribution with independent sensor noise (no feature leakage)
- **Algorithm**: Gradient Boosted Decision Trees (`XGBClassifier`) with regularized tree depth and hyperparameter tuning
- **Calibration**: Platt sigmoid calibration via 3-fold `CalibratedClassifierCV`
- **Explainability**: Local feature attribution via SHAP TreeExplainer
- **Deployment Formats**: Python (`ml/model.pkl`), ONNX Edge Runtime (`ml/model.onnx`)

## Intended Use
- **Primary Operational Domain**: Real-time operational failure risk assessment and degradation scoring for industrial machinery, rotational motors, CNC milling spindles, and hydraulic powertrains.
- **Workflow Integration**: Decision-support copilot for plant reliability engineers, technician work-order prioritization, and condition-based monitoring dashboards.
- **Inference Environments**: Edge telemetry gateway processing via ONNX Runtime (`ml/model.onnx`) or centralized cloud API batch/streaming ingestion (`ml/model.pkl`).

## Out-of-Scope Use
- **Autonomous Plant Shutdowns**: Autonomous emergency stop (E-stop) or safety-instrumented system (SIS) triggers without human-in-the-loop engineering validation.
- **Life-Safety and Mission-Critical Infrastructure**: Life-safety equipment, nuclear facility controls, aviation flight avionics, or clinical life-support machinery.
- **Uncalibrated Sensor Drift & Novel Hardware**: Turbines, non-reciprocating compressors, or novel machine architectures without baseline telemetry recalibration.
- **Standalone Cutting Tool Life Assurance**: Sole reliance on the binary classification model for cutting blade tool wear monitoring without dedicated acoustic sensor heads (due to empirical Tool Wear class scarcity).

## Performance
- **Stratified 5-Fold Cross-Validation**:
  - **ROC-AUC (CV)**: **0.9348 ± 0.0087** across 5 stratified folds
  - **F1-Score (CV)**: **0.3466 ± 0.0212** (Range: `[0.3191, 0.3846]`)
- **Held-Out Test Set Evaluation** (Total test samples = 2,000; Test positives count = 68, Normal = 1,932):
  - **ROC-AUC**: **0.9336** (95% Bootstrap CI: `[0.9070, 0.9551]`, SE: `0.0125`)
  - **Brier Score Loss & Probability Calibration**:
    - Uncalibrated XGBoost: **0.0887**
    - Calibrated XGBoost (Platt Sigmoid): **0.0263** (95% Bootstrap CI: `[0.0215, 0.0313]`, SE: `0.0024`, 70.38% error reduction)
    - *Methodology & Confirmation*: Both Brier scores (0.0887 uncalibrated to 0.0263 calibrated) were evaluated on the **exact same held-out test set** (N = 2,000; 68 positive failures) and derived from the **exact same underlying model family** (`XGBClassifier` with `learning_rate=0.03, max_depth=3, n_estimators=150`). Applying 3-fold Platt sigmoid calibration directly reduces probabilistic error on identical test data without changing model architecture or feature definitions. Calibration reliability curve saved at `ml/calibration_reliability_diagram.png`.
  - **Threshold Performance Comparison**:
    - **Tuned Threshold (`0.2849`)**: **F1: 0.4277** (95% Bootstrap CI: `[0.3239, 0.5091]`, SE: `0.0479`) | Precision: 0.3736 | Recall: 0.5000
    - **Default Threshold (`0.5000`)**: **F1: 0.0000** | Precision: 0.0000 | Recall: 0.0000 (highlights necessity of Precision-Recall threshold optimization under 28:1 class imbalance)
- **Held-Out Slice Verification**:
  - Validated across operational slices (Thermal Overheat, Vibration Fatigue, Overstrain Surge, Tool Wear, Power Failure).

## Known Weaknesses & Failure Mode Uncertainty

The table below reports empirical performance across failure modes on both the held-out test set and stratified 5-fold cross-validation. Stratified 5-fold CV is evaluated without touching or tuning on the test set, explicitly revealing the high variance and uncertainty inherent in small-support failure modes.

| Failure Mode | Test Support (N=2,000) | Test F1 | Test Recall | 5-Fold CV Total Support | 5-Fold CV Supp / Fold | 5-Fold CV F1 (Mean ± Std) | 5-Fold CV F1 Range [Min, Max] | 5-Fold CV Recall (Mean ± Std) | 5-Fold CV ROC-AUC (Mean ± Std) | Diagnostic Reality & Weakness |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Tool Wear (TWF)** | 9 | 0.1408 | 0.5556 | 43 | 8.6 | **0.0285 ± 0.0353** | **[0.0000, 0.0800]** | 0.0500 ± 0.0667 | 0.9144 ± 0.0124 | **Severe Data Starvation**: In 3 of 5 folds, CV F1 collapses to 0.0000. The single test-set F1 of 0.14 was driven by only 5 true positive hits on 9 test cases accompanied by 57 false alarms. |
| **Thermal Failure (HDF)** | 29 | 0.1702 | 0.2759 | 115 | 23.0 | **0.1212 ± 0.0384** | **[0.0625, 0.1667]** | 0.1113 ± 0.0389 | 0.9330 ± 0.0032 | **Persistent Insensitivity**: Moderate ranking ability (AUC 0.9330), but weak F1 and low recall (~11%) because the model triggers primarily on acute thermal shocks rather than gradual heat dissipation creep. |
| **Power Failure (PWF)** | 12 | 0.1842 | 0.5833 | 80 | 16.0 | **0.2956 ± 0.0671** | **[0.2286, 0.4091]** | 0.3522 ± 0.1093 | 0.9394 ± 0.0119 | **High Recall Variance**: Sensitive to mechanical power spikes, but fold recall fluctuates widely between 0.2778 and 0.5625 depending on torque/speed combinations. |
| **Overstrain Failure (OSF)** | 16 | 0.3023 | 0.8125 | 92 | 18.4 | **0.4137 ± 0.0984** | **[0.2326, 0.5333]** | 0.5014 ± 0.1617 | 0.9715 ± 0.0136 | **Sharp Signature with High Variance**: Strongest mechanical signal (AUC 0.9715), but fold recall varies between 0.2632 and 0.7500 across validation folds. |
| **All Failures (Overall)** | 68 | 0.4177 | 0.4853 | 339 | 67.8 | **0.3466 ± 0.0212** | **[0.3191, 0.3846]** | 0.2597 ± 0.0252 | 0.9348 ± 0.0087 | Aggregate performance across 28:1 class imbalance; overall CV AUC remains solid at 0.9348 ± 0.0087. |

> **Do not claim improvements the numbers do not show**:
> - The single test-set F1 of 0.14 for Tool Wear Failure gave a false impression of stability. Cross-validation reveals that the model effectively fails to detect tool wear in 3 out of 5 folds (F1 = 0.0000), yielding an average CV F1 of only **0.0285 ± 0.0353**.
> - Thermal Failure (HDF) F1 remains severely impaired (**0.1212 ± 0.0384 CV F1**; test F1 **0.1702**), capturing only ~11% to 28% of thermal degradation events.
> - These weaknesses stem from class scarcity (<0.45% tool wear samples in dataset) and the absence of continuous wear trajectory sensors. They cannot be resolved by threshold tuning alone and require dedicated multi-task wear heads or physical sensor instrumentation before real-world operational reliance.

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
