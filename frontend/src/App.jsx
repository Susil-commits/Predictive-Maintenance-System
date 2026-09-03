import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import PresetBar from './components/PresetBar';
import TelemetryForm from './components/TelemetryForm';
import PredictionResult from './components/PredictionResult';
import HistoryTable from './components/HistoryTable';
import { getHealth, getModelInfo, predictMaintenance, getHistory, clearHistory } from './api';

export default function App() {
  // Default initialized with user's exact specification
  const [formData, setFormData] = useState({
    temperature: 92.4,
    rpm: 2800,
    pressure: 31.5,
    vibration: 0.64,
    operating_hours: 4820
  });

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [health, setHealth] = useState(null);
  const [modelInfo, setModelInfo] = useState(null);
  const [history, setHistory] = useState([]);
  const [errorMsg, setErrorMsg] = useState(null);

  // Initial data loading
  useEffect(() => {
    const fetchSystemStatus = async () => {
      try {
        const [healthRes, infoRes, historyRes] = await Promise.all([
          getHealth().catch(() => null),
          getModelInfo().catch(() => null),
          getHistory().catch(() => [])
        ]);

        if (healthRes) setHealth(healthRes);
        if (infoRes) setModelInfo(infoRes);
        if (historyRes) setHistory(historyRes);
      } catch (err) {
        console.warn("Initial status fetch warning:", err);
      }
    };

    fetchSystemStatus();
  }, []);

  const handleFieldChange = (name, value) => {
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSelectPreset = (presetData) => {
    setFormData(presetData);
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

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    setLoading(true);
    setErrorMsg(null);

    try {
      const pred = await predictMaintenance(formData);
      setResult(pred);

      // Refresh history
      const updatedHistory = await getHistory();
      setHistory(updatedHistory);
    } catch (err) {
      console.error("Prediction error:", err);
      setErrorMsg(
        err.response?.data?.detail || "Unable to reach prediction service. Please ensure the backend is running."
      );
    } finally {
      setLoading(false);
    }
  };

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

      <PresetBar onSelectPreset={handleSelectPreset} />

      {errorMsg && (
        <div style={{
          padding: '12px 18px',
          background: 'rgba(244, 63, 94, 0.15)',
          border: '1px solid rgba(244, 63, 94, 0.4)',
          borderRadius: '12px',
          color: '#fecdd3',
          marginBottom: '20px',
          fontSize: '0.88rem'
        }}>
          {errorMsg}
        </div>
      )}

      <div className="dashboard-grid">
        <TelemetryForm
          formData={formData}
          onChange={handleFieldChange}
          onSubmit={handleSubmit}
          loading={loading}
        />

        <PredictionResult result={result} />
      </div>

      <HistoryTable
        history={history}
        onSelectRow={handleSelectHistoryRow}
        onClearHistory={handleClearHistory}
      />
    </div>
  );
}
