# Industrial Load Testing & Concurrency Benchmark

**Report Generated:** 2026-09-06 18:56:23 UTC  
**Testing Tool:** [Locust](https://locust.io/) (Headless Distributed Performance Harness)  
**Target Endpoint:** `POST /predict` (ML Inference + SHAP Explainer + FFT Extraction + PostgreSQL/SQLite Audit Logging)  
**Hardware / Runtime:** Dual-Worker Process (`--workers 2`, Python 3.13 / Uvicorn ASGI Server, PostgreSQL Pool: 20 + 30 overflow)

---

## Executive Summary

To evaluate production readiness under high-volume factory IoT telemetry streaming, the Predictive Maintenance System (`PMS`) API was subjected to stepped load testing at **10, 50, and 100 concurrent users**.

Each virtual user simulates a dedicated factory edge gateway continuously streaming sensor telemetry (temperature, rotational speed, pressure, vibration amplitude, operating hours) to the `/predict` endpoint.

> [!IMPORTANT]
> **Production Context & Rate Limiting Bypass Disclosure:**
> In standard production deployment, SlowAPI actively enforces a token-bucket rate limit of **60 requests/minute per client IP** (~1 req/s) on `/predict` to safeguard backend workers and database connection pools from exhaustion. For this benchmark harness, rate limiting was intentionally bypassed via `LOAD_TEST_MODE=1` (expanding the ceiling to 1,000,000 req/min) to stress-test the raw computational throughput of FFT feature extraction, calibrated XGBoost inference, SHAP TreeExplainer attribution, and PostgreSQL write commits.
> 
> **Takeaway on Production Throughput:** Real-world throughput for any single edge gateway or unauthenticated IP will be bounded by the **60 req/min (1 req/s)** policy unless whitelisted or assigned high-throughput API tiers. Aggregate production throughput will only scale toward the benchmarked numbers when distributed across multiple distinct client IP addresses.

---

## Optimization Impact: Side-by-Side Before vs. After Matrix

This matrix evaluates the empirical gains from migrating the PMS backend architecture:
- **Baseline Architecture:** Single Uvicorn worker process (`--workers 1`), SQLAlchemy database connection pool (`pool_size=5`, `max_overflow=10`).
- **Optimized Architecture:** Dual Uvicorn worker processes (`--workers 2`), expanded SQLAlchemy database connection pool (`pool_size=20`, `max_overflow=30`).

| Concurrency Level | Architecture / Configuration | Total Requests | Throughput (RPS) | Median Latency (p50) | 95th Percentile (p95) | 99th Percentile (p99) | Max Latency | Error Rate (%) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **10 users** | **Baseline (1 Worker, Pool=5/10)** | 223 | 17.0 req/s | 390.0 ms | 1400.0 ms | 2200.0 ms | 2983.57 ms | 0.0% |
| | **Optimized (2 Workers, Pool=20/30)** | 261 | **18.6 req/s** | **330.0 ms** | **1400.0 ms** | **2000.0 ms** | 2095.75 ms | 0.0% |
| | *Improvement / Delta (Δ)* | — | *+9.4% throughput* | *-15.4% latency* | *-0.0% latency* | *-9.1% latency* | — | *0% errors maintained* |
| **50 users** | **Baseline (1 Worker, Pool=5/10)** | 305 | 21.7 req/s | 1900.0 ms | 2400.0 ms | 2500.0 ms | 2636.45 ms | 0.0% |
| | **Optimized (2 Workers, Pool=20/30)** | 680 | **48.3 req/s** | **600.0 ms** | **3100.0 ms** | **3500.0 ms** | 3610.59 ms | 0.0% |
| | *Improvement / Delta (Δ)* | — | *+122.6% throughput* | *-68.4% latency* | *+29.2% latency* | *+40.0% latency* | — | *0% errors maintained* |
| **100 users** | **Baseline (1 Worker, Pool=5/10)** | 291 | 20.5 req/s | 3800.0 ms | 5100.0 ms | 6300.0 ms | 6518.97 ms | 0.0% |
| | **Optimized (2 Workers, Pool=20/30)** | 781 | **55.5 req/s** | **1300.0 ms** | **2900.0 ms** | **3500.0 ms** | 3712.96 ms | 0.0% |
| | *Improvement / Delta (Δ)* | — | *+170.7% throughput* | *-65.8% latency* | *-43.1% latency* | *-44.4% latency* | — | *0% errors maintained* |

---

## Latest Benchmark Results Matrix (2 Workers, Pool=20/30)

| Concurrent Users | Total Requests | Throughput (RPS) | Median Latency (p50) | 95th Percentile (p95) | 99th Percentile (p99) | Max Latency | Error Rate (%) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **10 users** | 261 | 18.6 req/s | 330.0 ms | 1400.0 ms | 2000.0 ms | 2095.75 ms | 0.0% |
| **50 users** | 680 | 48.3 req/s | 600.0 ms | 3100.0 ms | 3500.0 ms | 3610.59 ms | 0.0% |
| **100 users** | 781 | 55.5 req/s | 1300.0 ms | 2900.0 ms | 3500.0 ms | 3712.96 ms | 0.0% |

---

## Architectural Scaling & Contention Mechanics

### 1. Head-of-Line WAN I/O Blocking Alleviation
In the baseline single-worker architecture, every inference request completed in ~315 ms uncontended (with ~288 ms spent in remote WAN SSL round-trips to Supabase `aws-0-ap-south-1.pooler.supabase.com`). Under 50-100 concurrent clients, requests queued serially behind single-worker event loop thread synchronization, inflating p99 tail latency to **6,300 ms**.

By launching **`--workers 2`**, Uvicorn spawns two isolated worker processes with independent ASGI event loops. When Worker 1 awaits network I/O from a PostgreSQL commit, Worker 2 executes CPU-bound FFT feature extraction, XGBoost inference, and SHAP TreeExplainer attribution.

### 2. Database Connection Pool Contention Elimination
In the baseline, `pool_size=5, max_overflow=10` enforced a hard maximum of 15 simultaneous database connections. When 50 to 100 concurrent requests arrived, 35 to 85 requests stalled in SQLAlchemy's application-level queue awaiting available connection slots.

Expanding the pool to **`pool_size=20, max_overflow=30`** (up to 50 active pooled connections) completely eliminates application-level connection pool starvation during concurrency bursts.

### 3. Multi-Worker Schedulers & Concurrency Guards
Running `--workers 2` introduces two independent worker processes running `APScheduler` and `CanaryManager`. To prevent duplicate simultaneous retraining jobs if drift is detected concurrently in both workers, `backend/scheduler.py` implements an atomic filesystem lock (`.retrain.lock`) inside `_execute_retraining_pipeline`. If one worker begins retraining candidate models via `ml/train.py`, the secondary worker detects the active lock and safely skips execution.

### 4. Supabase Cloud Connection Ceiling Safety & Empirical Observation
While increasing application pool size eliminates connection queueing inside FastAPI, hosted cloud database poolers enforce their own strict upstream connection ceilings.

During our high-concurrency 50-100 user benchmark run with `pool_size=20, max_overflow=30` (up to 50 potential connections across 2 workers), Supabase's session-mode pooler actively surfaced:
```
(psycopg2.OperationalError) connection to server at "aws-0-ap-south-1.pooler.supabase.com", port 5432 failed: 
FATAL: (EMAXCONNSESSION) max clients reached in session mode - max clients are limited to pool_size: 15
```
Because the PMS backend isolates audit logging inside non-fatal try-except blocks, the client-facing `/predict` endpoint maintained a **0.0% Locust error rate** and delivered predictions without interruption. However, this empirically proves the classic production trade-off: **setting application connection pools higher than the cloud database gateway's allowance converts internal application queueing into external connection refusals**.

To ensure flexibility across cloud deployment tiers:
- `backend/database.py` exposes `DB_POOL_SIZE` (default: 20) and `DB_MAX_OVERFLOW` (default: 30) as environment variables.
- For Supabase Session Mode (port 5432, pool ceiling: 15), configure `DB_POOL_SIZE=6, DB_MAX_OVERFLOW=4` per worker (or run Supabase in **Transaction Mode on port 6543**, which supports thousands of multiplexed connections).

---

## Component-Level Latency & Queueing Breakdown

Profiling a single uncontended request through the full PMS pipeline reveals the division between CPU-bound computation and WAN I/O:

| Processing Stage | Subsystem | Measured Duration | % of Uncontended Total | Architectural Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Pydantic Validation & Routing** | FastAPI / ASGI | ~0.002 ms | <0.1% | Rust-backed Pydantic V2 core validation |
| **FFT Frequency Feature Extraction** | Signal Processing | ~6.9 ms | 2.2% | Vectorized `scipy.fft` + pandas DataFrame generation |
| **Calibrated XGBoost Inference** | ML Model | ~13.2 ms | 4.2% | Tree traversal across calibrated cross-validation folds |
| **SHAP TreeExplainer Attribution** | Model Explainability | ~4.2 ms | 1.3% | Fast tree-path marginal contribution calculations |
| **Database Network RTT + Commit** | Hosted Cloud PostgreSQL | ~287.9 ms | 91.2% | Public WAN TLS handshake + round-trip to Supabase AWS `ap-south-1` pooler + SQL `INSERT` + commit |
| **Uncontended Serial Total** | **End-to-End Single Request** | **~315.6 ms** | **100.0%** | **Real-world uncontended baseline** |

---

## Production Deployment Recommendations

1. **Worker Sizing on Render / Free Tier:**
   Render's free tier provides 1 shared vCPU. `--workers 2` is the sweet spot for maximizing I/O concurrency without incurring severe CPU context-switching overhead. Do not increase beyond 2 workers without upgrading to dedicated CPU plans.
2. **Asynchronous Audit Logging / Celery Offloading:**
   If sustained traffic exceeds 100+ concurrent requests, decouple the synchronous PostgreSQL commit from the `/predict` response path by buffering audit records into an async background task or queue (e.g. Redis + Celery or PostgreSQL batch copy).
3. **Connection Pool Monitoring:**
   Monitor Supabase Dashboard -> Database -> Connection Pooler metrics during peak usage to ensure total client connections stay well below pooler capacity.
