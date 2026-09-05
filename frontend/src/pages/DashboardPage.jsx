import React, { useState, useEffect, useCallback } from 'react';
import { Terminal, LogOut, Shield, User, Clock, Radio } from 'lucide-react';
import { getSession, logout, logPageAccess, getAccessLog } from '../auth';

// Existing PMS modules
import PresetBar from '../components/PresetBar';
import TelemetryForm from '../components/TelemetryForm';
import PredictionResult from '../components/PredictionResult';
import HistoryTable from '../components/HistoryTable';
import DriftMonitor from '../components/DriftMonitor';
import BatchPredict from '../components/BatchPredict';
import {
  getHealth, getModelInfo, predictMaintenance,
  getHistory, clearHistory, getDriftStatus, exportHistory
} from '../api';
import { Sliders, Layers, LayoutGrid, Upload } from 'lucide-react';

const DEFAULT_FORM_DATA = {
  temperature: 92.4,
  rpm: 2800,
  pressure: 31.5,
  vibration: 0.64,
  operating_hours: 4820
};

export default function DashboardPage({ onLogout }) {
  const session = getSession();

  const [formData, setFormData]     = useState(DEFAULT_FORM_DATA);
  const [result, setResult]         = useState(null);
  const [loading, setLoading]       = useState(false);
  const [health, setHealth]         = useState(null);
  const [modelInfo, setModelInfo]   = useState(null);
  const [driftStatus, setDriftStatus] = useState(null);
  const [history, setHistory]       = useState([]);
  const [errorMsg, setErrorMsg]     = useState(null);
  const [activeTab, setActiveTab]   = useState('all');
  const [myAccessLog, setMyAccessLog] = useState([]);

  // Log page access on mount
  useEffect(() => {
    logPageAccess('dashboard');
    // Build this user's own access log slice
    const log = getAccessLog().filter(e => e.userId === session?.userId);
    setMyAccessLog(log);
  }, [session?.userId]);

  const fetchSystemStatus = async () => {
    try {
      const [healthRes, infoRes, historyRes, driftRes] = await Promise.all([
        getHealth().catch(() => null),
        getModelInfo().catch(() => null),
        getHistory().catch(() => []),
        getDriftStatus().catch(() => null)
      ]);
      if (healthRes)  setHealth(healthRes);
      if (infoRes)    setModelInfo(infoRes);
      if (historyRes) setHistory(historyRes);
      if (driftRes)   setDriftStatus(driftRes);
    } catch (err) {
      console.warn('Status fetch warning:', err);
    }
  };

  useEffect(() => {
    fetchSystemStatus();
    const interval = setInterval(() => {
      if (!health) fetchSystemStatus();
    }, 6000);
    return () => clearInterval(interval);
  }, [health]);

  const handleFieldChange = (name, value) => setFormData(prev => ({ ...prev, [name]: value }));
  const handleSelectPreset = (presetData) => setFormData(presetData);
  const handleResetForm = () => setFormData(DEFAULT_FORM_DATA);

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
      const [updatedHistory, updatedDrift] = await Promise.all([
        getHistory().catch(() => []),
        getDriftStatus().catch(() => null)
      ]);
      setHistory(updatedHistory);
      if (updatedDrift) setDriftStatus(updatedDrift);
    } catch (err) {
      const isNetworkError = !err.response && (err.code === 'ERR_NETWORK' || err.message?.includes('Network Error'));
      setErrorMsg(
        err.response?.data?.detail ||
        (isNetworkError
          ? 'Unable to reach prediction service. The Render backend may be waking up (~30-50s). Please wait and try again.'
          : 'Unable to reach prediction service. Please ensure the backend is running.')
      );
    } finally {
      setLoading(false);
    }
  }, [formData]);

  useEffect(() => {
    const handler = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        e.preventDefault();
        handleSubmit();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [handleSubmit]);

  const handleClearHistory = async () => {
    if (!window.confirm('Clear the prediction history log?')) return;
    try { await clearHistory(); setHistory([]); } catch {}
  };

  const handleLogout = () => {
    logout();
    onLogout();
  };

  const isHealthy = health?.status === 'healthy';

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="brand-wrapper">
          <div className="brand-icon"><Terminal size={20} /></div>
          <div className="brand-title-group">
            <h1 className="brand-title">
              <span>pms://telemetry</span>
              <span style={{ color: 'var(--text-dim)', fontWeight: 400 }}>//</span>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', fontWeight: 500 }}>inference-core</span>
            </h1>
            <p className="brand-tagline">Calibrated XGBoost · SHAP Waterfall Diagnostics · Drift Radar</p>
          </div>
        </div>

        <div className="header-status">
          {/* Employee identity chip */}
          <div className="model-badge">
            <User size={13} />
            <span>{session?.name}</span>
          </div>
          {modelInfo?.metrics?.roc_auc && (
            <div className="model-badge">
              <span>XGBoost [{modelInfo.version || 'v1'}]</span>
              <span style={{ color: 'var(--text-dim)' }}>·</span>
              <span>AUC {(modelInfo.metrics.roc_auc * 100).toFixed(1)}%</span>
            </div>
          )}
          <div
            className="status-chip"
            title={isHealthy ? 'Backend connected and ready' : 'Connecting to Render service...'}
            style={{ color: isHealthy ? '#ffffff' : '#f59e0b' }}
          >
            <span
              className="status-dot"
              style={{
                backgroundColor: isHealthy ? '#10b981' : '#f59e0b',
                color: isHealthy ? '#10b981' : '#f59e0b'
              }}
            />
            <Radio size={12} style={{ opacity: 0.8 }} />
            <span>{isHealthy ? 'LIVE' : 'CONNECTING'}</span>
          </div>
          <button type="button" className="preset-btn" onClick={handleLogout} style={{ padding: '6px 12px', gap: 6 }}>
            <LogOut size={13} /> Sign Out
          </button>
        </div>
      </header>

      {/* Tab Navigation */}
      <div className="view-nav-bar">
        <div className="nav-pill-group">
          {[
            { key: 'all',      icon: <LayoutGrid size={13} />, label: 'ALL MODULES' },
            { key: 'telemetry',icon: <Sliders size={13} />,    label: 'TELEMETRY & INFERENCE' },
            { key: 'batch',    icon: <Upload size={13} />,     label: 'BATCH PREDICT' },
            { key: 'mlops',    icon: <Layers size={13} />,     label: 'MLOPS & AUDIT LOG' },
            { key: 'mylog',    icon: <Clock size={13} />,      label: 'MY ACCESS LOG' },
          ].map(tab => (
            <button
              key={tab.key}
              type="button"
              className={`nav-tab-btn ${activeTab === tab.key ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.key)}
            >
              {tab.icon}
              <span>{tab.label}</span>
            </button>
          ))}
        </div>
        <PresetBar onSelectPreset={handleSelectPreset} />
      </div>

      {/* Error banner */}
      {errorMsg && (
        <div className="notification-banner">
          <span>{errorMsg}</span>
          <button type="button" onClick={() => setErrorMsg(null)} className="preset-btn" style={{ padding: '2px 8px', fontSize: '0.68rem' }}>
            Dismiss
          </button>
        </div>
      )}

      {/* Telemetry */}
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

      {/* Batch */}
      {(activeTab === 'all' || activeTab === 'batch') && <BatchPredict />}

      {/* MLOps */}
      {(activeTab === 'all' || activeTab === 'mlops') && (
        <>
          <DriftMonitor driftStatus={driftStatus} modelInfo={modelInfo} onRefresh={fetchSystemStatus} />
          <HistoryTable
            history={history}
            onSelectRow={handleSelectHistoryRow}
            onClearHistory={handleClearHistory}
            onExport={exportHistory}
          />
        </>
      )}

      {/* My Access Log */}
      {(activeTab === 'mylog') && (
        <div className="glass-panel">
          <div className="panel-header">
            <h2 className="panel-title">
              <Clock size={18} className="panel-icon" />
              <span>My Access Log</span>
            </h2>
            <span className="field-unit">{myAccessLog.length} EVENTS</span>
          </div>
          {myAccessLog.length === 0 ? (
            <div className="empty-state">No access events yet for your account.</div>
          ) : (
            <div className="table-responsive">
              <table className="history-table">
                <thead>
                  <tr>
                    <th>Login Time</th>
                    <th>Page Accessed</th>
                    <th>Session</th>
                  </tr>
                </thead>
                <tbody>
                  {myAccessLog.map((e, i) => (
                    <tr key={i}>
                      <td style={{ color: 'var(--text-dim)' }}>
                        {new Date(e.loginAt || e.accessedAt).toLocaleString()}
                      </td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.74rem' }}>
                        {e.page || 'login'}
                      </td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.70rem', color: 'var(--text-muted)' }}>
                        {e.userId}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
