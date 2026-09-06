import React, { useState, useEffect, useCallback } from 'react';
import { Terminal, LogOut, Shield, User, Clock, Radio, Camera, FileText, ExternalLink, Trash2, Cloud, Eye } from 'lucide-react';
import { getSession, logout, logPageAccess, getAccessLog, getReportsForUser, deleteReport } from '../auth';
import { isCloudinaryConfigured } from '../cloudinary';
import ReportDetailModal from '../components/ReportDetailModal';

// Existing PMS modules
import PresetBar from '../components/PresetBar';
import TelemetryForm from '../components/TelemetryForm';
import PredictionResult from '../components/PredictionResult';
import HistoryTable from '../components/HistoryTable';
import DriftMonitor from '../components/DriftMonitor';
import BatchPredict from '../components/BatchPredict';
import RULForecastCard from '../components/RULForecastCard';
import {
  getHealth, getModelInfo, predictMaintenance, predictRul,
  getHistory, clearHistory, getDriftStatus, exportHistory,
  API_BASE_URL
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
  const [myReports,   setMyReports]   = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);
  const [rulForecast, setRulForecast] = useState(null);
  const [rulLoading,  setRulLoading]  = useState(false);

  const refreshReports = useCallback(() => {
    if (session?.userId) setMyReports(getReportsForUser(session?.userId));
  }, [session?.userId]);

  const fetchRulForecast = useCallback(async (currentData) => {
    setRulLoading(true);
    try {
      const target = currentData || formData;
      const trajectory = [];
      const steps = 20;
      for (let i = 0; i < steps; i++) {
        const factor = (i + 1) / steps;
        trajectory.push({
          temperature: +(target.temperature - (1 - factor) * 8 + (Math.sin(i) * 0.8)).toFixed(1),
          rpm: Math.round(target.rpm + (Math.cos(i) * 40)),
          pressure: +(target.pressure - (1 - factor) * 3 + (Math.sin(i * 0.5) * 0.5)).toFixed(1),
          vibration: +(Math.max(0.12, target.vibration - (1 - factor) * 0.12 + (Math.cos(i) * 0.02))).toFixed(2),
          operating_hours: Math.round(target.operating_hours - (steps - i) * 0.5)
        });
      }
      const rulRes = await predictRul(trajectory);
      setRulForecast(rulRes);
    } catch (err) {
      console.warn('RUL calculation note:', err);
    } finally {
      setRulLoading(false);
    }
  }, [formData]);

  // Log page access on mount
  useEffect(() => {
    logPageAccess('dashboard');
    const log = getAccessLog().filter(e => e.userId === session?.userId);
    setMyAccessLog(log);
    refreshReports();
  }, [session?.userId, refreshReports]);

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

  const refreshAccessLog = useCallback(() => {
    const log = getAccessLog().filter(e => e.userId === session?.userId);
    setMyAccessLog(log);
  }, [session?.userId]);

  useEffect(() => {
    fetchSystemStatus();
    fetchRulForecast(DEFAULT_FORM_DATA);
    const interval = setInterval(() => {
      fetchSystemStatus();
    }, 15000);
    return () => clearInterval(interval);
  }, [fetchRulForecast]);

  const handleFieldChange = (name, value) => setFormData(prev => ({ ...prev, [name]: value }));
  const handleSelectPreset = (presetData) => {
    setFormData(presetData);
    fetchRulForecast(presetData);
  };
  const handleResetForm = () => setFormData(DEFAULT_FORM_DATA);

  const handleSelectHistoryRow = (rowData) => {
    const nextData = {
      temperature: rowData.temperature,
      rpm: rowData.rpm,
      pressure: rowData.pressure,
      vibration: rowData.vibration,
      operating_hours: rowData.operating_hours
    };
    setFormData(nextData);
    fetchRulForecast(nextData);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleSubmit = useCallback(async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    setLoading(true);
    setErrorMsg(null);
    try {
      const pred = await predictMaintenance(formData);
      setResult(pred);
      fetchRulForecast(formData);
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
  }, [formData, fetchRulForecast]);

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
            <p className="brand-tagline">Predictive Telemetry · Root Cause Diagnostics · Drift Radar</p>
          </div>
        </div>

        <div className="header-status">
          {/* Employee avatar */}
          {session?.avatarUrl
            ? <img src={session.avatarUrl} alt={session?.name} style={{ width: 30, height: 30, borderRadius: '50%', objectFit: 'cover', border: '1px solid var(--border-medium)', flexShrink: 0 }} />
            : <div style={{ width: 30, height: 30, borderRadius: '50%', background: '#18181b', border: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.72rem', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--text-secondary)', flexShrink: 0 }}>{session?.name?.split(' ').map(w => w[0]).join('').slice(0,2).toUpperCase()}</div>
          }
          <div className="model-badge">
            <User size={13} />
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', lineHeight: 1.2 }}>
              <span>{session?.name}</span>
              <span style={{ fontSize: '0.65rem', color: '#38bdf8', fontWeight: 400 }}>
                {session?.designation || (session?.role === 'admin' ? 'System Administrator' : 'Maintenance Specialist')}
              </span>
            </div>
          </div>
          {modelInfo?.metrics?.roc_auc && (
            <div className="model-badge">
              <span>PMS Core [{modelInfo.version || 'v1'}]</span>
              <span style={{ color: 'var(--text-dim)' }}>·</span>
              <span>Accuracy {(modelInfo.metrics.roc_auc * 100).toFixed(1)}%</span>
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
            <span>{isHealthy ? 'ONLINE' : 'CONNECTING'}</span>
          </div>
          <a
            href={`${API_BASE_URL}/docs`}
            target="_blank"
            rel="noreferrer"
            className="preset-btn"
            style={{ padding: '6px 12px', gap: 6, textDecoration: 'none', color: 'inherit' }}
            title="Open Interactive Swagger OpenAPI Documentation"
          >
            <ExternalLink size={13} /> API Docs
          </a>
          <button type="button" className="preset-btn" onClick={handleLogout} style={{ padding: '6px 12px', gap: 6 }}>
            <LogOut size={13} /> Sign Out
          </button>
        </div>
      </header>

      {/* Tab Navigation */}
      <div className="view-nav-bar">
        <div className="nav-pill-group">
          {[
            { key: 'all',       icon: <LayoutGrid size={13} />, label: 'ALL MODULES' },
            { key: 'telemetry', icon: <Sliders size={13} />,    label: 'TELEMETRY & INFERENCE' },
            { key: 'batch',     icon: <Upload size={13} />,     label: 'BATCH PREDICT' },
            { key: 'mlops',     icon: <Layers size={13} />,     label: 'STABILITY & AUDIT LOG' },
            { key: 'myreports', icon: <FileText size={13} />,   label: `MY REPORTS${myReports.length ? ` [${myReports.length}]` : ''}` },
            { key: 'mylog',     icon: <Clock size={13} />,      label: 'MY ACCESS LOG' },
          ].map(tab => (
            <button
              key={tab.key}
              type="button"
              className={`nav-tab-btn ${activeTab === tab.key ? 'active' : ''}`}
              onClick={() => {
                setActiveTab(tab.key);
                if (tab.key === 'myreports') refreshReports();
                if (tab.key === 'mylog') refreshAccessLog();
              }}
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
        <>
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
          <RULForecastCard
            rulData={rulForecast}
            loading={rulLoading}
            onRefresh={() => fetchRulForecast(formData)}
          />
        </>
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

      {/* My Reports */}
      {activeTab === 'myreports' && (
        <div className="glass-panel">
          <div className="panel-header">
            <h2 className="panel-title">
              <FileText size={18} className="panel-icon" />
              <span>My Saved Reports</span>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontWeight: 400, fontFamily: 'var(--font-mono)' }}>
                [{myReports.length} reports]
              </span>
            </h2>
          </div>
          {myReports.length === 0 ? (
            <div className="empty-state">
              No saved reports yet. Run a prediction and click <strong style={{ color: '#fff' }}>Report → Save to Cloud</strong>.
            </div>
          ) : (
            <div className="reports-list">
              {myReports.map(r => (
                <div key={r.reportId} className={`report-card ${r.risk === 'HIGH' ? 'high' : 'low'}`}>
                  <div className="report-card-left">
                    <span className={`badge-risk ${r.risk === 'HIGH' ? 'high' : 'low'}`}>{r.risk}</span>
                    <div className="report-card-meta">
                      <span className="report-card-prob">{r.probability != null ? (r.probability * 100).toFixed(1) + '%' : '—'}</span>
                      <span className="report-card-date">{new Date(r.savedAt).toLocaleString()}</span>
                      {r.predictionId && (
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.66rem', color: 'var(--text-muted)' }}>
                          #{r.predictionId.slice(0, 10)}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="report-card-actions">
                    <button
                      type="button"
                      className="preset-btn highlight"
                      onClick={() => setSelectedReport(r)}
                      style={{ padding: '3px 10px', fontSize: '0.7rem', gap: 5 }}
                    >
                      <Eye size={11} /> View Doc
                    </button>
                    {r.cloudinaryUrl
                      ? <a href={r.cloudinaryUrl} target="_blank" rel="noreferrer" className="cloud-link"><ExternalLink size={11} /> Cloud Doc</a>
                      : <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>Local only</span>
                    }
                    <button
                      type="button"
                      className="preset-btn"
                      onClick={() => {
                        deleteReport(session?.userId, r.reportId);
                        setMyReports(getReportsForUser(session?.userId));
                      }}
                      style={{ padding: '3px 9px', fontSize: '0.7rem', color: '#fda4af', borderColor: 'rgba(244,63,94,0.3)', gap: 5 }}
                    >
                      <Trash2 size={11} /> Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* My Access Log */}
      {activeTab === 'mylog' && (
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

      {/* Modal for viewing individual generation doc */}
      {selectedReport && (
        <ReportDetailModal
          report={selectedReport}
          onClose={() => setSelectedReport(null)}
          onDelete={(r) => {
            deleteReport(session?.userId, r.reportId);
            setMyReports(getReportsForUser(session?.userId));
            setSelectedReport(null);
          }}
        />
      )}
    </div>
  );
}
