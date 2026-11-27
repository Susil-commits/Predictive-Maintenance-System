# Predictive Maintenance System (PMS) — Operations UI

React 19 + Vite 6 single-page application providing real-time equipment telemetry diagnostics, multi-asset fleet supervision, vectorized batch inference, digital twin de-rating simulation, and RBAC administration.

---

## Stack & Tooling

- **Framework**: React `19.2.x` + Vite `6.2.x` (`vite.config.js`)
- **HTTP Client**: Axios (`src/api.js`) with automatic JWT bearer attachment, 401 expiry redirect, and WebSocket auto-reconnect (`connectTelemetryStream`)
- **Icons**: `lucide-react`
- **Lint Gate**: `oxlint --deny-warnings` (zero-warning enforcement across all `src/` files)
- **Tests**:
  - `node --test src/__tests__/api.test.js` — Axios request/query serialization & contract tests
  - `vitest run` (`@testing-library/react` + `@testing-library/jest-dom` + `jsdom`) — React component behavior & interaction tests (`src/__tests__/components.test.jsx`)

---

## Key Modules (`src/`)

| Path | Responsibility |
| :--- | :--- |
| `src/pages/LandingPage.jsx` | Public overview + cold-start backend health probe (`checkServer`) |
| `src/pages/LoginPage.jsx` | JWT authentication (`POST /auth/login`) with role routing (`admin` vs. `employee`) |
| `src/pages/DashboardPage.jsx` | Main operator cockpit combining telemetry scoring, fleet matrix, WS stream, RUL, drift, reports & history |
| `src/pages/AdminPage.jsx` | RBAC user management, PostgreSQL report audit viewer, access logs & ops controls |
| `src/components/TelemetryForm.jsx` | Single-frame sensor inputs, Context Envelope parameters, and runtime selector (`xgboost` / `onnx` / `hybrid`) |
| `src/components/PredictionResult.jsx` | Calibrated risk verdict, SHAP driver breakdown, RAG SOP procedure card, counterfactual fix & CMMS work-order dispatch |
| `src/components/BatchPredict.jsx` | Drag-and-drop CSV/JSON/XLSX/Parquet upload targeting `/batch-predict?runtime=onnx\|xgboost` |
| `src/components/FleetOverviewPanel.jsx` | Multi-asset fleet health matrix and live plant degradation replay trigger (`POST /fleet/simulate-stream`) |
| `src/components/DigitalTwinSimulator.jsx` | Interactive de-rating simulation (`-RPM`, `+Pressure`, `-Temp`) computing risk drop & $VaR avoided |
| `src/components/RULForecastCard.jsx` | History-aware Remaining Useful Life cycle & hour forecast |
| `src/components/DriftMonitor.jsx` | Population Stability Index (PSI) per-feature drift monitor |
| `src/components/ReportDetailModal.jsx` | Stored diagnostic report modal viewer with Cloudinary snapshot support |

---

## Environment Configuration

Frontend builds read optional `VITE_*` variables from the workspace root `.env` (`envDir: '../'` in `vite.config.js`):

```env
VITE_API_URL=http://localhost:8000
VITE_CLOUDINARY_CLOUD_NAME=your-cloud-name
VITE_CLOUDINARY_UPLOAD_PRESET=pms_uploads
```

> Never place backend secrets (such as `JWT_SECRET`, `PMS_API_KEY`, or `CLOUDINARY_API_SECRET`) in `VITE_*` variables.

---

## Development, Quality & Build Commands

```bash
cd frontend
npm install

npm run dev     # Start local Vite dev server (default: http://localhost:5173)
npm run lint    # Enforce zero-warning oxlint gate (oxlint --deny-warnings)
npm test        # Run API unit tests (node --test) and React component tests (vitest)
npm run build   # Build production bundle into frontend/dist/
```
