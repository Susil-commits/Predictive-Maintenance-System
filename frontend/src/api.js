import axios from 'axios';

let rawBaseUrl = import.meta.env?.VITE_API_BASE_URL || 'http://localhost:8000';

// Ensure remote URLs always use HTTPS and strip trailing slashes
if (rawBaseUrl && !rawBaseUrl.includes('localhost') && !rawBaseUrl.includes('127.0.0.1')) {
  if (rawBaseUrl.startsWith('http://')) {
    rawBaseUrl = rawBaseUrl.replace('http://', 'https://');
  } else if (!rawBaseUrl.startsWith('https://')) {
    rawBaseUrl = `https://${rawBaseUrl}`;
  }
}
export const API_BASE_URL = rawBaseUrl.replace(/\/+$/, '');

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 60000,
});

// Automatically inject JWT Bearer token into all requests when logged in
api.interceptors.request.use((config) => {
  try {
    const token = localStorage.getItem('pms_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  } catch {
    // Ignore localStorage access restrictions in restricted environments
  }
  return config;
});

// Response interceptor to catch 401 unauthorized / expired tokens
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      const isLoginEndpoint = error.config?.url?.includes('/auth/login');
      if (!isLoginEndpoint) {
        try {
          localStorage.removeItem('pms_token');
          localStorage.removeItem('pms_session');
        } catch {
          // Ignore storage errors
        }
        if (window.location.hash !== '#login') {
          window.location.hash = '#login';
          window.dispatchEvent(new Event('hashchange'));
        }
      }
    }
    return Promise.reject(error);
  }
);

export const loginApi = async (username, password) => {
  const response = await api.post('/auth/login', { username, password });
  return response.data;
};

export const getUsersApi = async () => {
  const response = await api.get('/auth/users');
  return response.data;
};

export const createUserApi = async (userData) => {
  const response = await api.post('/auth/users', userData);
  return response.data;
};

export const deleteUserApi = async (userId) => {
  const response = await api.delete(`/auth/users/${userId}`);
  return response.data;
};

export const getAccessLogsApi = async (limit = 100) => {
  const response = await api.get(`/auth/access-logs?limit=${limit}`);
  return response.data;
};

export const logAccessEventApi = async (page = 'dashboard', name = null) => {
  const response = await api.post('/auth/access-logs', { page, name });
  return response.data;
};

export const clearAccessLogsApi = async () => {
  const response = await api.delete('/auth/access-logs');
  return response.data;
};

export const getReportsApi = async (userId = null, limit = 100) => {
  const params = new URLSearchParams({ limit: String(limit) });
  if (userId) params.set('user_id', userId);
  const response = await api.get(`/reports?${params.toString()}`);
  return response.data;
};

export const saveReportApi = async (reportData) => {
  const response = await api.post('/reports', reportData);
  return response.data;
};

export const deleteReportApi = async (reportId) => {
  const response = await api.delete(`/reports/${encodeURIComponent(reportId)}`);
  return response.data;
};

export const clearAllReportsApi = async () => {
  const response = await api.delete('/reports');
  return response.data;
};

export const getHealth = async () => {
  const response = await api.get('/health');
  return response.data;
};

export const getModelInfo = async () => {
  const response = await api.get('/model-info');
  return response.data;
};

export const predictMaintenance = async (payload, runtime = 'xgboost') => {
  const response = await api.post(`/predict?runtime=${encodeURIComponent(runtime)}`, payload);
  return response.data;
};

export const getInferenceBenchmark = async (iterations = 100) => {
  const response = await api.get(`/inference/benchmark?iterations=${iterations}`);
  return response.data;
};

export const predictNarrate = async (payload, includeCounterfactual = false) => {
  const response = await api.post(`/predict/narrate?include_counterfactual=${includeCounterfactual}`, payload);
  return response.data;
};

export const predictCounterfactual = async (payload) => {
  const response = await api.post('/predict-counterfactual', payload);
  return response.data;
};

export const predictRul = async (equipmentHistory) => {
  const response = await api.post('/predict-rul', equipmentHistory);
  return response.data;
};

export const simulateDerate = async (payload) => {
  const response = await api.post('/predict/simulate-derate', payload);
  return response.data;
};

export const dispatchWorkOrder = async (payload) => {
  const response = await api.post('/maintenance/dispatch-work-order', payload);
  return response.data;
};

export const getWorkOrders = async (assetId = null, status = null, limit = 50) => {
  const params = new URLSearchParams({ limit: String(limit) });
  if (assetId) params.set('asset_id', assetId);
  if (status) params.set('status', status);
  const response = await api.get(`/maintenance/work-orders?${params.toString()}`);
  return response.data;
};

export const updateWorkOrderStatus = async (workOrderId, payload) => {
  const response = await api.patch(`/maintenance/work-orders/${encodeURIComponent(workOrderId)}`, payload);
  return response.data;
};

export const getFinancialRiskSummary = async (limit = 50) => {
  const response = await api.get(`/financial/risk-summary?limit=${limit}`);
  return response.data;
};


export const getHistory = async (limit = 20, assetId = null) => {
  const params = new URLSearchParams({ limit: String(limit) });
  if (assetId) params.set('asset_id', assetId);
  const response = await api.get(`/history?${params.toString()}`);
  return response.data;
};

export const getFleetSummary = async (limit = 500) => {
  const response = await api.get(`/fleet/summary?limit=${limit}`);
  return response.data;
};

export const getAssetRul = async (assetId, windowSize = 30) => {
  const response = await api.get(`/fleet/${encodeURIComponent(assetId)}/rul?window=${windowSize}`);
  return response.data;
};

export const connectTelemetryStream = ({ onEvent, onStatus } = {}) => {
  let ws = null;
  let closedByUser = false;
  let reconnectTimer = null;
  let attempt = 0;

  const wsUrl = `${API_BASE_URL.replace(/^http/i, 'ws')}/ws/telemetry`;

  const connect = () => {
    if (closedByUser) return;
    try {
      ws = new WebSocket(wsUrl);
      ws.onopen = () => {
        attempt = 0;
        if (onStatus) onStatus('connected');
      };
      ws.onmessage = (msg) => {
        try {
          const data = JSON.parse(msg.data);
          if (onEvent) onEvent(data);
        } catch {
          // Ignore malformed frame
        }
      };
      ws.onerror = () => {
        if (onStatus) onStatus('error');
      };
      ws.onclose = () => {
        if (onStatus) onStatus('disconnected');
        if (!closedByUser) {
          attempt += 1;
          const delay = Math.min(30000, 2000 * Math.pow(1.5, attempt - 1));
          reconnectTimer = setTimeout(connect, delay);
        }
      };
    } catch {
      if (onStatus) onStatus('disconnected');
    }
  };

  connect();

  return () => {
    closedByUser = true;
    if (reconnectTimer) clearTimeout(reconnectTimer);
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
      ws.close();
    }
  };
};

export const clearHistory = async () => {
  const response = await api.delete('/history');
  return response.data;
};

export const getDriftStatus = async () => {
  const response = await api.get('/drift-status');
  return response.data;
};

export const resetDriftStatus = async () => {
  const response = await api.post('/drift-status/reset');
  return response.data;
};

export const triggerRetrain = async () => {
  const response = await api.post('/retrain');
  return response.data;
};

export const getFeedbackMetrics = async () => {
  const response = await api.get('/mlops/feedback-metrics');
  return response.data;
};

export const exportFeedbackDataset = async () => {
  const response = await api.post('/mlops/export-feedback');
  return response.data;
};

export const getCanaryStatus = async () => {
  const response = await api.get('/canary/status');
  return response.data;
};

export const startCanaryRollout = async () => {
  const response = await api.post('/canary/start');
  return response.data;
};

export const promoteCanaryModel = async () => {
  const response = await api.post('/canary/promote');
  return response.data;
};

export const abortCanaryRollout = async () => {
  const response = await api.post('/canary/abort');
  return response.data;
};

export const getSchedulerJobs = async () => {
  const response = await api.get('/scheduler/jobs');
  return response.data;
};

export const runScheduledDriftCheck = async () => {
  const response = await api.post('/scheduler/run-drift-check');
  return response.data;
};

export const getSecurityTelemetry = async () => {
  const response = await api.get('/api/security/telemetry');
  return response.data;
};

export const getSecurityAuditTrail = async () => {
  const response = await api.get('/api/security/audit-trail');
  return response.data;
};

export const verifyAuditChain = async () => {
  const response = await api.get('/api/security/verify-chain');
  return response.data;
};

export const getCircuitStatus = async () => {
  const response = await api.get('/api/security/circuit-status');
  return response.data;
};

export const batchPredict = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/batch-predict', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  });
  return response.data;
};

export const exportHistory = async () => {
  const response = await api.get('/export', { responseType: 'blob' });
  const blob = new Blob([response.data], { type: 'text/csv' });
  const downloadUrl = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = downloadUrl;
  a.download = 'pms_history.csv';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(downloadUrl);
};

export default api;

