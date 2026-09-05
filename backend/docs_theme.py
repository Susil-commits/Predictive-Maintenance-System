"""
backend/docs_theme.py
=====================
Custom branded dark-theme UI for FastAPI interactive API documentation (/docs and /redoc).
Styled with Google Fonts Outfit & JetBrains Mono, glassmorphic top navigation bar,
live status indicator, and interactive OpenAPI security scheme configuration.
"""

from typing import List, Dict, Any

API_DESCRIPTION = """
### 🚀 Industrial Equipment & Fleet Failure Intelligence Platform

The **Predictive Maintenance System (PMS) API** delivers real-time failure prediction, explainable AI diagnostics (SHAP), batch telemetry reconciliation, and continuous MLOps drift monitoring for vehicle fleets and industrial machinery.

---

### 🔑 Interactive Authentication & Access Control

Endpoints marked with 🔒 require administrative privileges. You can authenticate using either:
1. **JWT Bearer Token**: Obtain a signed token via `POST /auth/login` and supply the header:
   `Authorization: Bearer <your_jwt_token>`
2. **Admin API Key**: Supply your administrative API key via the header:
   `X-API-Key: <your_admin_api_key>` (Default test key: `pms-admin-secret-key`)

> **💡 Quick Start**: Click the green **Authorize** 🔒 button at the top right of this page to configure your credentials once for all test requests.

---

### 📊 Monitored Sensor Telemetry Features

| Sensor Feature | Typical Range | Unit | Diagnostic Significance |
| :--- | :--- | :--- | :--- |
| `temperature` | `20.0` - `150.0` | °C | Thermal friction, overheating, cooling failure |
| `rpm` | `500.0` - `4500.0` | RPM | Operational rotational velocity & torque demand |
| `pressure` | `10.0` - `60.0` | bar | Hydraulic & pneumatic system operating pressure |
| `vibration` | `0.05` - `1.50` | mm/s | Mechanical imbalance, loose bearings & misalignment |
| `operating_hours` | `0.0` - `15000.0` | hrs | Cumulative component lifecycle aging |

---

### 🧠 Explainable Machine Learning Stack
* **Ensemble Architecture**: Calibrated LightGBM Classifier with tuned precision-recall decision thresholds.
* **Explainability Engine**: Real-time TreeSHAP contribution decomposition ranking key drivers.
* **Drift Monitoring**: Automated Population Stability Index (PSI) tracking against training baselines.
* **Continuous MLOps**: Mutex-guarded retraining pipeline (`/retrain`) with dynamic model reloading.
"""

TAGS_METADATA: List[Dict[str, Any]] = [
    {
        "name": "Prediction",
        "description": "⚡ Real-time failure risk prediction, calibrated failure probability, and instant SHAP factor attribution."
    },
    {
        "name": "Batch Operations",
        "description": "📦 High-throughput CSV, Excel, and JSON batch processing with fuzzy column matching and data export."
    },
    {
        "name": "MLOps",
        "description": "🔄 Population Stability Index (PSI) telemetry drift monitoring, reference baseline reload, and retraining."
    },
    {
        "name": "Authentication",
        "description": "🛡️ User authentication, bcrypt verification, signed JWT issuance, and RBAC user provisioning."
    },
    {
        "name": "Audit & History",
        "description": "📋 Historical prediction records, PostgreSQL-backed query filters, and data pruning."
    },
    {
        "name": "Model",
        "description": "ℹ️ Model architecture metadata, MLflow run lineage, decision thresholds, and feature rankings."
    },
    {
        "name": "Health",
        "description": "💓 Un-throttled system uptime, database ping, and model verification for load balancers."
    },
    {
        "name": "Metrics",
        "description": "📈 Prometheus-compatible operational counters and live drift metrics."
    }
]

SWAGGER_DARK_CSS = """
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Outfit:wght@300;400;500;600;700;800&display=swap');

:root {
  --pms-bg: #09090b;
  --pms-card: #121215;
  --pms-card-hover: #18181d;
  --pms-border: rgba(255, 255, 255, 0.09);
  --pms-border-active: rgba(255, 255, 255, 0.22);
  --pms-cyan: #06b6d4;
  --pms-emerald: #10b981;
  --pms-rose: #f43f5e;
  --pms-amber: #f59e0b;
  --pms-text: #f4f4f5;
  --pms-text-muted: #a1a1aa;
  --pms-text-dim: #71717a;
}

html, body {
  background-color: var(--pms-bg) !important;
  color: var(--pms-text) !important;
  font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif !important;
  margin: 0;
  padding: 0;
  -webkit-font-smoothing: antialiased;
}

/* Custom Header Bar */
.pms-header {
  position: sticky;
  top: 0;
  z-index: 1000;
  background: rgba(9, 9, 11, 0.92);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--pms-border);
  padding: 12px 28px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.pms-brand {
  display: flex;
  align-items: center;
  gap: 14px;
}

.pms-logo-box {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(6, 182, 212, 0.2), rgba(16, 185, 129, 0.15));
  border: 1px solid rgba(6, 182, 212, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 15px rgba(6, 182, 212, 0.25);
}

.pms-brand-info {
  display: flex;
  flex-direction: column;
}

.pms-brand-title {
  font-size: 1.05rem;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: -0.02em;
}

.pms-brand-sub {
  font-size: 0.75rem;
  color: var(--pms-cyan);
  font-family: 'JetBrains Mono', monospace;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 6px;
}

.pms-status-pulse {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background-color: var(--pms-emerald);
  box-shadow: 0 0 8px var(--pms-emerald);
  display: inline-block;
  animation: pulse 2s infinite ease-in-out;
}

@keyframes pulse {
  0% { transform: scale(0.95); opacity: 0.8; }
  50% { transform: scale(1.2); opacity: 1; box-shadow: 0 0 12px var(--pms-emerald); }
  100% { transform: scale(0.95); opacity: 0.8; }
}

.pms-nav-links {
  display: flex;
  align-items: center;
  gap: 10px;
}

.pms-nav-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 13px;
  border-radius: 8px;
  font-size: 0.82rem;
  font-weight: 600;
  text-decoration: none;
  color: var(--pms-text-muted);
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--pms-border);
  transition: all 0.2s ease;
}

.pms-nav-btn:hover {
  color: #ffffff;
  background: rgba(255, 255, 255, 0.08);
  border-color: var(--pms-border-active);
  transform: translateY(-1px);
}

.pms-nav-btn.primary {
  color: #000000;
  background: var(--pms-cyan);
  border-color: var(--pms-cyan);
  box-shadow: 0 0 12px rgba(6, 182, 212, 0.35);
}

.pms-nav-btn.primary:hover {
  background: #22d3ee;
  color: #000000;
}

/* Swagger UI Dark Overrides */
.swagger-ui {
  color: var(--pms-text) !important;
  font-family: 'Outfit', sans-serif !important;
  max-width: 1300px;
  margin: 0 auto;
  padding: 24px 20px 80px;
}

.swagger-ui .topbar {
  display: none !important;
}

/* Info Section */
.swagger-ui .info {
  margin: 24px 0 32px !important;
  background: var(--pms-card);
  border: 1px solid var(--pms-border);
  border-radius: 16px;
  padding: 28px 32px !important;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.6);
}

.swagger-ui .info .title {
  color: #ffffff !important;
  font-family: 'Outfit', sans-serif !important;
  font-size: 2.1rem !important;
  font-weight: 800 !important;
  letter-spacing: -0.03em;
  margin-bottom: 8px !important;
}

.swagger-ui .info .version {
  background: rgba(6, 182, 212, 0.15) !important;
  color: var(--pms-cyan) !important;
  border: 1px solid rgba(6, 182, 212, 0.3) !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 0.8rem !important;
  padding: 4px 10px !important;
  border-radius: 20px !important;
}

.swagger-ui .info p, .swagger-ui .info li {
  color: var(--pms-text-muted) !important;
  font-size: 0.95rem !important;
  line-height: 1.65 !important;
}

.swagger-ui .info h3 {
  color: #ffffff !important;
  font-weight: 700 !important;
  margin-top: 20px !important;
  font-size: 1.25rem !important;
}

.swagger-ui .info table {
  width: 100%;
  margin: 16px 0;
  border-collapse: collapse;
  background: #09090b;
  border-radius: 8px;
  overflow: hidden;
}

.swagger-ui .info table th, .swagger-ui .info table td {
  padding: 10px 14px;
  border: 1px solid var(--pms-border);
  text-align: left;
}

.swagger-ui .info table th {
  background: rgba(255, 255, 255, 0.05);
  color: #ffffff;
  font-weight: 600;
  font-size: 0.85rem;
}

.swagger-ui .info table td code {
  color: var(--pms-cyan);
  background: rgba(6, 182, 212, 0.08);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'JetBrains Mono', monospace;
}

/* Authorize Button & Scheme Container */
.swagger-ui .scheme-container {
  background: var(--pms-card) !important;
  border: 1px solid var(--pms-border) !important;
  border-radius: 14px !important;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5) !important;
  padding: 16px 24px !important;
  margin-bottom: 28px !important;
}

.swagger-ui .btn.authorize {
  color: var(--pms-emerald) !important;
  border-color: var(--pms-emerald) !important;
  background: rgba(16, 185, 129, 0.1) !important;
  border-radius: 10px !important;
  font-family: 'Outfit', sans-serif !important;
  font-weight: 700 !important;
  font-size: 0.92rem !important;
  padding: 8px 18px !important;
  transition: all 0.2s ease !important;
}

.swagger-ui .btn.authorize:hover {
  background: var(--pms-emerald) !important;
  color: #000000 !important;
  box-shadow: 0 0 16px rgba(16, 185, 129, 0.4) !important;
}

.swagger-ui .btn.authorize svg {
  fill: currentColor !important;
}

/* Tags & Operations */
.swagger-ui .opblock-tag-section {
  margin-bottom: 24px;
}

.swagger-ui .opblock-tag {
  color: #ffffff !important;
  font-family: 'Outfit', sans-serif !important;
  font-size: 1.35rem !important;
  font-weight: 700 !important;
  border-bottom: 1px solid var(--pms-border) !important;
  padding: 14px 0 10px !important;
}

.swagger-ui .opblock-tag small {
  color: var(--pms-text-muted) !important;
  font-size: 0.88rem !important;
  font-weight: 400 !important;
}

/* Operation Blocks */
.swagger-ui .opblock {
  background: var(--pms-card) !important;
  border: 1px solid var(--pms-border) !important;
  border-radius: 12px !important;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.4) !important;
  margin: 0 0 12px !important;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
}

.swagger-ui .opblock:hover {
  border-color: var(--pms-border-active) !important;
  background: var(--pms-card-hover) !important;
  transform: translateY(-1px);
}

.swagger-ui .opblock .opblock-summary {
  padding: 10px 16px !important;
}

.swagger-ui .opblock .opblock-summary-method {
  border-radius: 8px !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-weight: 700 !important;
  font-size: 0.82rem !important;
  min-width: 82px !important;
  text-align: center !important;
  color: #000000 !important;
}

/* Method Specific Color Styling */
.swagger-ui .opblock-post {
  border-color: rgba(16, 185, 129, 0.25) !important;
  background: rgba(16, 185, 129, 0.02) !important;
}
.swagger-ui .opblock-post .opblock-summary-method {
  background: var(--pms-emerald) !important;
}

.swagger-ui .opblock-get {
  border-color: rgba(6, 182, 212, 0.25) !important;
  background: rgba(6, 182, 212, 0.02) !important;
}
.swagger-ui .opblock-get .opblock-summary-method {
  background: var(--pms-cyan) !important;
}

.swagger-ui .opblock-delete {
  border-color: rgba(244, 63, 94, 0.25) !important;
  background: rgba(244, 63, 94, 0.02) !important;
}
.swagger-ui .opblock-delete .opblock-summary-method {
  background: var(--pms-rose) !important;
  color: #ffffff !important;
}

.swagger-ui .opblock .opblock-summary-path {
  color: #ffffff !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 0.95rem !important;
  font-weight: 600 !important;
}

.swagger-ui .opblock .opblock-summary-description {
  color: var(--pms-text-muted) !important;
  font-size: 0.88rem !important;
}

/* Operation Body & Forms */
.swagger-ui .opblock-body {
  background: #09090b !important;
  border-top: 1px solid var(--pms-border) !important;
  padding: 20px 24px !important;
}

.swagger-ui .opblock-section-header {
  background: rgba(255, 255, 255, 0.03) !important;
  border-radius: 8px;
  padding: 8px 14px !important;
}

.swagger-ui .opblock-section-header h4 {
  color: #ffffff !important;
  font-size: 0.9rem !important;
  font-weight: 700 !important;
}

.swagger-ui table thead tr th {
  color: var(--pms-text-dim) !important;
  font-size: 0.75rem !important;
  text-transform: uppercase !important;
  letter-spacing: 0.05em !important;
  border-bottom: 1px solid var(--pms-border) !important;
}

.swagger-ui table tbody tr td {
  border-bottom: 1px solid rgba(255, 255, 255, 0.04) !important;
  color: var(--pms-text-muted) !important;
}

.swagger-ui .parameter__name {
  color: #ffffff !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 0.85rem !important;
  font-weight: 600 !important;
}

.swagger-ui .parameter__type {
  color: var(--pms-cyan) !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 0.78rem !important;
}

.swagger-ui input[type=text], .swagger-ui textarea, .swagger-ui select {
  background: #18181d !important;
  color: #ffffff !important;
  border: 1px solid var(--pms-border) !important;
  border-radius: 8px !important;
  padding: 8px 12px !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 0.85rem !important;
}

.swagger-ui input[type=text]:focus, .swagger-ui textarea:focus {
  border-color: var(--pms-cyan) !important;
  outline: none !important;
  box-shadow: 0 0 0 2px rgba(6, 182, 212, 0.25) !important;
}

.swagger-ui .btn {
  border-radius: 8px !important;
  font-family: 'Outfit', sans-serif !important;
  font-weight: 600 !important;
}

.swagger-ui .btn.execute {
  background-color: var(--pms-cyan) !important;
  color: #000000 !important;
  border: none !important;
  font-weight: 700 !important;
  box-shadow: 0 0 14px rgba(6, 182, 212, 0.35) !important;
}

.swagger-ui .btn.cancel {
  background: #27272a !important;
  color: #ffffff !important;
  border: none !important;
}

.swagger-ui .response-col_status {
  color: var(--pms-emerald) !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-weight: 700 !important;
}

.swagger-ui .response-col_description {
  color: var(--pms-text) !important;
}

.swagger-ui .highlight-code pre {
  background: #121215 !important;
  border: 1px solid var(--pms-border) !important;
  border-radius: 8px !important;
  font-family: 'JetBrains Mono', monospace !important;
}

/* Models Section */
.swagger-ui section.models {
  border: 1px solid var(--pms-border) !important;
  border-radius: 14px !important;
  background: var(--pms-card) !important;
  padding: 16px !important;
  margin-top: 32px !important;
}

.swagger-ui section.models h4 {
  color: #ffffff !important;
  font-family: 'Outfit', sans-serif !important;
  font-weight: 700 !important;
}

.swagger-ui .model-box {
  background: #09090b !important;
  border: 1px solid var(--pms-border) !important;
  border-radius: 8px !important;
}

/* Auth Modal UX */
.swagger-ui .dialog-ux .modal-ux {
  background: #121215 !important;
  border: 1px solid var(--pms-border-active) !important;
  border-radius: 16px !important;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.95) !important;
}

.swagger-ui .dialog-ux .modal-ux-header {
  border-bottom: 1px solid var(--pms-border) !important;
  padding: 18px 24px !important;
}

.swagger-ui .dialog-ux .modal-ux-header h3 {
  color: #ffffff !important;
  font-family: 'Outfit', sans-serif !important;
  font-weight: 700 !important;
}

.swagger-ui .dialog-ux .modal-ux-content {
  color: var(--pms-text-muted) !important;
  padding: 20px 24px !important;
}

.swagger-ui .dialog-ux .modal-ux-content h4 {
  color: #ffffff !important;
}

/* Custom Scrollbar */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}
::-webkit-scrollbar-track {
  background: #09090b;
}
::-webkit-scrollbar-thumb {
  background: #27272a;
  border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
  background: #3f3f46;
}
"""

def get_pms_swagger_html(
    openapi_url: str = "/openapi.json",
    title: str = "PMS API Explorer | Predictive Maintenance System"
) -> str:
    """Generates customized Swagger UI HTML with dark theme and brand header."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2306b6d4' stroke-width='2'><path d='M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83'/></svg>">
  <link rel="stylesheet" type="text/css" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
  <style>{SWAGGER_DARK_CSS}</style>
</head>
<body>
  <header class="pms-header">
    <div class="pms-brand">
      <div class="pms-logo-box">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#06b6d4" stroke-width="2.5">
          <path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83"/>
        </svg>
      </div>
      <div class="pms-brand-info">
        <span class="pms-brand-title">Predictive Maintenance System</span>
        <span class="pms-brand-sub">
          <span class="pms-status-pulse"></span>
          API Explorer &bull; v1.1.0 Live
        </span>
      </div>
    </div>
    <nav class="pms-nav-links">
      <a href="/health" class="pms-nav-btn" target="_blank">🩺 Health Status</a>
      <a href="/metrics" class="pms-nav-btn" target="_blank">📈 Metrics</a>
      <a href="/redoc" class="pms-nav-btn">📖 ReDoc Reference</a>
      <a href="{openapi_url}" class="pms-nav-btn primary" target="_blank">📄 OpenAPI Spec</a>
    </nav>
  </header>

  <div id="swagger-ui"></div>

  <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-standalone-preset.js"></script>
  <script>
    window.onload = function() {{
      const ui = SwaggerUIBundle({{
        url: "{openapi_url}",
        dom_id: '#swagger-ui',
        deepLinking: true,
        presets: [
          SwaggerUIBundle.presets.apis,
          SwaggerUIStandalonePreset
        ],
        plugins: [
          SwaggerUIBundle.plugins.DownloadUrl
        ],
        layout: "BaseLayout",
        defaultModelsExpandDepth: 1,
        defaultModelExpandDepth: 2,
        docExpansion: "list",
        filter: true,
        persistAuthorization: true,
        displayRequestDuration: true,
        tryItOutEnabled: true
      }});
      window.ui = ui;
    }};
  </script>
</body>
</html>
"""

def get_pms_redoc_html(
    openapi_url: str = "/openapi.json",
    title: str = "PMS API Reference | Predictive Maintenance System"
) -> str:
    """Generates customized ReDoc documentation HTML with dark theme matching brand."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2306b6d4' stroke-width='2'><path d='M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83'/></svg>">
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    body {{ margin: 0; padding: 0; background: #09090b; font-family: 'Outfit', sans-serif; }}
  </style>
</head>
<body>
  <redoc spec-url="{openapi_url}"
         theme='{{"colors":{{"primary":{{"main":"#06b6d4"}}}},"typography":{{"fontFamily":"Outfit, sans-serif","headings":{{"fontFamily":"Outfit, sans-serif"}},"code":{{"fontFamily":"JetBrains Mono, monospace"}}}}}}'>
  </redoc>
  <script src="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js"></script>
</body>
</html>
"""
