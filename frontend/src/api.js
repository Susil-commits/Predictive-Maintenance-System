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
const API_BASE_URL = rawBaseUrl.replace(/\/+$/, '');

const API_KEY = import.meta.env.VITE_API_KEY || 'pms-admin-secret-key';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY,
  },
  timeout: 60000,
});

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

export default api;

