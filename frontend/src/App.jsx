import React, { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import PresetBar from './components/PresetBar';
import TelemetryForm from './components/TelemetryForm';
import PredictionResult from './components/PredictionResult';
import HistoryTable from './components/HistoryTable';
import DriftMonitor from './components/DriftMonitor';
import BatchPredict from './components/BatchPredict';
import { getHealth, getModelInfo, predictMaintenance, getHistory, clearHistory, getDriftStatus, exportHistory } from './api';
import { Sliders, Layers, LayoutGrid, Upload, Download } from 'lucide-react';

const DEFAULT_FORM_DATA = {
  temperature: 92.4,
  rpm: 2800,
  pressure: 31.5,
  vibration: 0.64,
  operating_hours: 4820
};

export default function App() {
  const [formData, setFormData] = useState(DEFAULT_FORM_DATA);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [health, setHealth] = useState(null);
  const [modelInfo, setModelInfo] = useState(null);
  const [driftStatus, setDriftStatus] = useState(null);
  const [history, setHistory] = useState([]);
  const [errorMsg, setErrorMsg] = useState(null);
  const [activeTab, setActiveTab] = useState('all'); // 'all' | 'telemetry' | 'mlops'

  const fetchSystemStatus = async () => {
    try {
      const [healthRes, infoRes, historyRes, driftRes] = await Promise.all([
        getHealth().catch(() => null),
        getModelInfo().catch(() => null),
        getHistory().catch(() => []),
        getDriftStatus().catch(() => null)
      ]);

      if (healthRes) setHealth(healthRes);
      if (infoRes) setModelInfo(infoRes);
      if (historyRes) setHistory(historyRes);
      if (driftRes) setDriftStatus(driftRes);
    } catch (err) {
      console.warn("Status fetch warning:", err);
    }
  };

  // Initial data loading with periodic retry if backend is waking up
  useEffect(() => {
    fetchSystemStatus();
    const interval = setInterval(() => {
      if (!health) {
        fetchSystemStatus();
      }
    }, 6000);
    return () => clearInterval(interval);
  }, [health]);

  const handleFieldChange = (name, value) => {
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSelectPreset = (presetData) => {
    setFormData(presetData);
  };

  const handleResetForm = () => {
    setFormData(DEFAULT_FORM_DATA);
  };

  const handleSelectHistoryRow = (rowData) => {
    setFormData({
      temperature: rowData.temperature,
      rpm: rowData.rpm,
      pressure: rowData.pressure,
      vibration: rowData.vibration,
      operating_hours: rowData.operating_hours
    });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleSubmit = useCallback(async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    setLoading(true);
    setErrorMsg(null);

    try {
      const pred = await predictMaintenance(formData);
      setResult(pred);

      // Refresh history & drift metrics
      const [updatedHistory, updatedDrift] = await Promise.all([
        getHistory().catch(() => []),
        getDriftStatus().catch(() => null)
      ]);
      setHistory(updatedHistory);
      if (updatedDrift) setDriftStatus(updatedDrift);
    } catch (err) {
      console.error("Prediction error:", err);
      const isNetworkError = !err.response && (err.code === 'ERR_NETWORK' || err.message?.includes('Network Error'));
      setErrorMsg(
        err.response?.data?.detail ||
        (isNetworkError
          ? "Unable to reach prediction service. The Render backend may be waking up from free-tier sleep (takes ~30-50s). Please wait a moment and try again."
          : "Unable to reach prediction service. Please ensure the backend is running.")
      );
    } finally {
      setLoading(false);
    }
  }, [formData]);

  // Global Keyboard Shortcut: Cmd/Ctrl + Enter to trigger prediction
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        e.preventDefault();
        handleSubmit();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleSubmit]);

  const handleClearHistory = async () => {
    if (!window.confirm("Are you sure you want to clear the prediction history log?")) return;
    try {
      await clearHistory();
      setHistory([]);
    } catch (err) {
      console.error("Failed to clear history:", err);
    }
  };

  return (
    <div className="app-container">
      <Header health={health} modelInfo={modelInfo} />

      {/* Top View Selector & Presets */}
      <div className="view-nav-bar">
        <div className="nav-pill-group">
          <button
            type="button"
            className={`nav-tab-btn ${activeTab === 'all' ? 'active' : ''}`}
            onClick={() => setActiveTab('all')}
          >
            <LayoutGrid size={13} />
            <span>ALL MODULES</span>
          </button>
          <button
            type="button"
            className={`nav-tab-btn ${activeTab === 'telemetry' ? 'active' : ''}`}
            onClick={() => setActiveTab('telemetry')}
          >
            <Sliders size={13} />
            <span>TELEMETRY & INFERENCE</span>
          </button>
          <button
            type="button"
            className={`nav-tab-btn ${activeTab === 'batch' ? 'active' : ''}`}
            onClick={() => setActiveTab('batch')}
          >
            <Upload size={13} />
            <span>BATCH PREDICT</span>
          </button>
          <button
            type="button"
            className={`nav-tab-btn ${activeTab === 'mlops' ? 'active' : ''}`}
            onClick={() => setActiveTab('mlops')}
          >
            <Layers size={13} />
            <span>MLOPS & AUDIT LOG</span>
          </button>
        </div>

        <PresetBar onSelectPreset={handleSelectPreset} />
      </div>

      {errorMsg && (
        <div className="notification-banner">
          <span>{errorMsg}</span>
          <button
            type="button"
            onClick={() => setErrorMsg(null)}
            className="preset-btn"
            style={{ padding: '2px 8px', fontSize: '0.68rem' }}
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Primary Telemetry & Prediction Studio */}
      {(activeTab === 'all' || activeTab === 'telemetry') && (
        <div className="main-grid">
          <TelemetryForm
            formData={formData}
            onChange={handleFieldChange}
            onSubmit={handleSubmit}
            loading={loading}
            onReset={handleResetForm}
          />

          <PredictionResult result={result} />
        </div>
      )}

      {/* Batch Predict */}
      {(activeTab === 'all' || activeTab === 'batch') && (
        <BatchPredict />
      )}

      {/* MLOps Radar & Database Audit Log */}
      {(activeTab === 'all' || activeTab === 'mlops') && (
        <>
          <DriftMonitor
            driftStatus={driftStatus}
            modelInfo={modelInfo}
            onRefresh={fetchSystemStatus}
          />

          <HistoryTable
            history={history}
            onSelectRow={handleSelectHistoryRow}
            onClearHistory={handleClearHistory}
            onExport={exportHistory}
          />
        </>
      )}
    </div>
  );
}
