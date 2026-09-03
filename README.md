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
  "probability": 0.9999,
  "maintenance_required": true,
  "contributing_factors": [
    {
      "factor": "Vibration",
      "impact": 5.4531,
      "description": "Harmonic oscillation and mechanical instability"
    },
    {
      "factor": "RPM",
      "impact": 2.8429,
      "description": "Rotational speed and dynamic rotor stresses"
    },
    {
      "factor": "Temperature",
      "impact": 0.7525,
      "description": "Thermal stress on cooling and lubrication circuits"
    },
    {
      "factor": "Pressure",
      "impact": 0.4188,
      "description": "Hydraulic / pneumatic system pressure loading"
    }
  ]
}
```

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
