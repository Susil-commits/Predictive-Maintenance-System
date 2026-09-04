# Predictive Maintenance System (PMS)

An end-to-end machine learning platform for industrial equipment predictive maintenance. The system analyzes operating telemetry in real time to assess equipment failure risk, generates explainable diagnostics using SHAP, monitors statistical data drift, logs inference records, and provides operational visibility through a React dashboard and Prometheus/Grafana metrics.

---

## Features

- **Failure Risk Prediction**: Real-time failure probability and risk tier classification (`LOW`, `MEDIUM`, `HIGH`) using hyperparameter-tuned XGBoost.
- **Model Explainability**: Per-prediction feature attribution via SHAP (SHapley Additive exPlanations) TreeExplainer, identifying key operational drivers behind elevated risk scores.
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

| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/predict` | Ingests telemetry, returns failure risk, probability, and SHAP factors |
| `GET` | `/drift-status` | Evaluates Population Stability Index (PSI) drift against baseline reference |
| `POST` | `/drift-status/reset` | Reloads baseline reference statistics from model training |
| `GET` | `/history` | Returns recent inference records and predictions |
| `DELETE` | `/history` | Clears prediction audit history (for development & demo reset) |
| `POST` | `/retrain` | Triggers background model retraining and hot-reload upon drift |
| `GET` | `/model-info` | Returns active model metadata, parameters, and baseline metrics |
| `GET` | `/metrics` | Exposes Prometheus application and drift metrics |
| `GET` | `/health` | Health check endpoint returning system, model, and DB status |

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

| Model | ROC-AUC | F1-Score | Recall | Precision | Configuration |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Logistic Regression** (Baseline) | 0.8368 | 0.2017 | 0.7794 | 0.1170 | Standard scaling, L2 regularization |
| **Random Forest** | 0.9423 | 0.3897 | 0.7794 | 0.2585 | 150 estimators, balanced class weights |
| **XGBoost** (Default 0.50 Cutoff) | 0.9398 | 0.3583 | 0.8088 | 0.2301 | `scale_pos_weight: 28.21`, default 0.50 cutoff |
| **XGBoost** (PR-Tuned Production) | **0.9398** | **0.4462** | **0.4265** | **0.4677** | `scale_pos_weight: 28.21`, optimal threshold `0.8367` |

### Class Imbalance & Threshold Tuning Insights

> **"AUC 0.94 but low precision is class imbalance + default threshold, not a broken model"**

- **Class Imbalance Dynamics**: In industrial equipment telemetry, failures represent ~3.4% of total observations (9,663 normal vs. 342 failure records, an approximate 28:1 ratio).
- **Impact of `scale_pos_weight`**: Setting `scale_pos_weight = (neg_count / pos_count)` (28.21) scales the gradient loss of positive minority instances by 28.2x, preventing the model from collapsing to the majority class. However, this shifts the raw predicted probabilities upward.
- **Why Default 0.5 Cutoff Underperforms**: Using the unadjusted 0.50 cutoff captures high recall (80.88%) but incurs false positives, yielding a low precision of 23.01% and an F1 score of 0.3583.
- **Precision-Recall Curve Tuning**: Instead of the default 0.50 cutoff, the decision threshold is tuned across the Precision-Recall curve to maximize the $F_1$-score. Tuning to **0.8367** elevates Precision from **0.2301 to 0.4677** (+103% improvement) and increases overall $F_1$ from **0.3583 to 0.4462** while maintaining an excellent ROC-AUC of **0.9398**.
- **Operational Reality & Honest Metric Assessment**: At the tuned threshold, the model achieves **Precision 0.47 / Recall 0.43 / F1 0.45** (alongside ROC-AUC 0.94). In an operational environment, this means roughly half of flagged "HIGH risk" warnings are false alarms, and over half of actual failures may still be missed. Rather than claiming off-the-shelf production readiness, this reflects legitimate, explainable boundaries of a small synthetic dataset (~340 total failure records). It demonstrates rigorous MLOps practice—transparently navigating the precision/recall tradeoff rather than chasing misleading accuracy.

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

## Known Limitations & Production Roadmap

This system is built as a technical demonstration and reference architecture for industrial ML systems. The following intentional trade-offs and roadmap items are recognized:

1. **Authentication & Authorization (Zero-Trust API)**:
   - **Current State**: Endpoints such as `DELETE /history` (which purges inference history) and `POST /retrain` (which initiates background model retraining) are currently unauthenticated to facilitate immediate local development and interactive review.
   - **Production Roadmap**: Introduce API Key or OAuth2 / JWT bearer authentication, restricting mutating or administrative operations (`DELETE /history`, `POST /retrain`, `/drift-status/reset`) to authorized MLOps administrators and automated pipelines.
2. **CORS Policy & Origin Isolation**:
   - Configured with `allow_origins=["*"]` and `allow_credentials=False` to strictly satisfy W3C CORS standards while avoiding wildcard credential rejection in modern browsers. Enterprise deployments should restrict `allow_origins` to explicitly enumerated company domains.
3. **Training Worker Isolation**:
   - **Current State**: Retraining runs as an asynchronous background subprocess on the application host.
   - **Production Roadmap**: Decouple heavy training workloads from the inference API by dispatching tasks to dedicated distributed worker queues (e.g., Celery, Redis Queue, Argo Workflows, or Kubeflow).
4. **Telemetry Realism & Dataset Size**:
   - Synthetic telemetry provides clean statistical properties but lacks non-stationary industrial sensor degradation patterns, intermittent communication drops, and multi-mode mechanical failure progressions present in field deployments.

---

## License

This project is licensed under the MIT License.
