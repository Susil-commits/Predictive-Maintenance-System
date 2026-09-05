import React, { useState } from 'react';
import {
  X, FileText, ExternalLink, Trash2, AlertOctagon,
  CheckCircle2, TrendingUp, TrendingDown, Clock,
  User, Database, Cloud, Code, Layers
} from 'lucide-react';

export default function ReportDetailModal({ report, onClose, onDelete }) {
  const [activeTab, setActiveTab] = useState('summary'); // 'summary' | 'json'
  const [deleteConfirm, setDeleteConfirm] = useState(false);

  if (!report) return null;

  const isHighRisk = report.risk === 'HIGH';
  const probPercent = report.probability != null ? (report.probability * 100).toFixed(1) : '—';
  const factors = report.shapFactors || [];
  const maxImp = factors.length > 0
    ? Math.max(...factors.map(f => f.importance || Math.abs(f.impact || 0)))
    : 1;

  const handleDelete = () => {
    if (!deleteConfirm) {
      setDeleteConfirm(true);
      setTimeout(() => setDeleteConfirm(false), 3500);
      return;
    }
    if (onDelete) {
      onDelete(report);
      onClose();
    }
  };

  return (
    <div className="report-viewer-overlay" onClick={onClose}>
      <div className="report-viewer-card" style={{ maxWidth: 680, maxHeight: '88vh' }} onClick={e => e.stopPropagation()}>
        {/* Modal Top Bar */}
        <div className="report-viewer-bar" style={{ borderBottom: '1px solid var(--border-subtle)', paddingBottom: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{
              width: 32, height: 32, borderRadius: 8,
              background: 'rgba(255,255,255,0.06)',
              border: '1px solid var(--border-subtle)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: '#ffffff'
            }}>
              <FileText size={16} />
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '0.92rem', color: '#ffffff', display: 'flex', alignItems: 'center', gap: 8 }}>
                <span>Individual Generation Doc</span>
                <span className={`badge-risk ${isHighRisk ? 'high' : 'low'}`} style={{ fontSize: '0.66rem', padding: '2px 8px' }}>
                  {report.risk}
                </span>
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: 'var(--text-dim)', marginTop: 2 }}>
                ID: {report.reportId}
              </div>
            </div>
          </div>
          <button type="button" className="login-eye-btn" onClick={onClose} title="Close">
            <X size={18} />
          </button>
        </div>

        {/* Metadata Banner */}
        <div style={{
          display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'center',
          padding: '10px 14px', background: 'rgba(255,255,255,0.02)',
          border: '1px solid var(--border-subtle)', borderRadius: 8, margin: '14px 0',
          fontSize: '0.74rem', fontFamily: 'var(--font-mono)'
        }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 5, color: '#ffffff' }}>
            <User size={12} style={{ color: 'var(--text-dim)' }} /> {report.userName || 'Anonymous'}
          </span>
          <span style={{ color: 'var(--border-medium)' }}>|</span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 5, color: 'var(--text-secondary)' }}>
            <Clock size={12} style={{ color: 'var(--text-dim)' }} /> {new Date(report.savedAt).toLocaleString()}
          </span>
          {report.predictionId && (
            <>
              <span style={{ color: 'var(--border-medium)' }}>|</span>
              <span style={{ color: 'var(--text-dim)' }}>Pred: #{report.predictionId.slice(0, 10)}</span>
            </>
          )}
          {report.cloudinaryUrl && (
            <a
              href={report.cloudinaryUrl}
              target="_blank"
              rel="noreferrer"
              className="cloud-link"
              style={{ marginLeft: 'auto' }}
            >
              <Cloud size={11} /> Cloud Doc <ExternalLink size={10} />
            </a>
          )}
        </div>

        {/* Tab switch */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 14 }}>
          <button
            type="button"
            className={`nav-pill ${activeTab === 'summary' ? 'active' : ''}`}
            onClick={() => setActiveTab('summary')}
            style={{ padding: '4px 12px', fontSize: '0.74rem' }}
          >
            <Layers size={12} /> Diagnostic Summary
          </button>
          <button
            type="button"
            className={`nav-pill ${activeTab === 'json' ? 'active' : ''}`}
            onClick={() => setActiveTab('json')}
            style={{ padding: '4px 12px', fontSize: '0.74rem' }}
          >
            <Code size={12} /> Raw JSON Payload
          </button>
        </div>

        {/* Content Area */}
        <div style={{ overflowY: 'auto', maxHeight: '50vh', paddingRight: 4 }}>
          {activeTab === 'summary' ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {/* Verdict row */}
              <div className={`risk-banner ${isHighRisk ? 'high' : 'low'}`} style={{ padding: '12px 16px' }}>
                <div className="risk-info">
                  <span className="risk-tag">Classification Verdict</span>
                  <div className={`risk-value ${isHighRisk ? 'high' : 'low'}`} style={{ fontSize: '1.2rem' }}>
                    {isHighRisk ? (
                      <><AlertOctagon size={22} color="#fb7185" /><span>RISK: HIGH</span></>
                    ) : (
                      <><CheckCircle2 size={22} color="#34d399" /><span>RISK: LOW</span></>
                    )}
                  </div>
                </div>
                <div className="prob-meter-card" style={{ minWidth: 90, padding: '6px 12px' }}>
                  <div className="prob-number" style={{ fontSize: '1.4rem', color: isHighRisk ? '#fb7185' : '#34d399' }}>
                    {probPercent}%
                  </div>
                  <span className="prob-label">Probability</span>
                </div>
              </div>

              {/* Input Telemetry */}
              <div>
                <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-dim)', marginBottom: 8, fontWeight: 600 }}>
                  Input Sensor Telemetry
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))', gap: 8 }}>
                  {Object.entries(report.inputData || {}).map(([key, val]) => (
                    <div key={key} style={{
                      background: 'rgba(255,255,255,0.03)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 6, padding: '8px 10px'
                    }}>
                      <div style={{ fontSize: '0.66rem', color: 'var(--text-dim)', textTransform: 'uppercase', fontFamily: 'var(--font-mono)' }}>
                        {key.replace('_', ' ')}
                      </div>
                      <div style={{ fontSize: '0.88rem', fontWeight: 600, color: '#ffffff', fontFamily: 'var(--font-mono)', marginTop: 2 }}>
                        {typeof val === 'number' ? val.toFixed(2) : String(val)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Contributing factors */}
              {factors.length > 0 && (
                <div>
                  <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-dim)', marginBottom: 8, fontWeight: 600 }}>
                    Tree-SHAP Feature Attribution
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {factors.map((factor, idx) => {
                      const isPositive = factor.impact >= 0;
                      const barWidth = Math.max(8, Math.min(100, Math.round(((factor.importance || Math.abs(factor.impact || 0)) / (maxImp || 1)) * 100)));
                      return (
                        <div key={idx} style={{
                          background: 'rgba(255,255,255,0.02)',
                          border: '1px solid var(--border-subtle)',
                          borderRadius: 6, padding: '8px 10px'
                        }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.76rem', marginBottom: 4 }}>
                            <span style={{ color: '#ffffff', fontWeight: 500 }}>{factor.factor}</span>
                            <span className={`factor-impact ${isPositive ? 'positive' : 'negative'}`} style={{ fontSize: '0.72rem' }}>
                              {isPositive ? <TrendingUp size={11} style={{ display: 'inline', marginRight: 3 }} /> : <TrendingDown size={11} style={{ display: 'inline', marginRight: 3 }} />}
                              {isPositive ? `+${factor.impact?.toFixed(3)}` : factor.impact?.toFixed(3)}
                            </span>
                          </div>
                          <div className="factor-bar-bg" style={{ height: 4 }}>
                            <div
                              className="factor-bar-fill"
                              style={{ width: `${barWidth}%`, backgroundColor: isPositive ? '#fb7185' : '#34d399' }}
                            />
                          </div>
                          {factor.description && (
                            <p style={{ fontSize: '0.66rem', color: 'var(--text-dim)', margin: '4px 0 0 0' }}>
                              {factor.description}
                            </p>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <pre className="report-viewer-pre" style={{ maxHeight: '45vh' }}>
              {JSON.stringify(report, null, 2)}
            </pre>
          )}
        </div>

        {/* Footer Actions */}
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          borderTop: '1px solid var(--border-subtle)', paddingTop: 12, marginTop: 14
        }}>
          {onDelete && (
            <button
              type="button"
              className="preset-btn"
              onClick={handleDelete}
              style={{
                padding: '5px 12px', fontSize: '0.72rem', gap: 6,
                color: deleteConfirm ? '#ffffff' : '#fda4af',
                borderColor: deleteConfirm ? '#f43f5e' : 'rgba(244, 63, 94, 0.3)',
                background: deleteConfirm ? 'rgba(244, 63, 94, 0.2)' : undefined,
              }}
            >
              <Trash2 size={12} />
              {deleteConfirm ? 'Confirm Delete Document?' : 'Delete Document'}
            </button>
          )}
          <button
            type="button"
            className="preset-btn highlight"
            onClick={onClose}
            style={{ marginLeft: 'auto', padding: '5px 14px', fontSize: '0.74rem' }}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
