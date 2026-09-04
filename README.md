# 🔧 Predictive Maintenance System (PMS)

An end-to-end industrial vehicle and heavy machinery predictive maintenance platform. Given sensor operating telemetry, the system evaluates failure risk, computes failure probability, provides explainable diagnostics using **SHAP (SHapley Additive exPlanations)**, logs every inference into **PostgreSQL**, and visualizes real-time metrics on an interactive **React** dashboard.

---

## 🏛️ Architecture

```
Public Industrial Dataset (UCI AI4I 2020)
                  ↓
Data Cleaning & Industrial Telemetry Mapping
                  ↓
Exploratory Data Analysis (EDA)
                  ↓
Feature Engineering (Dynamic Harmonic & Stress Indices)
                  ↓
Model Hierarchy:
  • Logistic Regression (Baseline)
  • Random Forest (Ensemble)
  • XGBoost (Final Production Model)
                  ↓
SHAP TreeExplainer Attribution
                  ↓
FastAPI Backend (POST /predict, GET /health, GET /model-info, GET /history, GET /metrics)
                  ↓
PostgreSQL Audit Log (Supabase / Local)
                  ↓
React + Vite Interactive Dashboard
```

---

## 📊 Telemetry Interface

### Input Schema (`POST /predict`)
```json
{
  "temperature": 92.4,
  "rpm": 2800,
  "pressure": 31.5,
  "vibration": 0.64,
  "operating_hours": 4820
}
```

### Output Schema
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

## 📈 Model Performance & Validation

The telemetry mapping strictly models physical machine coupling (torque, tool wear, thermal stress) without artificial label injection, preventing data leakage. Models are tuned using 3-fold stratified cross-validation via `GridSearchCV`.

| Model | ROC-AUC | F1-Score | Recall | Precision | Notes |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Logistic Regression** (Baseline) | 0.8368 | 0.2017 | 0.7794 | 0.1170 | Linear baseline with standard scaling |
| **Random Forest** (Ensemble) | 0.9423 | 0.3897 | 0.7794 | 0.2585 | 150 trees, balanced class weights |
| **XGBoost (Tuned Production)** | **0.9416** | **0.3382** | **0.8529** | **0.2109** | **Best parameters:** `max_depth: 3, n_estimators: 100, learning_rate: 0.06` |

- **High Recall Focus**: In predictive maintenance, missing an equipment failure (false negative) is catastrophic. The model achieves **85.3% recall** on the failure class using cost-sensitive positive weighting (`scale_pos_weight`).
- **Explainability**: SHAP TreeExplainer delivers exact per-instance log-odds attribution, highlighting primary failure drivers (RPM dynamics, cumulative wear, and harmonic vibration) for field engineers.

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+
- Node.js 18+ and npm
- PostgreSQL (or automated SQLite fallback)

### 2. Backend Setup
```bash
# Clone repository
git clone https://github.com/Susil-commits/Predictive-Maintenance-System.git
cd Predictive-Maintenance-System

# Create virtual environment
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# or .\.venv\Scripts\activate on Windows

# Install dependencies
pip install -r backend/requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your DATABASE_URL

# Train ML model & download dataset
python ml/train.py

# Start FastAPI server
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Interactive Swagger API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)

### 3. Frontend Dashboard Setup
```bash
cd frontend
npm install
npm run dev
```

Dashboard UI will be live at: [http://localhost:5173](http://localhost:5173)

---

## 🐳 Docker Deployment

To launch the full production stack (PostgreSQL, FastAPI Backend, React Frontend, Prometheus, and Grafana):

```bash
docker-compose up --build -d
```

- **Frontend Dashboard**: [http://localhost:3000](http://localhost:3000)
- **API Backend**: [http://localhost:8000](http://localhost:8000)
- **Prometheus Metrics**: [http://localhost:9090](http://localhost:9090)
- **Grafana Monitoring**: [http://localhost:3001](http://localhost:3001)

---

## 🧪 Testing

Run backend integration test suite:
```bash
pytest backend/tests/test_api.py -v
```

---

## 📄 License
MIT License
