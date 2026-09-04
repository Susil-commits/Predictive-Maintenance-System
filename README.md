# Predictive Maintenance System (PMS)

[![PMS CI Pipeline](https://github.com/Susil-commits/Predictive-Maintenance-System/actions/workflows/ci.yml/badge.svg)](https://github.com/Susil-commits/Predictive-Maintenance-System/actions/workflows/ci.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![XGBoost](https://img.shields.io/badge/XGBoost-Calibrated-EB5424)](https://xgboost.readthedocs.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Live Deployments & Quick Links:**
> - 🌐 **Production Frontend (Vercel)**: [https://pms-frontend.vercel.app](https://pms-frontend.vercel.app) *(or your deployed Vercel URL)*
> - ⚡ **Production API (Render)**: [https://pms-backend.onrender.com](https://pms-backend.onrender.com)
> - 📖 **Interactive Swagger Docs**: [https://pms-backend.onrender.com/docs](https://pms-backend.onrender.com/docs)
> - 📊 **Prometheus Metrics**: [https://pms-backend.onrender.com/metrics](https://pms-backend.onrender.com/metrics)

An end-to-end machine learning platform for industrial equipment predictive maintenance. The system analyzes operating telemetry in real time to assess equipment failure risk, delivers statistically calibrated probabilities via `CalibratedClassifierCV`, generates explainable diagnostics using SHAP, monitors statistical data drift, logs inference records, and provides operational visibility through a React dashboard and Prometheus/Grafana metrics.

---

## Features

- **Calibrated Failure Risk Prediction**: Real-time failure probability and risk tier classification (`LOW`, `HIGH`) using hyperparameter-tuned XGBoost wrapped in `CalibratedClassifierCV` (Platt sigmoid calibration) to ensure predicted probabilities reflect true empirical risk.
- **Rate-Limited Inference API**: Protected by `slowapi` rate limiting (60 requests/minute per client) to prevent abuse and denial-of-service.
- **Administrative Key Authentication**: Mutating operations (`DELETE /history`, `POST /retrain`) are secured by an `X-API-Key` administrative header check.
- **Model Explainability**: Per-prediction feature attribution via SHAP (SHapley Additive exPlanations) TreeExplainer, identifying key operational drivers behind elevated risk scores.
- **Multi-Model Benchmark**: Comprehensive performance comparison across Logistic Regression, Random Forest, LightGBM, uncalibrated XGBoost, and calibrated XGBoost.
- **Data Drift Monitoring**: Population Stability Index (PSI) tracking comparing incoming telemetry distributions against baseline reference distributions, triggering automated alerts when PSI exceeds industry thresholds (<0.10 stable, 0.10–0.25 warning, ≥0.25 significant drift).
- **Inference Persistence**: Structured persistence of all inference requests, predicted risk scores, and contributing factors in PostgreSQL (with automatic SQLite fallback).
- **Interactive Dashboard**: Modern React + Vite frontend featuring real-time telemetry inputs, preset scenario loading, historical audit logging, and drift analysis.
- **Production Observability**: Prometheus instrumentation (`/metrics` endpoint) and pre-configured Grafana dashboards for throughput and latency tracking.

---

## Architecture

```
                      Industrial Telemetry Input
                     (Temperature, RPM, Pressure,
                    Vibration, Operating Hours)
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │      FastAPI Server     │
                    └────────────┬────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         ▼                       ▼                       ▼
┌──────────────────┐   ┌───────────────────┐   ┌──────────────────┐
│   XGBoost Model  │   │  SHAP Explainer   │   │  Drift Detector  │
│ (Risk / Prob.)   │   │ (TreeExplainer)   │   │ (PSI Drift Engine)│
└────────┬─────────┘   └─────────┬─────────┘   └────────┬─────────┘
         │                       │                      │
         └───────────────────────┼──────────────────────┘
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │ PostgreSQL / SQLite   │
                     └───────────┬───────────┘
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
       ┌───────────────────┐           ┌───────────────────┐
       │  React Dashboard  │           │ Prometheus/Grafana│
       └───────────────────┘           └───────────────────┘
```

---

## API Reference

### Endpoints

| Method | Path | Auth / Limits | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/predict` | Rate-limited (`60/min`) | Ingests telemetry, returns calibrated failure risk, probability, and SHAP factors |
| `GET` | `/drift-status` | Public | Evaluates Population Stability Index (PSI) drift against baseline reference |
| `POST` | `/drift-status/reset` | Public | Reloads baseline reference statistics from model training |
| `GET` | `/history` | Public | Returns recent inference records and predictions |
| `DELETE` | `/history` | **Admin API Key** (`X-API-Key`) | Clears prediction audit history (for development & demo reset) |
| `POST` | `/retrain` | **Admin API Key** (`X-API-Key`) | Triggers background model retraining and hot-reload upon drift |
| `GET` | `/model-info` | Public | Returns active model metadata, parameters, calibration metrics, and benchmarks |
| `GET` | `/metrics` | Public | Exposes Prometheus application and drift metrics |
| `GET` | `/health` | Public | Health check endpoint returning system, model, and DB status |

### Example Request (`POST /predict`)

```json
{
  "temperature": 92.4,
  "rpm": 2800,
  "pressure": 31.5,
  "vibration": 0.64,
  "operating_hours": 4820
}
```

### Example Response

```json
{
  "failure_risk": "HIGH",
  "probability": 0.9734,
  "maintenance_required": true,
  "decision_threshold": 0.8367,
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

---

## Model Training & Evaluation

The model is trained on the UCI AI4I 2020 Predictive Maintenance Dataset with physical coupling indicators (thermal stress index, mechanical power demand, and harmonic pressure ratio). Hyperparameters are tuned using 3-fold stratified cross-validation via `GridSearchCV`, utilizing `scale_pos_weight = (neg_count / pos_count)` to address severe class imbalance.

### Evaluation Results

| Model | ROC-AUC | F1-Score | Brier Score Loss | Recall | Precision | Configuration / Notes |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Logistic Regression** (Baseline) | 0.8368 | 0.2017 | 0.1398 | 0.7794 | 0.1170 | Standard scaling, balanced weights |
| **Random Forest** | 0.9423 | 0.3897 | 0.0529 | 0.7794 | 0.2585 | 150 estimators, balanced class weights |
| **LightGBM** | 0.9389 | 0.4142 | 0.0342 | 0.7353 | 0.2874 | 150 estimators, `scale_pos_weight: 28.21` |
| **XGBoost** (Uncalibrated, 0.50 Cutoff) | 0.9398 | 0.1111 | 0.0638 | 0.0588 | 1.0000 | GridSearchCV tuned, uncalibrated probabilities |
| **Calibrated XGBoost** (PR-Tuned Production) | **0.9489** | **0.4966** | **0.0237** | **0.5294** | **0.4675** | `CalibratedClassifierCV` (sigmoid, cv=3), threshold `0.2619` |

### Probability Calibration & Brier Score Loss

- **Why Calibration Matters**: While tree-based models (like XGBoost and Random Forest) yield strong discriminative ranking (high ROC-AUC), their raw output scores are frequently distorted by extreme gradient boosting iterations and class reweighting (`scale_pos_weight`). Consequently, a predicted score of "0.70" does not mean a 70% chance of failure—it is merely a relative ranking score.
- **Platt Sigmoid Scaling (`CalibratedClassifierCV`)**: Using 3-fold cross-validated Platt scaling maps raw decision values through a calibrated sigmoid transformation, aligning predicted probabilities with true empirical event frequencies.
- **Quantifiable Error Reduction**: The Brier Score Loss drops from **0.0638** (uncalibrated XGBoost) to **0.0237** (calibrated XGBoost)—a **62.9% reduction in probabilistic error**. This ensures that threshold tuning operates on trustworthy probabilities rather than arbitrary monotonic ranks.

### Class Imbalance & Threshold Tuning Insights

> **"AUC 0.94 but low precision is class imbalance + default threshold, not a broken model"**

- **Class Imbalance Dynamics**: In industrial equipment telemetry, failures represent ~3.4% of total observations (9,663 normal vs. 342 failure records, an approximate 28:1 ratio).
- **Impact of `scale_pos_weight`**: Setting `scale_pos_weight = (neg_count / pos_count)` (28.21) scales the gradient loss of positive minority instances by 28.2x, preventing the model from collapsing to the majority class.
- **Precision-Recall Curve Tuning**: Instead of the default 0.50 cutoff, the decision threshold is tuned across the Precision-Recall curve to maximize the $F_1$-score. Tuning to **0.2619** on calibrated probabilities elevates $F_1$ to **0.4966** while maintaining an exceptional ROC-AUC of **0.9489**.
- **Operational Reality & Honest Metric Assessment**: At the tuned threshold, the model achieves **Precision 0.47 / Recall 0.53 / F1 0.50** (alongside ROC-AUC 0.95 and Brier 0.0237). In an operational environment, this means roughly half of flagged "HIGH risk" warnings are actionable alerts. Rather than claiming 99% off-the-shelf accuracy on an imbalanced dataset, this demonstrates rigorous MLOps practice—transparently calibrating probabilities and navigating the precision/recall tradeoff.

### Next-Step Production Enhancements

1. **SMOTE / ADASYN**: Introduce Synthetic Minority Over-sampling Technique (SMOTE) or ADASYN to interpolate synthetic failure instances along feature boundaries, complementing algorithmic weight scaling.
2. **Cost-Sensitive Learning**: Formalize an operational cost matrix balancing the financial cost of an unscheduled catastrophic downtime event ($C_{\text{FN}}$) against the marginal cost of a preventive inspection ($C_{\text{FP}}$) to directly optimize business expected value.
3. **More Failure Samples**: Ingest real-world telemetry from extended fleet deployments, accelerated wear test rigs, and hardware failure simulations to augment the empirical representation of mechanical failure modes.

Experiment metrics, reference statistics, serialized artifacts, and the Precision-Recall plot are tracked via MLflow and exported to `ml/model.pkl`, `ml/scaler.pkl`, `ml/pr_curve.png`, and `ml/reference_stats.json`.

---

## Project Structure

```
Predictive-Maintenance-System/
├── backend/
│   ├── main.py              # FastAPI application entrypoint & routing
│   ├── predictor.py         # XGBoost & SHAP inference engine
│   ├── drift_detector.py    # Statistical drift detection module
│   ├── database.py          # SQLAlchemy engine and session management
│   ├── models.py            # Database schema definitions
│   ├── schemas.py           # Pydantic request/response schemas
│   └── tests/               # API integration test suite
├── frontend/
│   ├── src/                 # React UI components, dashboard & styles
│   └── package.json         # Frontend dependencies & scripts
├── ml/
│   ├── train.py             # Model training, tuning, and MLflow logging
│   ├── dataset_loader.py    # Ingestion & feature preprocessing
│   └── model_info.json      # Model metadata and evaluation metrics
├── prometheus/              # Prometheus scraping configuration
├── docker-compose.yml       # Multi-service stack deployment
└── Dockerfile.backend       # Container definition for FastAPI service
```

---

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm
- Docker and Docker Compose (optional for containerized deployment)

### 1. Local Backend Setup

```bash
# Clone repository
git clone https://github.com/Susil-commits/Predictive-Maintenance-System.git
cd Predictive-Maintenance-System

# Set up virtual environment
python -m venv .venv
source .venv/bin/activate    # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt

# Configure environment variables
cp .env.example .env

# Train the model and generate reference artifacts
python ml/train.py

# Start FastAPI server
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Interactive OpenAPI documentation is accessible at `http://localhost:8000/docs`.

### 2. Local Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Dashboard will be accessible at `http://localhost:5173`.

---

## Containerized Deployment (Docker Compose)

To launch the complete infrastructure stack including the API, frontend, PostgreSQL, Prometheus, and Grafana:

```bash
docker-compose up --build -d
```

| Service | URL |
| :--- | :--- |
| **Frontend Dashboard** | `http://localhost:3000` |
| **FastAPI Backend** | `http://localhost:8000` |
| **Prometheus Server** | `http://localhost:9090` |
| **Grafana Monitoring** | `http://localhost:3001` |

---

## Testing

Execute the backend integration and API test suite:

```bash
pytest backend/tests/test_api.py -v
```

---

## Security Controls & Production Roadmap

1. **Authentication & Authorization (Active Control / Resolved)**:
   - **Implemented**: Mutating and resource-intensive administrative operations (`DELETE /history` to purge audit records and `POST /retrain` to trigger background retraining) are guarded by an `X-API-Key` administrative header matching `PMS_API_KEY`. Unauthenticated requests are rejected with `401 Unauthorized`.
   - **Production Roadmap**: Introduce OAuth2/OIDC JWT tokens with fine-grained role-based access control (RBAC) for multi-tenant organizational hierarchy.
2. **Rate Limiting & Abuse Prevention (Active Control / Resolved)**:
   - **Implemented**: The core inference endpoint (`POST /predict`) is shielded against automated abuse and traffic bursts via `slowapi` rate limiting (60 requests per minute per IP), answering security concerns before they become production vulnerabilities.
3. **CORS Policy & Origin Isolation**:
   - Configured with `allow_origins=["*"]` and `allow_credentials=False` to strictly satisfy W3C CORS standards while avoiding wildcard credential rejection in modern browsers. Enterprise deployments should restrict `allow_origins` to explicitly enumerated company domains.
4. **Training Worker Isolation**:
   - **Current State**: Retraining runs as an asynchronous background subprocess on the application host.
   - **Production Roadmap**: Decouple heavy training workloads from the inference API by dispatching tasks to dedicated distributed worker queues (e.g., Celery, Redis Queue, Argo Workflows, or Kubeflow).
5. **Telemetry Realism & Dataset Size**:
   - Synthetic telemetry provides clean statistical properties but lacks non-stationary industrial sensor degradation patterns, intermittent communication drops, and multi-mode mechanical failure progressions present in field deployments.

---

## License

This project is licensed under the MIT License.
