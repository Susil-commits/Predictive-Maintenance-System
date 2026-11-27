# Predictive Maintenance System (PMS) — Operations, API & Runbook Reference

This document provides an exact operational and interface reference for the FastAPI gateway, real-time streaming, Redis multi-worker coordination, Prometheus/Alertmanager alerting loop, Grafana provisioning, and CI/CD verification gates.

---

## 1. Core API & Streaming Endpoints

### Health, Model Inspection & Metrics
| Method & Path | Auth | Purpose |
| :--- | :---: | :--- |
| `GET /health`, `/health/live`, `/health/ready` | Public | Liveness and database/model readiness checks |
| `GET /metrics` | Public | Prometheus OpenMetrics exposition (`backend/metrics.py`) |
| `GET /model-info` | Public | Model version, threshold (`0.2849`), Brier/ROC-AUC metrics, feature list |
| `GET /inference/benchmark?iterations=100` | Public | Live CPU latency benchmark comparing ONNX vs. Calibrated XGBoost |

### Inference, Vectorized Batch & Prescriptive Analytics
| Method & Path | Auth | Purpose |
| :--- | :---: | :--- |
| `POST /predict?runtime=xgboost\|onnx\|hybrid` | Rate-limited (`60/min`) | Single-frame scoring with Context Envelope enrichment, Platt calibration, and on-demand SHAP |
| `POST /batch-predict?runtime=xgboost\|onnx` | Authenticated / Rate-limited | CSV/JSON/XLSX/Parquet batch inference (max 5 MB, 5,000 rows); `onnx` uses vectorized NumPy/FFT + batch ONNX scoring |
| `POST /predict/narrate` | Rate-limited | Context-grounded RAG technician SOP briefing with `PromptShield`, `PIISanitizer`, and `CanaryTrap` |
| `POST /predict-counterfactual` | Rate-limited | Evaluates minimal feature adjustments (`find_minimal_fix`) required to cross below risk threshold |
| `POST /predict-rul` | Rate-limited | Point-in-time Remaining Useful Life cycle/hour quantile estimation |
| `POST /predict/simulate-derate` | Rate-limited | Mechanical de-rating digital twin recalculating failure risk $\Delta P$ and Downtime Value-at-Risk ($VaR) |

### Multi-Asset Fleet, WebSocket Streaming & Plant Replay
| Method & Path | Auth | Purpose |
| :--- | :---: | :--- |
| `GET /fleet/summary?limit=200` | Authenticated | Per-asset latest health snapshot, prediction counts, and critical-asset count |
| `GET /fleet/{asset_id}/rul?window=30` | Authenticated | Rolling history-aware RUL degradation slope and forecast for a tracked asset |
| `POST /fleet/simulate-stream` | Admin / API Key | Replays synthetic degradation trajectories (`thermal`, `overstrain`, `wear`, `mixed`) into inference + `/ws/telemetry` |
| `WS /ws/telemetry` | Public stream | Real-time WebSocket stream delivering `prediction` and `ops_alert` frames across workers |

### Closed-Loop CMMS & Active Learning
| Method & Path | Auth | Purpose |
| :--- | :---: | :--- |
| `POST /maintenance/dispatch-work-order` | Open / Idempotent (`X-Idempotency-Key`) | Compiles, persists (`work_orders`), audits, and dispatches BOM + LOTO work order; deduplicates retries |
| `GET /maintenance/work-orders` | Authenticated | Filterable (`asset_id`, `status`, `limit`) maintenance dispatch ledger |
| `PATCH /maintenance/work-orders/{work_order_id}` | Authenticated | Transitions status (`DISPATCHED_TO_CMMS` $\rightarrow$ `IN_PROGRESS` $\rightarrow$ `RESOLVED`) with ground-truth feedback (`actual_failure_confirmed`) |
| `GET /mlops/feedback-metrics` | Authenticated | Real-world precision, false-alarm rate, and confusion matrix derived from resolved work orders |
| `POST /mlops/export-feedback` | Admin (`X-API-Key` / JWT) | Exports technician-labeled telemetry samples (`ml/data/feedback_dataset.csv`) for leakage-free retraining |

### Authentication, Persistence & Audit Compliance
| Method & Path | Auth | Purpose |
| :--- | :---: | :--- |
| `POST /auth/login` | Public | Authenticates `username`/`password` via `bcrypt`, issuing HS256 JWT (7-day TTL) |
| `GET/POST/DELETE /auth/users` | Admin | PostgreSQL/SQLite RBAC user lifecycle |
| `GET/POST /auth/access-logs` | User / Admin | Persistent user navigation telemetry (`user_access_logs` table) |
| `GET/POST/DELETE /reports` | User / Admin | Persistent diagnostic PDF/JSON metadata (`diagnostic_reports` table) scoped by owner |
| `GET /api/security/audit-trail` | Admin | Recent events in SHA-256 tamper-evident hash chain (`audit_events` table) |
| `GET /api/security/verify-chain` | Admin | Recomputes and verifies contiguous cryptographic linkage across all audit records |

### MLOps Governance & Alertmanager Bridge
| Method & Path | Auth | Purpose |
| :--- | :---: | :--- |
| `GET /drift-status` & `POST /drift-status/reset` | Public / Admin | Population Stability Index (PSI) across baseline quantiles (Redis-cached when available) |
| `POST /retrain` | Admin | Spawns background `ml/retrain_candidate.py` protected by local + Redis distributed leader lock |
| `GET /canary/status`, `POST /canary/start\|promote\|abort` | Admin | Phased canary rollout state (`ml/canary_state.json` + Redis cross-worker sync) |
| `POST /ops/alerts/webhook` | Webhook Auth (`X-API-Key`, Admin JWT, or `Bearer ALERTMANAGER_WEBHOOK_SECRET`) | Ingests Prometheus Alertmanager v4 webhooks, logs `PROMETHEUS_ALERT` in SHA-256 chain, broadcasts over WS, and auto-dispatches deduplicated CMMS work orders for critical asset-scoped alerts |
| `GET /ops/alerts` | Authenticated | Filterable (`severity`, `status`, `limit`) feed of persisted Alertmanager incidents |

---

## 2. Prometheus Metrics, Alert Rules & Turnkey Grafana

### Exported Metrics (`backend/metrics.py`)
- `pms_predictions_total`: Counter of total prediction evaluations
- `pms_predictions_high_risk`: Counter of `HIGH` risk predictions
- `pms_predict_latency_seconds`: Histogram (`_bucket`, `_count`, `_sum`) measuring `/predict` runtime latency
- `pms_drift_detected`: Gauge (`1` if PSI $\ge 0.25$, else `0`)
- `pms_drift_max_psi`: Gauge tracking peak monitored feature PSI
- `pms_feature_psi{feature="..."}`: Per-feature PSI gauges

### Alertmanager Routing Pipeline
```
Prometheus (/metrics every 15s)
   └─► prometheus/alert_rules.yml (5 rules evaluated every 15s)
          ├─ PMSBackendDown            (up{job="pms-backend"} == 0 for 1m, critical)
          ├─ PMSDataDriftCritical      (pms_drift_max_psi >= 0.25 for 1m, critical)
          ├─ PMSDataDriftWarning       (0.10 <= pms_drift_max_psi < 0.25 for 2m, warning)
          ├─ PMSHighRiskPredictionSpike(increase(pms_predictions_high_risk[5m]) > 10 for 1m, warning)
          └─ PMSInferenceLatencyHigh   (p95 latency > 0.5s for 2m, warning)
          ▼
Alertmanager (:9093 via prometheus/alertmanager.yml)
   └─► POST http://backend:8000/ops/alerts/webhook (firing & resolved)
          ├─► AuditLogger (PROMETHEUS_ALERT persisted to audit_events SHA-256 chain)
          ├─► TelemetryBroadcaster (ops_alert event pushed to WS /ws/telemetry)
          └─► Deduplicated CMMS WorkOrderRecord (if firing + critical + labels.asset_id)
```

### Turnkey Grafana Provisioning
Starting `docker-compose up -d` mounts:
- Datasource config: [`monitoring/provisioning/datasources/prometheus.yml`](../monitoring/provisioning/datasources/prometheus.yml) (`Prometheus` default proxy at `http://prometheus:9090`)
- Dashboard provider: [`monitoring/provisioning/dashboards/pms.yml`](../monitoring/provisioning/dashboards/pms.yml) loading [`monitoring/grafana_dashboard.json`](../monitoring/grafana_dashboard.json) into `/var/lib/grafana/dashboards/pms_dashboard.json` under folder **PMS Operational Intelligence**.

---

## 3. Multi-Worker Redis Scaling (`REDIS_URL`)

When `REDIS_URL` is configured (e.g., `redis://redis:6379/0`), multi-worker processes coordinate safely across:
1. **Rate Limiting**: `backend/limiter.py` passes `REDIS_URL` to SlowAPI so request quotas span all API workers.
2. **Idempotency Fast Cache**: `backend/security/idempotency.py` checks in-memory cache $\rightarrow$ Redis (`pms:idem:<key>`) $\rightarrow$ SQL database.
3. **Distributed Leader Lock**: `acquire_distributed_lock` uses Redis `SET ... NX EX` with fallback `threading.Lock` when offline.
4. **Drift Cache Coherency**: `/drift-status` caches payloads in Redis (`pms:drift:*`) and clears prefixes on `/drift-status/reset`.
5. **Canary State & WebSocket Fan-Out**: `CanaryManager` syncs rollout traffic state via Redis, and `TelemetryBroadcaster` fans out events on channel `pms:telemetry:stream`.

---

## 4. Database Migrations & CI Parity Gates

### Alembic Migrations (`alembic/versions/`)
1. `7402cafe3126`: Initial `predictions` and `pms_users` tables.
2. `a8c4e91f2b10`: Added `asset_id`, `regime`, and `runtime` columns + composite index to `predictions`.
3. `b9e2d4f1c307`: Added `work_orders`, `audit_events`, and `idempotency_keys` tables.
4. `c3f8a1b9d402`: Added `diagnostic_reports` and `user_access_logs` tables.

Run manually:
```bash
PYTHONPATH=. alembic upgrade head
```

### CI Pipeline Verification (`.github/workflows/ci.yml`)
Every push/PR to `main` runs 5 independent checks:
1. **Backend Quality & Test Suite**: `ruff`, `black --check`, `pyright`, `alembic upgrade head` (SQLite), `pytest`, plus degradation/eval/chaos harnesses.
2. **PostgreSQL 16 & Redis 7 Integration Parity**: Spins up real `postgres:16-alpine` and `redis:7-alpine` containers, runs `alembic upgrade head`, verifies live Redis ping + distributed lock, validates Prometheus/Alertmanager/Grafana YAML & JSON configs, and runs persistence/streaming/webhook tests against live Postgres + Redis.
3. **Security Vulnerability Audit**: `pip-audit --desc --local`.
4. **Docker Image Builds**: `Dockerfile.backend` and `Dockerfile.frontend`.
5. **Frontend Lint, Test & Build**: `npm run lint` (`oxlint --deny-warnings`), `npm test` (`node --test` + `vitest run`), and `vite build`.
