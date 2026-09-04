# Predictive Maintenance System (PMS)

An end-to-end machine learning platform for industrial equipment predictive maintenance. The system analyzes operating telemetry in real time to assess equipment failure risk, generates explainable diagnostics using SHAP, monitors statistical data drift, logs inference records, and provides operational visibility through a React dashboard and Prometheus/Grafana metrics.

---

## Features

- **Failure Risk Prediction**: Real-time failure probability and risk tier classification (`LOW`, `MEDIUM`, `HIGH`) using hyperparameter-tuned XGBoost.
- **Model Explainability**: Per-prediction feature attribution via SHAP (SHapley Additive exPlanations) TreeExplainer, identifying key operational drivers behind elevated risk scores.
- **Data Drift Detection**: Automated statistical drift checks (Kolmogorov-Smirnov test and Wasserstein distance) comparing incoming telemetry batches against baseline reference distributions.
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
│ (Risk / Prob.)   │   │ (TreeExplainer)   │   │ (KS-Test / Drift)│
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
| `GET` | `/drift` | Runs statistical drift analysis against baseline reference data |
| `GET` | `/history` | Returns recent inference records and predictions |
| `GET` | `/model-info` | Returns active model metadata, parameters, and baseline metrics |
| `GET` | `/metrics` | Exposes Prometheus application metrics |
| `GET` | `/health` | Health check endpoint |

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
  "probability": 0.9616,
  "maintenance_required": true,
  "contributing_factors": [
    {
      "factor": "RPM",
      "impact": 1.8775,
      "importance": 1.8775,
      "description": "Rotational speed and dynamic rotor stresses"
    },
    {
      "factor": "Operating Hours",
      "impact": 1.4799,
      "importance": 1.4799,
      "description": "Cumulative service wear and fatigue aging"
    },
    {
      "factor": "Vibration",
      "impact": 0.5538,
      "importance": 0.5538,
      "description": "Harmonic oscillation and mechanical instability"
    },
    {
      "factor": "Pressure",
      "impact": -0.4172,
      "importance": 0.4172,
      "description": "Hydraulic / pneumatic system pressure loading"
    },
    {
      "factor": "Temperature",
      "impact": -0.1763,
      "importance": 0.1763,
      "description": "Thermal stress on cooling and lubrication circuits"
    }
  ]
}
```

---

## Model Training & Evaluation

The model is trained on the UCI AI4I 2020 Predictive Maintenance Dataset with physical coupling indicators (thermal stress index, mechanical power demand, and harmonic pressure ratio). Hyperparameters are tuned using 3-fold stratified cross-validation via `GridSearchCV`, utilizing `scale_pos_weight` to address class imbalance and maximize detection recall.

### Evaluation Results

| Model | ROC-AUC | F1-Score | Recall | Precision | Configuration |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Logistic Regression** (Baseline) | 0.8368 | 0.2017 | 0.7794 | 0.1170 | Standard scaling, L2 regularization |
| **Random Forest** | 0.9423 | 0.3897 | 0.7794 | 0.2585 | 150 estimators, balanced class weights |
| **XGBoost** (Production) | **0.9416** | **0.3382** | **0.8529** | **0.2109** | `max_depth: 3`, `n_estimators: 100`, `learning_rate: 0.06` |

Experiment metrics, reference statistics, and serialized artifacts are tracked via MLflow and exported to `ml/model.pkl`, `ml/scaler.pkl`, and `ml/reference_stats.json`.

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

## License

This project is licensed under the MIT License.
