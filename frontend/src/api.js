import axios from 'axios';

let rawBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

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

export const getHealth = async () => {
  const response = await api.get('/health');
  return response.data;
};

export const getModelInfo = async () => {
  const response = await api.get('/model-info');
  return response.data;
};

export const predictMaintenance = async (payload) => {
  const response = await api.post('/predict', payload);
  return response.data;
};

export const getHistory = async (limit = 20) => {
  const response = await api.get(`/history?limit=${limit}`);
  return response.data;
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

