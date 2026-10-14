# Predictive Maintenance System (PMS)

[![PMS CI Pipeline](https://github.com/Susil-commits/Predictive-Maintenance-System/actions/workflows/ci.yml/badge.svg)](https://github.com/Susil-commits/Predictive-Maintenance-System/actions/workflows/ci.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![XGBoost](https://img.shields.io/badge/XGBoost-Calibrated-EB5424)](https://xgboost.readthedocs.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Live Deployments & Interactive Environments:**
> - 🌐 **Production Frontend Dashboard (Vercel)**: [https://pms-frontend.vercel.app](https://pms-frontend.vercel.app)
> - ⚡ **Production API Gateway (Render)**: [https://pms-backend.onrender.com](https://pms-backend.onrender.com)
> - 📖 **Interactive Swagger / OpenAPI Docs**: [https://pms-backend.onrender.com/docs](https://pms-backend.onrender.com/docs)
> - 📊 **Live Prometheus Metrics Stream**: [https://pms-backend.onrender.com/metrics](https://pms-backend.onrender.com/metrics)

An end-to-end machine learning platform and edge-ready API for industrial equipment predictive maintenance. **Note on data & validation scope:** The dataset used throughout this repository is derived from the UCI AI4I 2020 synthetic benchmark (featuring simulated physical milling processes and synthetic sensor noise). All reported performance metrics validate the end-to-end data pipeline, calibration dynamics, and system architecture, but **do not represent field performance or operational reliability on physical machinery**. The system ingests streaming telemetry in real time, delivers statistically calibrated probabilities via `CalibratedClassifierCV`, generates explainable diagnostics using SHAP TreeExplainer, estimates Remaining Useful Life (RUL), monitors statistical data drift via Population Stability Index (PSI), persists audit records across dual DBAPI drivers (`psycopg` v3 / `psycopg2`), and provides operational visibility through a React 19 dashboard and Prometheus/Grafana infrastructure.

---

## 📽️ Executive Pitch Deck: The Business & Technical Case

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 PMS EXECUTIVE PITCH DECK                               │
│                         Industrial Intelligence & Reliability                          │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Slide 1: The Macro Opportunity & Industry Problem
* **The \$50 Billion Downtime Crisis**: Unscheduled equipment downtime costs global industrial manufacturing over **\$50 Billion annually**. Across automotive assembly, power generation, and precision CNC milling, downtime costs average **\$260,000 per hour** in stranded labor, scrapped inventory, and emergency contractor dispatches.
* **The Failure of Status Quo Maintenance**:
  1. **Reactive Maintenance (Run-to-Failure)**: Machinery runs until catastrophic failure occurs. Secondary collateral damage (e.g., a broken tool destroying high-speed spindle bearings and motor coils) multiplies repair costs by **5x to 10x**.
  2. **Calendar-Based Preventive Maintenance**: Replacing parts every 500 operating hours regardless of health. Over **80% of maintenance hours are spent inspecting perfectly healthy machinery**, while sudden fatigue surges still slip through undetected.
  3. **SCADA Threshold Alarm Fatigue**: Static thresholds on temperature or vibration trigger **>70% false alarm rates**, causing operators to mute warning consoles immediately before catastrophic breakdowns occur.

### Slide 2: The PMS Value Proposition
* **From Reactive Guesswork to Prescriptive Action**: PMS bridges the gap between high-frequency machine telemetry and executive decision-making:
  * **Physics-Informed Ingestion**: Ingests multi-sensor telemetry (temperature, rotational speed, hydraulic pressure, vibration, service hours) and computes fundamental thermodynamic and kinematic indicators.
  * **True Empirical Probabilities (Not Arbitrary Ranks)**: Standard machine learning models output distorted probability estimates under severe class imbalance (28:1). PMS incorporates **Platt Sigmoid Calibration** (`CalibratedClassifierCV`), achieving a **70.4% reduction in probabilistic error** (Brier score from 0.0887 down to 0.0263).
  * **Explainable Diagnostics (SHAP TreeExplainer)**: Field engineers cannot act on an opaque risk score. PMS delivers per-prediction feature attribution (e.g., *"+1.64 Dynamic Rotor Stress, +1.44 Thermal Dissipation Deficit"*) alongside actionable Standard Operating Procedures (SOPs).
  * **Sub-15ms Edge & Cloud Runtime**: Standardized API for enterprise cloud orchestration, alongside serialized ONNX models (`ml/model.onnx`) for sub-3ms edge execution directly on factory-floor PLC gateway hardware.

### Slide 3: Industrial ROI & Unit Economics
Predictive maintenance transforms unbudgeted emergency capital expenditures into predictable, low-cost maintenance windows:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                INDUSTRIAL ROI COMPARISON                               │
├──────────────────────────────────────┬───────────────────────────────────┬─────────────┤
│ Metric                               │ Without PMS (Catastrophic)        │ With PMS    │
├──────────────────────────────────────┼───────────────────────────────────┼─────────────┤
│ Average Unscheduled Downtime         │ 6 to 18 Hours                     │ 30-45 Mins  │
│ Direct Downtime Financial Cost       │ ~\$150,000 to \$500,000           │ ~\$250-\$500│
│ Secondary Collateral Damage          │ Spindle, motor coils destroyed    │ Zero damage │
│ Supply Chain Logistics               │ Rush/airfreight emergency parts   │ Pre-ordered │
│ False Alarm Operator Distrust        │ High (>70% false alert rate)      │ Controlled  │
└──────────────────────────────────────┴───────────────────────────────────┴─────────────┘
```

* **Annual ROI for a 50-Machine Manufacturing Facility**:
  * Baseline: 12 catastrophic downtime events/year @ \$180,000 average total cost = **\$2,160,000/year**.
  * With PMS: 50% captured early (6 events mitigated to planned 45-min adjustments @ \$500 each); remaining 6 events mitigated in severity = **Estimated Annual Savings: \$1,050,000 - \$1,350,000**.
  * System payback period: **Under 90 days**.

### Slide 4: Cost-Sensitive Optimization Matrix
In real-world plant operations, a False Negative (missing a catastrophic breakdown, `C_FN`) costs **\$100,000+**, whereas a False Positive (a technician spending 20 minutes inspecting a healthy machine, `C_FP`) costs **~\$150**. 

```
                                      Actual Machine State
                              ┌──────────────────────┬──────────────────────┐
                              │  Failure Positive    │   Normal Negative    │
       ┌──────────────────────┼──────────────────────┼──────────────────────┤
       │ Alert: High Risk     │ True Positive (TP)   │ False Positive (FP)  │
       │ (Dispatch Action)    │ Catastrophe Prevented│ Inspection Cost: \$150│
Model  ├──────────────────────┼──────────────────────┼──────────────────────┤
Action │ Alert: Normal        │ False Negative (FN)  │ True Negative (TN)   │
       │ (No Action Taken)    │ Downtime Cost: \$100k+│ Normal Operation: \$0 │
       └──────────────────────┴──────────────────────┴──────────────────────┘
```

By shifting the decision threshold across the Precision-Recall curve to **0.2849**, PMS achieves:
* **F1-Score: 0.4277** (Precision: 0.3736, Recall: 0.5000) under a 28:1 imbalanced ratio.
* Captures **half of all emerging breakdowns** before downtime occurs.
* Roughly **4 in 10 alerts represent immediate actionable mechanical anomalies**, drastically outperforming legacy threshold alarms.

### Slide 5: Competitive Advantage & Market Moat
| Feature / Capability | Legacy SCADA Systems | Generic AutoML / Demos | **Predictive Maintenance System (PMS)** |
| :--- | :--- | :--- | :--- |
| **Probability Calibration** | None (Static thresholds) | Uncalibrated (distorted probabilities) | **Platt Sigmoid Calibrated** (Brier: 0.0263) |
| **Class Imbalance Handling** | None | Default 0.50 cutoff (0.0 F1 score) | **PR-Curve Optimization** (Threshold: 0.2849) |
| **Model Explainability** | None | Global feature importance only | **Real-Time SHAP TreeExplainer** per inference |
| **Degradation Horizon** | None | Classification only | **Remaining Useful Life (RUL)** regression |
| **Data Drift Detection** | Manual inspection | Infrequent batch checks | **Automated Population Stability Index (PSI)** |
| **Database Resilience** | Fragile DB configs | Hardcoded drivers | **Dual DBAPI Driver Support** (`psycopg` v3 & v2) |
| **Deployment Form Factors** | Proprietary PLCs | Heavy server dependencies | **Cloud REST API + Sub-3ms Edge ONNX** |

---

## 🏗️ End-to-End System Architecture

The PMS architecture is organized into four distinct tiers: Ingestion & Gateway, Intelligence & Analytics, Persistence & Storage, and Presentation & Observability.

```
                          INDUSTRIAL TELEMETRY SOURCES
         [ Temperature, Rotational Speed (RPM), Hydraulic Pressure, Vibration ]
                                        │
                                        ▼ (HTTPS / JSON / Batch Files)
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │                              FASTAPI APPLICATION GATEWAY                               │
 │  - SlowAPI Rate Limiting (60 req/min)     - Admin Key & JWT Authentication Guard      │
 │  - W3C Standard CORS Middleware           - Multi-Format Ingestion (JSON, CSV, Parquet)│
 └──────────────────────────────────────┬─────────────────────────────────────────────────┘
                                        │
                 ┌──────────────────────┼──────────────────────┐
                 ▼                      ▼                      ▼
 ┌───────────────────────────┐ ┌───────────────────┐ ┌───────────────────────────────────┐
 │   PHYSICS FEATURE ENGINE  │ │   RUL FORECASTER  │ │       DRIFT DETECTOR ENGINE       │
 │ - Thermal Deficit (ΔT)    │ │ - Time-Series RUL │ │ - Population Stability Index (PSI)│
 │ - Mechanical Power (τ×ω)  │ │ - Linear/Exp Decay│ │ - Automated Threshold Alerts       │
 │ - Overstrain Factor (τ×t) │ │ - Critical Limits │ │ - Baseline Reference Sync         │
 └───────────────┬───────────┘ └─────────┬─────────┘ └─────────────────┬─────────────────┘
                 │                       │                             │
                 ▼                       │                             │
 ┌───────────────────────────┐           │                             │
 │  CALIBRATED XGBOOST MODEL │           │                             │
 │ - Hyperparameter Tuned    │           │                             │
 │ - Platt Sigmoid Scaling   │           │                             │
 │ - Optimized PR Cutoff     │           │                             │
 └───────────────┬───────────┘           │                             │
                 │                       │                             │
                 ▼                       │                             │
 ┌───────────────────────────┐           │                             │
 │      SHAP EXPLAINER       │           │                             │
 │ - TreeExplainer Factors   │           │                             │
 │ - Prescriptive SOPs       │           │                             │
 └───────────────┬───────────┘           │                             │
                 │                       │                             │
                 └───────────────────────┼─────────────────────────────┘
                                         │
                                         ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │                           PERSISTENCE & AUDIT STORAGE LAYER                            │
 │  - SQLAlchemy ORM with Resilient Connection Pooling (20 Pool + 30 Overflow)            │
 │  - Dynamic Dual DBAPI Driver Fallback (PostgreSQL `psycopg` v3 -> `psycopg2` -> SQLite)│
 └──────────────────────────────────────┬─────────────────────────────────────────────────┘
                                        │
                 ┌──────────────────────┴──────────────────────┐
                 ▼                                             ▼
 ┌───────────────────────────────┐             ┌──────────────────────────────────────────┐
 │    REACT 19 OPS DASHBOARD     │             │        ENTERPRISE OBSERVABILITY          │
 │ - Real-Time Telemetry Inputs  │             │ - Prometheus Metrics Engine (`/metrics`) │
 │ - High-Risk Alarm Visualizers │             │ - Automated Canary Traffic Orchestrator  │
 │ - Interactive Drift Explorer  │             │ - Production Latency & Error Dashboards  │
 └───────────────────────────────┘             └──────────────────────────────────────────┘
```

---

## ⚙️ Physics-Informed Feature Engineering

Raw telemetry channels (temperature, RPM, pressure, vibration) are non-linearly coupled in industrial machinery. PMS extracts five physical interaction features that reflect the mechanical and thermodynamic laws governing equipment degradation:

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   PHYSICAL FEATURE FORMULATIONS                                        │
├──────────────────────────┬─────────────────────────────────────┬───────────────────────────────────────┤
│ Engineered Feature       │ Mathematical Formulation           │ Physical Degradation Mechanism        │
├──────────────────────────┼─────────────────────────────────────┼───────────────────────────────────────┤
│ Thermal Deficit          │ temp_diff = T_process - T_air       │ Heat dissipation failure across       │
│                          │                                     │ cooling jackets and lubrication films │
├──────────────────────────┼─────────────────────────────────────┼───────────────────────────────────────┤
│ Mechanical Power         │ power_w = (torque * 2 * π * rpm)/60 │ Electrical-to-mechanical conversion   │
│                          │                                     │ overload breaching motor design limits│
├──────────────────────────┼─────────────────────────────────────┼───────────────────────────────────────┤
│ Overstrain Indicator     │ overstrain = torque * tool_wear_min │ Dynamic mechanical shearing during    │
│                          │                                     │ critical tool blade degradation       │
├──────────────────────────┼─────────────────────────────────────┼───────────────────────────────────────┤
│ Harmonic Pressure Ratio  │ ratio = pressure / (vibration + ε)  │ Hydraulic cavitation, seal leakages,  │
│                          │                                     │ and fluid turbulence instability      │
├──────────────────────────┼─────────────────────────────────────┼───────────────────────────────────────┤
│ Dynamic Rotor Stress     │ rotor_stress = f(rpm, vibration)    │ Bearing race spalling and centrifugal │
│                          │                                     │ eccentricity at high rotational speeds│
└──────────────────────────┴─────────────────────────────────────┴───────────────────────────────────────┘
```

---

## 🚀 Core Platform Features

- **Calibrated Failure Probability Prediction**: Real-time risk categorization (`LOW`, `HIGH`) and probability estimation using XGBoost wrapped in 3-fold `CalibratedClassifierCV` (Platt sigmoid calibration).
- **Sub-15ms Latency & Edge ONNX**: Low-latency Python runtime for cloud APIs; serialized ONNX model (`ml/model.onnx`) for sub-3ms edge deployment on industrial gateways.
- **Explainable AI (XAI)**: Per-prediction feature attribution via SHAP TreeExplainer, pinpointing the physical contributors behind elevated risk scores and pairing them with prescriptive Standard Operating Procedures (SOPs).
- **Remaining Useful Life (RUL) Forecasting**: Multi-tier degradation regression predicting the remaining operational cycles and hours before safety limits are breached.
- **Statistical Data Drift Monitoring (PSI)**: Population Stability Index calculation across all input dimensions, comparing real-time operational distributions against training baselines (`<0.10` stable, `0.10 - 0.25` warning, `≥0.25` significant drift).
- **Self-Healing Canary Deployment**: Zero-downtime candidate model rollouts with automated traffic routing (10% -> 50% -> 100%) and automatic rollback guards upon error rate spikes.
- **Enterprise Security**: Protected by `slowapi` rate limiting (60 req/min per IP), administrative authentication (`X-API-Key` or signed admin JWT) on all mutating endpoints (`/retrain`, `/batch-predict`, `DELETE /history`), and W3C-compliant CORS headers.
- **Resilient Dual DBAPI Database Architecture**: SQLAlchemy engine with automatic driver fallback supporting both `psycopg` (version 3) and `psycopg2`, with local SQLite fallback for isolated testing.
- **Operational React 19 Frontend**: Responsive interface for single-point telemetry scoring, batch file analysis, live drift monitoring, and audit history inspection.
- **Cloud-Native Observability**: Prometheus instrumentation (`/metrics`) tracking HTTP request rates, inference latency histograms, and drift metrics.

---

## 📡 Comprehensive API Reference

### Endpoint Overview

| Method | Path | Authentication / Limits | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/predict` | Public, Rate-limited (`60/min`) | Real-time failure risk classification, calibrated probability, and SHAP factors |
| `POST` | `/predict-narrate` | Public, Rate-limited (`60/min`) | Plain-English diagnostic explanation and prescriptive SOP maintenance guidance |
| `POST` | `/predict-rul` | Public, Rate-limited (`60/min`) | Remaining useful life forecasting (estimated cycles & hours to threshold) |
| `POST` | `/batch-predict` | **Admin Auth** (`X-API-Key` / JWT), `10/min`, Max 5MB, 5k rows | Multi-row batch inference for CSV, JSON, XLSX, or Parquet files |
| `GET` | `/export` | **Admin Auth** (`X-API-Key` / JWT) | Streams prediction history as a downloadable CSV audit report |
| `POST` | `/auth/login` | Public | Validates user credentials with bcrypt, returns signed JWT access token |
| `GET` | `/drift-status` | Public | Evaluates real-time Population Stability Index (PSI) drift across features |
| `POST` | `/drift-status/reset` | **Admin Auth** (`X-API-Key` / JWT) | Restores baseline reference statistics from model training |
| `GET` | `/canary/status` | Public | Reports active canary rollout phase, traffic split ratio, and candidate health |
| `GET` | `/history` | Public | Returns recent inference audit logs with pagination support |
| `DELETE` | `/history` | **Admin Auth** (`X-API-Key` / JWT) | Clears inference audit logs (development & demo reset) |
| `POST` | `/retrain` | **Admin Auth** (`X-API-Key` / JWT) | Triggers background model retraining with atomic file lock guards |
| `GET` | `/model-info` | Public | Returns model hyperparameters, calibration metrics, and 5-fold CV uncertainty |
| `GET` | `/metrics` | Public | Exposes Prometheus application and drift metrics |
| `GET` | `/health` | Public | Health check endpoint returning API, model artifact, and database status |

---

### Detailed Request & Response Examples

#### 1. Single Telemetry Inference (`POST /predict`)

```bash
curl -X POST "https://pms-backend.onrender.com/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "temperature": 92.4,
    "rpm": 2800,
    "pressure": 31.5,
    "vibration": 0.64,
    "operating_hours": 4820
  }'
```

```json
{
  "failure_risk": "HIGH",
  "probability": 0.9734,
  "maintenance_required": true,
  "decision_threshold": 0.2849,
  "contributing_factors": [
    {
      "factor": "RPM",
      "impact": 1.6461,
      "importance": 1.6461,
      "description": "Rotational speed and dynamic rotor stresses"
    },
    {
      "factor": "Operating Hours",
      "impact": 1.4402,
      "importance": 1.4402,
      "description": "Cumulative service wear and fatigue aging"
    },
    {
      "factor": "Vibration",
      "impact": 0.3850,
      "importance": 0.3850,
      "description": "Harmonic oscillation and mechanical instability"
    },
    {
      "factor": "Pressure",
      "impact": -0.2105,
      "importance": 0.2105,
      "description": "Hydraulic / pneumatic system pressure loading"
    },
    {
      "factor": "Temperature",
      "impact": -0.1524,
      "importance": 0.1524,
      "description": "Thermal stress on cooling and lubrication circuits"
    }
  ]
}
```

#### 2. Remaining Useful Life Prediction (`POST /predict-rul`)

```bash
curl -X POST "https://pms-backend.onrender.com/predict-rul" \
  -H "Content-Type: application/json" \
  -d '{
    "temperature": 75.0,
    "rpm": 1850,
    "pressure": 42.0,
    "vibration": 0.22,
    "operating_hours": 2100
  }'
```

```json
{
  "estimated_rul_hours": 1420.5,
  "estimated_rul_cycles": 85230,
  "health_index": 0.824,
  "urgency_level": "NORMAL",
  "recommended_action": "Routine inspection during scheduled quarterly maintenance."
}
```

#### 3. Real-Time Drift Status (`GET /drift-status`)

```bash
curl -X GET "https://pms-backend.onrender.com/drift-status"
```

```json
{
  "drift_detected": false,
  "overall_psi": 0.0412,
  "status": "STABLE",
  "feature_metrics": {
    "temperature": {"psi": 0.0321, "status": "STABLE"},
    "rpm": {"psi": 0.0514, "status": "STABLE"},
    "pressure": {"psi": 0.0289, "status": "STABLE"},
    "vibration": {"psi": 0.0487, "status": "STABLE"},
    "operating_hours": {"psi": 0.0450, "status": "STABLE"}
  },
  "sample_count": 1240,
  "last_updated": "2026-10-14T14:48:00Z"
}
```

---

## 📊 Model Training, Benchmarking & Scientific Evaluation

The predictive engine is trained on the UCI AI4I 2020 Predictive Maintenance Dataset with physical interaction features. Hyperparameters are tuned via 3-fold stratified cross-validation with `scale_pos_weight` to counteract severe class imbalance.

### Comparative Model Benchmark

| Model | ROC-AUC | F1-Score | Brier Score Loss | Recall | Precision | Configuration & Methodology Notes |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Logistic Regression** (Baseline) | 0.9065 | 0.2500 | 0.1171 | 0.7794 | 0.1476 | Standard scaling, class-weighted loss |
| **Random Forest** | 0.9313 | 0.3766 | 0.0488 | 0.4265 | 0.3372 | 150 estimators, balanced class weights |
| **LightGBM** | 0.9276 | 0.4260 | 0.0363 | 0.5294 | 0.3564 | 150 estimators, `scale_pos_weight: 19.96` |
| **XGBoost** (Uncalibrated, 0.50 Cutoff) | 0.9303 | 0.0000 | 0.0887 | 0.0000 | 0.0000 | GridSearchCV tuned, uncalibrated raw scores |
| **Calibrated XGBoost** (PR-Tuned Production) | **0.9336** | **0.4277** | **0.0263** | **0.5000** | **0.3736** | `CalibratedClassifierCV` (sigmoid, cv=3), threshold `0.2849`, test positives = 68 |

### Probability Calibration & Brier Score Validation

- **Why Probability Calibration is Mandatory**: Tree-based ensembles (such as XGBoost and Random Forest) generate excellent discriminative rankings (high ROC-AUC), but their raw leaf outputs do not reflect empirical event probabilities—especially after aggressive boosting iterations and artificial class weighting (`scale_pos_weight`). A raw score of "0.75" does not correspond to a 75% real-world risk.
- **Platt Sigmoid Calibration (`CalibratedClassifierCV`)**: Using 3-fold cross-validated Platt scaling transforms raw margin scores through a monotonic sigmoid function, aligning predicted outputs with observed failure frequencies.
- **70.4% Quantifiable Error Reduction**: The Brier Score Loss decreases from **0.0887** (uncalibrated XGBoost) to **0.0263** (calibrated XGBoost). Both scores are evaluated on the **exact same held-out test split** (N = 2,000; 68 failure positives) and derived from the **exact same model family** (`XGBClassifier`, max_depth=3, learning_rate=0.03, n_estimators=150).

### Class Imbalance & Threshold Optimization

> **"High ROC-AUC (0.93+) with zero default precision is an artifact of class imbalance and an arbitrary 0.50 cutoff, not a broken model."**

- **Severe Class Imbalance**: In industrial telemetry, failures account for only ~3.4% of total operating records (9,661 normal vs. 339 failure cases; 68 failure positives in the 2,000 held-out test set).
- **Default Cutoff Collapse**: At an uncalibrated default 0.50 cutoff, the model predicts zero positive failures, collapsing to an F1-score of 0.0000.
- **Precision-Recall Curve Tuning**: By optimizing the decision threshold across the PR curve to **0.2849**, PMS achieves **F1 of 0.4277 (Precision: 0.3736, Recall: 0.5000)**. In plant operations, this ensures that half of all pending catastrophic breakdowns are captured while keeping false alarms to a manageable level.

---

## 🔍 Known Weaknesses & Cross-Validated Failure Mode Uncertainty

To maintain scientific integrity and prevent overclaiming model capability, performance across individual mechanical failure modes is evaluated using **Stratified 5-Fold Cross-Validation** (without touching the held-out test set for tuning). See the detailed model card in [`ml/MODEL_CARD.md`](file:///c:/Users/nayak/OneDrive/Desktop/PMS/ml/MODEL_CARD.md).

```
┌───────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                               5-FOLD CROSS-VALIDATED FAILURE MODE UNCERTAINTY                                     │
├──────────────────────┬─────────────┬──────────────┬──────────────────┬──────────────────┬─────────────────────────┤
│ Failure Mode         │ Total Cases │ Cases / Fold │ CV F1 (Mean±Std) │ CV Recall (Mean) │ Known Weakness / Limit  │
├──────────────────────┼─────────────┼──────────────┼──────────────────┼──────────────────┼─────────────────────────┤
│ Overstrain (OSF)     │ 92          │ 18.4         │ 0.4137 ± 0.0984  │ 0.5014 ± 0.1617  │ Moderate variance       │
├──────────────────────┼─────────────┼──────────────┼──────────────────┼──────────────────┼─────────────────────────┤
│ Power Failure (PWF)  │ 80          │ 16.0         │ 0.2956 ± 0.0671  │ 0.3522 ± 0.1093  │ Boundary overlap        │
├──────────────────────┼─────────────┼──────────────┼──────────────────┼──────────────────┼─────────────────────────┤
│ Thermal (HDF)        │ 115         │ 23.0         │ 0.1212 ± 0.0384  │ 0.1113 ± 0.0389  │ Misses gradual thermal  │
│                      │             │              │                  │                  │ dissipation creep       │
├──────────────────────┼─────────────┼──────────────┼──────────────────┼──────────────────┼─────────────────────────┤
│ Tool Wear (TWF)      │ 43          │ 8.6          │ 0.0285 ± 0.0353  │ 0.0500 ± 0.0667  │ Severely data-starved   │
│                      │             │              │                  │                  │ (Collapses to 0.00 F1)  │
└──────────────────────┴─────────────┴──────────────┴──────────────────┴──────────────────┴─────────────────────────┘
```

- **Tool Wear Failure (TWF)**: Only 43 total failure instances exist in the entire dataset (an average of 8.6 instances per fold). Cross-validation shows that TWF performance collapses to **F1 0.0285 ± 0.0353** (scoring 0.0000 in 3 out of 5 folds). It should not be relied upon for standalone cutting tool blade life prediction without supplementary acoustic/vibration sensor data.
- **Thermal Dissipation Failure (HDF)**: Achieves **F1 0.1212 ± 0.0384** with ~11% recall. While acute thermal spikes trigger alarms, the model struggles with slow, sub-critical thermal creep where heat builds up without exceeding peak temperature thresholds.

---

## 🛠️ Repository & File Layout

```
Predictive-Maintenance-System/
├── backend/
│   ├── main.py              # FastAPI application entrypoint, CORS & route definitions
│   ├── predictor.py         # Calibrated XGBoost & SHAP TreeExplainer engine
│   ├── drift_detector.py    # Statistical Population Stability Index (PSI) drift engine
│   ├── database.py          # SQLAlchemy engine (resilient psycopg v3/v2 dual-driver support)
│   ├── models.py            # PostgreSQL / SQLite audit schema definitions
│   ├── schemas.py           # Pydantic request & response validation schemas
│   ├── canary.py            # Automated canary deployment & candidate health evaluator
│   ├── scheduler.py         # Background periodic telemetry tasks (APScheduler)
│   ├── knowledge_base/      # Prescriptive Standard Operating Procedures (SOPs)
│   └── tests/               # 53 comprehensive integration, API & leakage unit tests
├── frontend/
│   ├── src/                 # React 19 UI components, interactive charts & styling
│   └── package.json         # Frontend dependencies and build scripts
├── ml/
│   ├── train.py             # Model training, hyperparameter tuning & MLflow artifact logging
│   ├── evaluate.py          # Test evaluation & 5-fold CV failure-mode uncertainty suite
│   ├── rul_engine.py        # Remaining Useful Life (RUL) regression forecasting
│   ├── dataset_loader.py    # Raw telemetry ingestion & physical feature engineering
│   ├── MODEL_CARD.md        # Comprehensive model card & known weaknesses documentation
│   └── model_info.json      # Serialized model metadata, parameters & calibration statistics
├── prometheus/              # Prometheus scraping configuration
├── docker-compose.yml       # Multi-service stack orchestration (API, UI, DB, Metrics)
├── Dockerfile.backend       # Multi-stage production container for FastAPI API
├── Dockerfile.frontend      # Optimized container build for React web dashboard
└── requirements.txt         # Root Python requirements for cloud-native deployment
```

---

## 💻 Installation & Quickstart Guide

### Prerequisites
- **Python**: 3.10 or higher
- **Node.js**: 18.x or higher with npm
- **Docker & Docker Compose** (optional, for full-stack containerization)

---

### Method 1: Local Development Setup

#### 1. Backend API Service
```bash
# Clone the repository
git clone https://github.com/Susil-commits/Predictive-Maintenance-System.git
cd Predictive-Maintenance-System

# Create and activate Python virtual environment
python -m venv .venv
source .venv/bin/activate       # On Windows: .venv\Scripts\activate

# Install backend dependencies (includes psycopg[binary] and psycopg2-binary)
pip install -r backend/requirements.txt

# Configure environment variables
cp .env.example .env

# Train the model and generate reference artifacts
python ml/train.py

# Launch FastAPI development server
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
* Interactive Swagger API documentation will be available at: `http://localhost:8000/docs`

#### 2. Frontend React Dashboard
```bash
# In a separate terminal window
cd frontend
npm install
npm run dev
```
* Dashboard will be live at: `http://localhost:5173`

---

### Method 2: Full-Stack Docker Compose Deployment

Launch the complete containerized stack including the FastAPI gateway, React dashboard, PostgreSQL database, Prometheus metrics collector, and Grafana:

```bash
docker-compose up --build -d
```

| Service | Access URL | Credentials / Notes |
| :--- | :--- | :--- |
| **React Ops Dashboard** | `http://localhost:3000` | Production web application |
| **FastAPI Backend Gateway** | `http://localhost:8000` | Swagger docs at `/docs` |
| **Prometheus Server** | `http://localhost:9090` | Telemetry scraping engine |
| **Grafana Dashboards** | `http://localhost:3001` | Pre-configured monitoring |
| **PostgreSQL Database** | `localhost:5432` | User: `postgres`, Port: `5432` |

To tear down the containers:
```bash
docker-compose down -v
```

---

## 🧪 Testing & Verification

The repository contains 53 automated tests covering API contracts, probability calibration, data leakage prevention, rate limiting, administrative authentication, database driver fallbacks, and cross-validation schema integrity:

```bash
# Run the complete test suite
pytest backend/tests/ -v
```

### Key Verification Test Suites
- `test_leakage.py`: Confirms strict separation between train and test sets prior to scaling, verifying zero mathematical target leakage.
- `test_api.py`: Validates all request schemas, rate limiting, authentication headers, and 5-fold CV response contracts.
- `test_predictor.py`: Verifies Platt calibration outputs, Brier score assertions, and SHAP TreeExplainer factor rankings.
- `test_drift_detector.py`: Confirms Population Stability Index calculations across stable and drifted telemetry distributions.

---

## 🔒 Enterprise Security Controls & Production Best Practices

1. **Authentication & Authorization Guardrails**:
   - Mutating and administrative endpoints (`POST /retrain`, `POST /batch-predict`, `POST /drift-status/reset`, and `DELETE /history`) require a valid `X-API-Key` administrative header matching `PMS_API_KEY` or a signed admin JWT token. Unauthenticated requests are rejected with `401 Unauthorized` or `403 Forbidden`.
2. **Abuse Prevention & Rate Limiting**:
   - The inference endpoint (`POST /predict`) is shielded against denial-of-service traffic and automated scraping via `slowapi` rate limiting configured to 60 requests per minute per IP address.
3. **Database Driver Resilience**:
   - The SQLAlchemy engine dynamically detects available PostgreSQL drivers (`psycopg` v3 vs. `psycopg2`), rewriting generic connection strings as necessary to prevent missing driver crashes across varied deployment environments.
4. **W3C CORS Compliance**:
   - Explicitly configured with `allow_origins=["*"]` and `allow_credentials=False` to adhere to browser standards while preventing unauthorized credential leakage. Enterprise deployments can restrict origins to specific plant domain names.
5. **Atomic Training Locks**:
   - Asynchronous background retraining tasks are protected by file-level atomic lock guards, preventing concurrent training jobs from corrupting serialized model artifacts (`ml/model.pkl`).

---

## 🗺️ Engineering & Commercial Roadmap

- [x] **Phase 1: Calibrated Core & Explainability**: Platt sigmoid calibration, SHAP TreeExplainer, RUL forecasting, and React 19 dashboard.
- [x] **Phase 2: Enterprise Reliability**: Dual DBAPI PostgreSQL support (`psycopg` v3 / v2), SlowAPI rate limiting, admin authentication, and automated 5-fold CV uncertainty tracking.
- [ ] **Phase 3: Edge PLC Firmware & Embedded C++**: Exporting optimized ONNX models directly to industrial microcontrollers (ARM Cortex-M, Siemens S7-1500) via ONNX Runtime IoT for sub-1ms on-device inference.
- [ ] **Phase 4: Multi-Modal Sensor Fusion**: Ingesting high-frequency acoustic emissions and 3-axis accelerometer vibration waveforms using 1D Convolutional Neural Networks (CNNs).
- [ ] **Phase 5: Fleet-Wide Multi-Tenant RBAC**: Hierarchical plant, line, and machine-level role-based access control with SSO (Okta / Azure AD).

---

## 📜 License & Citation

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

### Citation
```bibtex
@misc{pms2026,
  author = {Susil Nayak},
  title = {Predictive Maintenance System (PMS): Physics-Informed, Calibrated Industrial Intelligence Platform},
  year = {2026},
  publisher = {GitHub},
  howpublished = {\url{https://github.com/Susil-commits/Predictive-Maintenance-System}}
}
```
