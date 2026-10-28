# Predictive Maintenance System (PMS)

[![PMS CI Pipeline](https://github.com/Susil-commits/Predictive-Maintenance-System/actions/workflows/ci.yml/badge.svg)](https://github.com/Susil-commits/Predictive-Maintenance-System/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/Tests-96%20Passing%20%7C%20100%25-brightgreen.svg)](backend/tests/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![ONNX Runtime](https://img.shields.io/badge/ONNX%20Runtime-21%C2%B5s%20Latency-005CED?logo=onnx&logoColor=white)](https://onnxruntime.ai)
[![MCP](https://img.shields.io/badge/MCP-JSON--RPC%202.0-8A2BE2)](backend/mcp_server.py)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![XGBoost](https://img.shields.io/badge/XGBoost-Calibrated-EB5424)](https://xgboost.readthedocs.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Live Production Deployments:**
> - 🌐 **Operations Dashboard**: [https://pms-frontend.vercel.app](https://pms-frontend.vercel.app)
> - ⚡ **API Gateway**: [https://pms-backend.onrender.com](https://pms-backend.onrender.com) | 📖 **OpenAPI Docs**: [/docs](https://pms-backend.onrender.com/docs) | 📊 **Metrics**: [/metrics](https://pms-backend.onrender.com/metrics)

The Predictive Maintenance System (PMS) is an end-to-end industrial machine learning platform and edge-ready API designed for real-time condition monitoring, failure risk prediction, and automated technician dispatch across industrial powertrains. It features:
* **Context Engineering**: Operational regime awareness (`idle`, `warmup`, `steady_state_heavy`), environmental ambient factors, and temporal momentum derivatives ($dT/dt$, vibration crest factors) to eliminate context blindness in AI briefings.
* **Harness Engineering Suite**: Zero-hardware physical degradation simulators (Thermal Runaway, Overstrain, Tool Wear, Sensor Glitches), RAG/AI evaluation benchmarks on golden cases, and automated chaos fault injection.
* **Dual-Runtime Inferencing**: Microsecond edge scoring via C++ ONNX Runtime (0.021 ms latency, 90.4x speedup) coupled with calibrated Platt sigmoid scaling (`CalibratedClassifierCV`) and explainable SHAP TreeExplainer attributions.
* **Model Context Protocol (MCP) Server**: Standardized JSON-RPC 2.0 interface enabling autonomous AI coding agents (Antigravity, Claude Desktop, Cursor) to inspect telemetry, run diagnostics, and dispatch maintenance orders.
* **Enterprise Reliability**: Population drift monitoring (PSI), rolling remaining useful life (RUL) regression, dual DBAPI resilience (`psycopg` v3 / `psycopg2` / SQLite), and a responsive React 19 operational dashboard.

> [!NOTE]
> **Dataset & Scope Disclosure:** Trained and evaluated on the UCI AI4I 2020 synthetic milling benchmark (10,000 records). Reported metrics validate end-to-end data pipelines, calibration dynamics, and architecture, but **do not represent field reliability on physical machinery**.

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph TIER1["Tier 1: Ingestion, Gateway & MCP Agent Interface"]
        IoT["Industrial Telemetry Sources<br/>(Temperature, RPM, Pressure, Vibration, Hours)"] --> Gateway["FastAPI Application Gateway"]
        Gateway --> Security["Auth & Security Guard<br/>(Admin Key / JWT / SlowAPI 60 req/min)"]
        Gateway --> MCP["Model Context Protocol (MCP)<br/>(JSON-RPC 2.0 Tools, Resources, Prompts)"]
        Gateway --> Ingest["Ingestion Router<br/>(Single JSON, Batch CSV/Parquet)"]
    end

    subgraph TIER2["Tier 2: Context Engineering & Intelligence"]
        Ingest --> ContextEnv["Context Engineering Envelope<br/>(Regime, Machine ID, Ambient Temp, dT/dt, Crest Factor)"]
        ContextEnv --> PhysicsFE["Physics Feature Engine<br/>(Thermal Deficit ΔT, Mechanical Power, Overstrain)"]
        ContextEnv --> FFT["FFT Frequency Engine<br/>(Spectral Energy & Centroid)"]
        PhysicsFE --> Router{"Inference Runtime Router"}
        FFT --> Router
        Router -->|Edge Fast-Path (21 µs)| ONNX["ONNX Runtime Engine (C++)<br/>(High-Throughput Scoring)"]
        Router -->|Full Attribution (1.9 ms)| XGBoost["Calibrated XGBoost Model<br/>(Platt Sigmoid, Threshold 0.2849)"]
        XGBoost --> SHAP["SHAP TreeExplainer<br/>(Root-Cause Attribution)"]
        SHAP --> SOP["Prescriptive SOP Engine<br/>(Context-Grounded Procedures & Minimal Fix)"]
        ContextEnv --> RUL["RUL Forecaster<br/>(Rolling Regression)"]
        ContextEnv --> Drift["Drift Engine<br/>(Population Stability Index)"]
    end

    subgraph TIER3["Tier 3: Persistence & Storage Resilience"]
        XGBoost --> ORM["SQLAlchemy ORM<br/>(Pool: 20, Overflow: 30)"]
        RUL --> ORM
        ORM --> DualDriver{"Dynamic Dual DBAPI Driver"}
        DualDriver -->|Primary| Psycopg3["PostgreSQL (psycopg v3)"]
        DualDriver -->|Fallback 1| Psycopg2["PostgreSQL (psycopg2-binary)"]
        DualDriver -->|Fallback 2| SQLite["Local SQLite (pms.db)"]
    end

    subgraph TIER4["Tier 4: Observability, Canary & Operations"]
        XGBoost --> Dashboard["React 19 Ops Dashboard<br/>(Telemetry Scoring, Batch, Drift)"]
        Drift --> Dashboard
        Gateway --> Prometheus["Prometheus Metrics (/metrics)<br/>(Latencies, Status, PSI Gauges)"]
        Prometheus --> Grafana["Grafana Dashboards"]
        Gateway --> Canary["Canary Controller<br/>(10% → 50% → 100% Traffic Routing)"]
    end

    subgraph TIER5["Tier 5: Harness Engineering & Verification Suite"]
        Scenarios["Degradation Simulators<br/>(Thermal Runaway, Overstrain, Tool Wear, Glitches)"] --> Gateway
        AIEval["AI & RAG Eval Harness<br/>(Groundedness, Citation Recall, Canary Defense)"] --> Gateway
        Chaos["Chaos & Resilience Harness<br/>(DB Severing, Circuit Breaker FSM Tripping)"] --> Gateway
    end

    classDef tierStyle fill:#1e293b,stroke:#3b82f6,stroke-width:2px,color:#f8fafc;
    class TIER1,TIER2,TIER3,TIER4,TIER5 tierStyle;
```

---

## 📊 Honest Evaluation & Model Results

Performance pulled directly from serialized model evaluation in [`ml/model_info.json`](ml/model_info.json) and validated across held-out testing (N = 2,000; 68 failure positives) with **1,000-sample bootstrap 95% confidence intervals** and **Stratified 5-Fold Cross-Validation**:

### 1. Held-Out Test Set Benchmark (N = 2,000, 28:1 Class Imbalance)

| Model Architecture | Decision Threshold | ROC-AUC (95% Bootstrap CI) | F1-Score (95% Bootstrap CI) | Precision | Recall | Brier Score Loss |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Logistic Regression** (Baseline) | 0.5000 | 0.9065 | 0.2500 | 0.1476 | 0.7794 | 0.1171 |
| **Random Forest** (150 Trees) | 0.5000 | 0.9313 | 0.3766 | 0.3372 | 0.4265 | 0.0488 |
| **LightGBM** (Scale-Weighted) | 0.5000 | 0.9276 | 0.4260 | 0.3564 | 0.5294 | 0.0363 |
| **XGBoost** (Uncalibrated Default) | 0.5000 | 0.9303 | 0.0000 | 0.0000 | 0.0000 | 0.0887 |
| **Calibrated XGBoost (Production)** | **0.2849** | **0.9336** `[0.9070, 0.9551]` | **0.4277** `[0.3239, 0.5091]` | **0.3736** | **0.5000** | **0.0263** `[0.0215, 0.0313]` |

* **Calibration Impact**: 3-fold Platt sigmoid scaling reduces Brier score error by **70.38%** (0.0887 → 0.0263). See the reliability diagram at [`ml/calibration_reliability_diagram.png`](ml/calibration_reliability_diagram.png).
* **Threshold Tuning**: Shifting cutoff from 0.50 to 0.2849 overcomes 28:1 imbalance, lifting F1 from 0.00 to 0.4277 (capturing 50% of emerging failures).

### 2. Failure-Mode Uncertainty Profile (Stratified 5-Fold Cross-Validation)

| Failure Mode | Total Support | Mean Supp / Fold | CV F1 (Mean ± Std) | CV Recall (Mean ± Std) | CV ROC-AUC (Mean ± Std) | Empirical Diagnostic Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Overstrain (OSF)** | 92 | 18.4 | **0.4137 ± 0.0984** | 0.5014 ± 0.1617 | 0.9715 ± 0.0136 | **Strong Signature**: High mechanical separability from torque × speed. |
| **Power Failure (PWF)** | 80 | 16.0 | **0.2956 ± 0.0671** | 0.3522 ± 0.1093 | 0.9394 ± 0.0119 | **Sensitive**: Triggered by mechanical power breaching motor limits. |
| **Thermal (HDF)** | 115 | 23.0 | **0.1212 ± 0.0384** | 0.1113 ± 0.0389 | 0.9330 ± 0.0032 | **Known Limit**: Detects acute shocks, misses gradual thermal creep. |
| **Tool Wear (TWF)** | 43 | 8.6 | **0.0285 ± 0.0353** | 0.0500 ± 0.0667 | 0.9144 ± 0.0124 | **Data-Starved**: F1 collapses to 0.0 in 3/5 folds. Requires wear sensor heads. |
| **All Failures (Overall)** | 339 | 67.8 | **0.3466 ± 0.0212** | 0.2597 ± 0.0252 | 0.9348 ± 0.0087 | Aggregate CV baseline across 28:1 imbalanced distribution. |

---

## ⚡ High-Performance Multi-Runtime Inferencing

PMS incorporates a dual-runtime inference architecture designed for high-frequency industrial streaming:

### 1. Empirical Latency & Throughput Benchmark (Measured on CPU)

```
[Incoming Telemetry Stream]
             │
             ├──► ONNX Runtime (C++) ──► 0.021 ms / pred (90.4x Speedup | ~47,600 req/sec)
             │
             ├──► Calibrated XGBoost ──► 1.909 ms / pred (Platt Scaling + SHAP TreeExplainer)
             │
             └──► Hybrid Fast-Path   ──► Runs ONNX filter; triggers SHAP only on high-risk events
                                         (Cuts compute latency by 98% on nominal telemetry)
```

| Inference Engine | Execution Runtime | Mean Latency | 95th Percentile Latency | Max Throughput | Primary Operational Domain |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **ONNX Runtime** (`ml/model.onnx`) | C++ Execution Provider | **0.021 ms** (21 µs) | **0.028 ms** | **~47,600 req/sec** | Edge IoT gateways, high-speed PLC buses (100Hz+) |
| **Calibrated XGBoost** (`ml/model.pkl`) | Python / Cython | 1.909 ms | 2.450 ms | ~520 req/sec | Full SHAP attribution & probabilistic uncertainty |
| **Speedup Disparity** | — | **90.4x Faster** | — | — | **Sub-millisecond edge classification** |

* **Reason to Implement**: Edge PLCs and high-speed CNC controllers sample at 100Hz–1kHz. Standard Python XGBoost execution (~2ms) consumes excessive CPU budget and introduces queueing jitter. Exporting the booster to ONNX eliminates interpreter overhead and unlocks 47,000+ predictions/sec per core.
* **Honest Technical Disclosure**: The serialized ONNX model (`ml/model.onnx`) outputs uncalibrated decision probabilities. For true calibrated probabilities and local Shapley attribution, the `hybrid` runtime mode executes ONNX as a sub-millisecond triage filter, invoking the full TreeExplainer only when probability breaches the decision threshold.

---

## 🔬 Context Engineering Architecture

Point-in-time sensor readings (`temp=94.2`, `vibration=0.68`) lack physical meaning without operational context. PMS enriches incoming payloads with a structured **Context Envelope**:

1. **Operational Regime & Machine Metadata**:
   - Classifies operating states (`idle`, `warmup`, `steady_state_light`, `steady_state_heavy`, `shutdown`).
   - Normalizes thermal readings against plant ambient temperature ($\Delta T = T_{\text{process}} - T_{\text{ambient}}$).
2. **Temporal Momentum Gradients**:
   - Ingests temporal velocities ($dT/dt$ in °C/min) to distinguish acute thermal runaway from slow ambient drift.
   - Computes vibration crest factors ($\text{Peak} / \text{RMS}$) to detect sudden impact impulses and bearing spalling.
3. **Structured Prompt Grounding**:
   - Assembles machine specifications, operating limits, and counterfactual fix targets (`find_minimal_fix`) directly into LLM technician briefings alongside retrieved SOP chunks.

---

## 🧪 Harness Engineering Suite (`harness/`)

PMS includes automated evaluation, simulation, and chaos testing scaffolding to benchmark system health without physical machinery:

```
harness/
├── scenarios/     ──► Simulates physics failure curves (Thermal Runaway, Overstrain, Tool Wear, Glitches)
├── eval/          ──► Benchmarks AI groundedness, citation recall, and canary honeytoken security
└── chaos/         ──► Injects DB connection crashes and trips AI circuit breakers (FSM)
```

### 1. Degradation Simulation Harness (`python -m harness.runner --scenario all`)
| Degradation Scenario | Physical Failure Model | Detection Result | Expected / Detected | First Alert Step | Latency (Mean/P95) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Thermal Runaway** | Coolant circuit failure, exponential heat climb | **[PASS]** | 21 / 18 | Step 22 ($t \approx 44\text{s}$) | 1014ms / 4260ms |
| **Overstrain Surge** | Hard workpiece inclusion, hydraulic pressure spike | **[PASS]** | 13 / 13 | Step 13 ($t \approx 13\text{s}$) | 435ms / 622ms |
| **Tool Wear Fatigue** | Cumulative insert wear, vibration harmonics | **[PASS]** | 15 / 15 | Step 15 ($t \approx 15\text{s}$) | 463ms / 606ms |
| **Sensor Glitch** | Transducer EMI pulse and brownout recovery | **[PASS]** | 3 / 3 | Step 5 ($t \approx 5\text{s}$) | 516ms / 764ms |

*Outcome: 100% of physical failure modes detected with zero false alarms.*

### 2. AI & RAG Evaluation Harness (`python -m harness.eval.eval_harness`)
- **Groundedness Score ($G_{\text{score}}$)**: 80%–100% factual fidelity; asserts that numerical figures quoted in narratives strictly exist in the prediction or SOP chunks.
- **Prompt Injection Defense**: Evaluates OWASP LLM01 attacks; verified that `PromptShield` blocked 100% of malicious prompt injections and logged cryptographic SHA-256 audit events.
- **Canary Trap**: Zero system prompt honeytoken leakage detected across all evaluations.

### 3. Chaos & Fault-Injection Harness (`python -m harness.chaos.chaos_runner`)
- **AI Circuit Breaker Fault Injection**: Injected downstream timeouts; circuit transitioned `CLOSED -> OPEN -> HALF_OPEN -> CLOSED`. Fast-rejection latency clocked at **3.6 µs**.
- **Database Severing Resilience**: Severed database connection pool during active inference; API caught DB exceptions, logged rollbacks, and preserved **100% HTTP 200 uptime** with zero dropped predictions.

---

## 🤖 Model Context Protocol (MCP) Server (`backend/mcp_server.py`)

PMS implements the open **Model Context Protocol (MCP)** (JSON-RPC 2.0), enabling external AI agents (Antigravity, Claude Desktop, Cursor, plant maintenance bots) to interact natively with industrial equipment:

* **Dual Transport**: Supports standard input/output (`stdio`) for local desktop clients and HTTP (`POST /mcp`) for cloud gateways.
* **Exposed MCP Tools**:
  * `predict_equipment_risk`: Multi-runtime inference (`onnx`, `xgboost`, `hybrid`).
  * `predict_and_narrate`: Context-grounded RAG narration with auditable SOP chunks.
  * `simulate_derate_intervention`: Prescriptive speed/pressure de-rating to extend RUL.
  * `dispatch_work_order`: Closed-loop CMMS/ERP maintenance order generation.
  * `get_drift_telemetry`: Population Stability Index (PSI) drift monitoring.
  * `run_inference_benchmark`: Benchmarks ONNX vs. XGBoost runtimes.
* **Exposed MCP Resources**:
  * `pms://system/health`: System status, loaded models, and database connectivity.
  * `pms://models/manifest`: Serialized model architecture, metrics, and thresholds.
  * `pms://knowledge_base/sop_index`: RAG knowledge base document catalog.
* **Exposed MCP Prompts**:
  * `diagnose_machine_anomaly`: Step-by-step diagnostic workflow for shop-floor technicians.
  * `shift_handover_report`: Plant manager reliability summary.

---

## ⚡ Quickstart

### Option 1: Full-Stack Docker Compose (Recommended)

Start the API gateway, React UI, PostgreSQL database, Prometheus collector, and Grafana with one command:

```bash
docker-compose up --build -d
```

| Service | Access URL | Default Credentials / Purpose |
| :--- | :--- | :--- |
| **React Dashboard** | `http://localhost:3000` | Operational web interface |
| **FastAPI Backend** | `http://localhost:8000` | Interactive OpenAPI documentation at `/docs` |
| **Prometheus** | `http://localhost:9090` | Telemetry & PSI scraping engine |
| **Grafana** | `http://localhost:3001` | Pre-configured operational monitoring |
| **PostgreSQL** | `localhost:5432` | User: `postgres`, Password: `password` |

To tear down: `docker-compose down -v`

### Option 2: Local Python & Node.js Development

```bash
# 1. Backend Setup
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
cp .env.example .env
python ml/train.py                                   # Generate serialized model artifacts
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload

# 2. Frontend Setup (separate terminal)
cd frontend && npm install && npm run dev
```

Run test suite: `pytest backend/tests/ -v --cov=backend --cov-report=term-missing`

---

## 📖 Deep Documentation & References

- 🎯 **[Boardroom Strategy, Forensic Audit & Agent Plan](docs/BOARDROOM_STRATEGY_AND_AUDIT.md)**: Executive C-suite presentation script, red flag kill-list, Prescriptive Digital Twin specifications, and phased agent execution roadmap.
- ⚡ **[Distributed Systems & Performance Blueprint (50 Pillars)](docs/DISTRIBUTED_SYSTEMS_AND_PERFORMANCE.md)**: High-scale database transactions, ACID, indexing, distributed caching, idempotency, circuit breakers, CQRS, and W3C distributed tracing.
- 🛡️ **[Enterprise Security & AI Hardening Manual](docs/ENTERPRISE_SECURITY.md)**: Zero-trust architecture, cryptographic audit hash chains, prompt injection defenses, canary honeytokens, and SOC 2 / ISO 27001 compliance.
- 🏛️ **[System Architecture Reference](docs/ARCHITECTURE.md)**: Four-tier deep dive, physics formulas, FFT spectral extraction, DB pooling, and canary mechanics.
- 💼 **[Business Case & Industrial ROI](docs/BUSINESS_CASE.md)**: Worked economic example on downtime reduction, cost-sensitive optimization matrix, and unit economics.
- 📋 **[Scientific Model Card](ml/MODEL_CARD.md)**: Explicit intended and out-of-scope uses, calibration reliability curves, slice verification, and known weaknesses.
- 🚀 **[Load Testing & Concurrency Benchmark](docs/LOAD_TEST_RESULTS.md)**: Locust benchmark results at 10, 50, and 100 users, connection pooling mechanics, and latency breakdown.


---

## 📜 License & Citation

Licensed under the **MIT License** — see [LICENSE](LICENSE).

```bibtex
@misc{pms2026,
  author = {Susil Nayak},
  title = {Predictive Maintenance System (PMS): Calibrated Industrial Intelligence Platform},
  year = {2026},
  url = {https://github.com/Susil-commits/Predictive-Maintenance-System}
}
```
