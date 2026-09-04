import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const API_KEY = import.meta.env.VITE_API_KEY || 'pms-admin-secret-key';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY,
  },
  timeout: 10000,
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

