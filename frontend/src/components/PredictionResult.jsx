import React, { useState } from 'react';
import {
  AlertOctagon, CheckCircle2, TrendingUp, TrendingDown,
  Terminal, ShieldAlert, Hash, Clock,
  Cloud, Eye, EyeOff, Save, ExternalLink,
  Loader2, Check, Trash2, X, FileText,
  Wrench, Sparkles, ArrowRight
} from 'lucide-react';
import { uploadPredictionReport, isCloudinaryConfigured } from '../cloudinary';
import { getSession, saveReport } from '../auth';
import { predictCounterfactual } from '../api';

// ── Inline JSON viewer ────────────────────────────────────────────────────────
// ── Inline Report viewer ────────────────────────────────────────────────────────
function ReportViewer({ result, onClose, onSave, savedEntry }) {
  const [tab, setTab] = useState('summary');
  const [saving, setSaving] = useState(false);
  const json = JSON.stringify(result, null, 2);
  const isHighRisk = result?.failure_risk === 'HIGH';

  const handleSaveInternal = async () => {
    if (!onSave || saving || savedEntry) return;
    setSaving(true);
    try {
      await onSave();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="report-viewer-overlay" onClick={onClose}>
      <div className="report-viewer-card" style={{ maxWidth: 640 }} onClick={e => e.stopPropagation()}>
        <div className="report-viewer-bar">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <FileText size={15} style={{ color: '#ffffff' }} />
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: '#ffffff', fontWeight: 600 }}>
              report_{result?.prediction_id?.slice(0, 8) || 'preview'}.json
            </span>
            <span className={`badge-risk ${isHighRisk ? 'high' : 'low'}`} style={{ fontSize: '0.66rem' }}>
              {result?.failure_risk}
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {savedEntry ? (
              <span style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: '0.72rem', color: '#34d399', fontFamily: 'var(--font-mono)' }}>
                <Check size={12} /> Saved
              </span>
            ) : (
              <button
                type="button"
                className="report-action-btn save"
                onClick={handleSaveInternal}
                disabled={saving}
                style={{ padding: '3px 10px', fontSize: '0.72rem' }}
              >
                {saving ? <><Loader2 size={11} className="batch-spin" /> Saving...</> : <><Cloud size={11} /> Save to Cloud</>}
              </button>
            )}
            <button type="button" className="login-eye-btn" onClick={onClose}>
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Tab buttons */}
        <div style={{ display: 'flex', gap: 6, margin: '10px 0' }}>
          <button
            type="button"
            className={`nav-pill ${tab === 'summary' ? 'active' : ''}`}
            onClick={() => setTab('summary')}
            style={{ padding: '3px 10px', fontSize: '0.72rem' }}
          >
            Formatted Summary
          </button>
          <button
            type="button"
            className={`nav-pill ${tab === 'json' ? 'active' : ''}`}
            onClick={() => setTab('json')}
            style={{ padding: '3px 10px', fontSize: '0.72rem' }}
          >
            Raw JSON
          </button>
        </div>

        {tab === 'summary' ? (
          <div style={{ maxHeight: '52vh', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 10, paddingRight: 4 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px', background: 'rgba(255,255,255,0.03)', borderRadius: 6 }}>
              <div>
                <span style={{ fontSize: '0.68rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Verdict</span>
                <div style={{ fontWeight: 700, color: isHighRisk ? '#fb7185' : '#34d399', fontSize: '1rem' }}>
                  {isHighRisk ? 'HIGH RISK' : 'LOW RISK (NOMINAL)'}
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <span style={{ fontSize: '0.68rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Probability</span>
                <div style={{ fontWeight: 700, color: '#ffffff', fontSize: '1rem', fontFamily: 'var(--font-mono)' }}>
                  {(result.probability * 100).toFixed(1)}%
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 10px', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-subtle)', borderRadius: 6, fontSize: '0.72rem' }}>
              <span style={{ color: 'var(--text-dim)' }}>
                Assessor: <strong style={{ color: '#ffffff' }}>{getSession()?.name || 'Assessor'}</strong>
              </span>
              <span style={{ color: '#38bdf8', fontFamily: 'var(--font-mono)' }}>
                {getSession()?.designation || (getSession()?.role === 'admin' ? 'System Administrator' : 'Maintenance Specialist')}
              </span>
            </div>

            <div>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)', textTransform: 'uppercase', marginBottom: 6 }}>Input Telemetry</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(110px, 1fr))', gap: 6 }}>
                {Object.entries(result.input_data || {}).map(([k, v]) => (
                  <div key={k} style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-subtle)', borderRadius: 4, padding: '6px 8px' }}>
                    <div style={{ fontSize: '0.62rem', color: 'var(--text-dim)' }}>{k}</div>
                    <div style={{ fontSize: '0.8rem', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                      {typeof v === 'number' ? v.toFixed(2) : String(v)}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {result.contributing_factors?.length > 0 && (
              <div>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)', textTransform: 'uppercase', marginBottom: 6 }}>Top Attributions</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  {result.contributing_factors.slice(0, 4).map((f, i) => (
                    <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.74rem', background: 'rgba(255,255,255,0.02)', padding: '5px 8px', borderRadius: 4 }}>
                      <span>{f.factor}</span>
                      <span style={{ fontFamily: 'var(--font-mono)', color: f.impact >= 0 ? '#fb7185' : '#34d399' }}>
                        {f.impact >= 0 ? `+${f.impact.toFixed(3)}` : f.impact.toFixed(3)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {result.suggested_action && (
              <div style={{ padding: '8px 10px', background: isHighRisk ? 'rgba(251, 113, 133, 0.08)' : 'rgba(52, 211, 153, 0.08)', border: `1px solid ${isHighRisk ? 'rgba(251, 113, 133, 0.25)' : 'rgba(52, 211, 153, 0.25)'}`, borderRadius: 6 }}>
                <div style={{ fontSize: '0.64rem', color: isHighRisk ? '#fb7185' : '#34d399', textTransform: 'uppercase', fontWeight: 600, marginBottom: 4 }}>
                  Root Cause Guidance {result.top_risk_factor ? `[${result.top_risk_factor.toUpperCase()}]` : ''}
                </div>
                <div style={{ fontSize: '0.74rem', color: '#f4f4f5', lineHeight: 1.4 }}>
                  {result.suggested_action}
                </div>
              </div>
            )}
          </div>
        ) : (
          <pre className="report-viewer-pre" style={{ maxHeight: '52vh' }}>{json}</pre>
        )}
      </div>
    </div>
  );
}

// ── Save / View prompt ────────────────────────────────────────────────────────
function ReportPrompt({ result, onSaved, onView, onClose }) {
  const [saving, setSaving]   = useState(false);
  const [saved,  setSaved]    = useState(false);
  const [err,    setErr]      = useState('');
  const cloudReady = isCloudinaryConfigured();

  const handleSave = async () => {
    setSaving(true); setErr('');
    try {
      const session = getSession();
      let cloudinaryUrl = null;

      if (cloudReady) {
        cloudinaryUrl = await uploadPredictionReport(result, result.prediction_id || Date.now());
      }

      const entry = saveReport({
        predictionId:  result.prediction_id || null,
        risk:          result.failure_risk,
        probability:   result.probability,
        inputData:     result.input_data || {},
        shapFactors:   result.contributing_factors || [],
        cloudinaryUrl,
        userId:        session?.userId,
        userName:      session?.name,
        userDesignation: session?.designation || (session?.role === 'admin' ? 'System Administrator' : 'Maintenance Specialist'),
      });

      setSaved(true);
      onSaved(entry);
    } catch (e) {
      setErr(e.message || 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  if (saved) {
    return (
      <div className="report-prompt">
        <div className="report-prompt-saved">
          <Check size={15} style={{ color: '#34d399' }} />
          <span>Report saved to your profile</span>
        </div>
        <button type="button" className="preset-btn" onClick={onClose} style={{ padding: '4px 10px', fontSize: '0.72rem' }}>
          <X size={11} /> Dismiss
        </button>
      </div>
    );
  }

  return (
    <div className="report-prompt">
      <span className="report-prompt-label">
        <FileText size={13} /> Diagnostic generated: Save to cloud or just view?
      </span>
      <div className="report-prompt-actions">
        <button
          type="button"
          className="report-action-btn view"
          onClick={onView}
        >
          <Eye size={13} /> View Report
        </button>
        <button
          type="button"
          className="report-action-btn save"
          onClick={handleSave}
          disabled={saving}
        >
          {saving
            ? <><Loader2 size={13} className="batch-spin" /> Saving...</>
            : <><Cloud size={13} /> {cloudReady ? 'Save to Cloud' : 'Save to Profile'}</>}
        </button>
        <button type="button" className="login-eye-btn" onClick={onClose} style={{ marginLeft: 'auto' }}>
          <X size={14} />
        </button>
      </div>
      {err && <span style={{ fontSize: '0.7rem', color: '#fb7185', fontFamily: 'var(--font-mono)' }}>{err}</span>}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export default function PredictionResult({ result }) {
  const [showPrompt,  setShowPrompt]  = useState(false);
  const [showViewer,  setShowViewer]  = useState(false);
  const [savedEntry,  setSavedEntry]  = useState(null);
  const [cfData,      setCfData]      = useState(null);
  const [cfLoading,   setCfLoading]   = useState(false);
  const [cfError,     setCfError]     = useState(null);

  // When a new result comes in, automatically ask whether to View or Save and evaluate counterfactual if high risk
  React.useEffect(() => {
    if (result) {
      setShowPrompt(true);
      setShowViewer(false);
      setSavedEntry(null);
      setCfData(null);
      setCfError(null);

      // Auto-evaluate minimal counterfactual fix for HIGH risk predictions
      if (result.failure_risk === 'HIGH' && result.input_data) {
        setCfLoading(true);
        predictCounterfactual(result.input_data)
          .then(data => setCfData(data))
          .catch(err => setCfError(err.message || 'Counterfactual evaluation failed'))
          .finally(() => setCfLoading(false));
      }
    }
  }, [result?.prediction_id, result?.timestamp]);

  const handleFetchCounterfactual = () => {
    if (!result?.input_data || cfLoading) return;
    setCfLoading(true);
    setCfError(null);
    predictCounterfactual(result.input_data)
      .then(data => setCfData(data))
      .catch(err => setCfError(err.message || 'Counterfactual evaluation failed'))
      .finally(() => setCfLoading(false));
  };

  if (!result) {
    return (
      <div className="glass-panel">
        <div className="panel-header">
          <h2 className="panel-title">
            <ShieldAlert size={18} className="panel-icon" />
            <span>Diagnostics &amp; Root Cause Waterfall</span>
          </h2>
          <span className="field-unit">STANDBY</span>
        </div>
        <div className="empty-state">
          <div style={{
            width: 44, height: 44, borderRadius: '10px',
            background: '#121215', border: '1px solid rgba(255, 255, 255, 0.08)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            marginBottom: 16, color: '#71717a'
          }}>
            <Terminal size={22} />
          </div>
          <p style={{ maxWidth: 360, lineHeight: 1.6 }}>
            Telemetry stream idle. Select a preset or configure sensors, then click{' '}
            <strong style={{ color: '#ffffff' }}>EVALUATE TELEMETRY</strong> to run root cause diagnostic inference.
          </p>
        </div>
      </div>
    );
  }

  const isHighRisk  = result.failure_risk === 'HIGH';
  const probPercent = (result.probability * 100).toFixed(1);
  const factors     = result.contributing_factors || [];
  const maxImp      = factors.length > 0 ? Math.max(...factors.map(f => f.importance || Math.abs(f.impact))) : 1;

  const handleDirectSave = async () => {
    const session = getSession();
    let cloudinaryUrl = null;
    if (isCloudinaryConfigured()) {
      cloudinaryUrl = await uploadPredictionReport(result, result.prediction_id || Date.now());
    }
    const entry = saveReport({
      predictionId: result.prediction_id || null,
      risk: result.failure_risk,
      probability: result.probability,
      inputData: result.input_data || {},
      shapFactors: result.contributing_factors || [],
      cloudinaryUrl,
      userId: session?.userId,
      userName: session?.name,
      userDesignation: session?.designation || (session?.role === 'admin' ? 'System Administrator' : 'Maintenance Specialist'),
    });
    setSavedEntry(entry);
    setShowPrompt(false);
    return entry;
  };

  return (
    <>
      {/* Full-screen Report viewer */}
      {showViewer && (
        <ReportViewer
          result={result}
          onClose={() => setShowViewer(false)}
          onSave={handleDirectSave}
          savedEntry={savedEntry}
        />
      )}

      <div className="glass-panel">
        {/* Header */}
        <div className="panel-header">
          <h2 className="panel-title">
            <ShieldAlert size={18} className="panel-icon" />
            <span>Diagnostic Evaluation</span>
          </h2>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {getSession()?.name && (
              <span className="field-unit" style={{ color: '#38bdf8', borderColor: 'rgba(56,189,248,0.25)', background: 'rgba(56,189,248,0.05)' }}>
                {getSession().name} [{getSession().designation || (getSession().role === 'admin' ? 'System Administrator' : 'Maintenance Specialist')}]
              </span>
            )}
            <span className="field-unit">
              ROOT CAUSE ENGINE {result.model_version ? `// ${result.model_version.toUpperCase()}` : ''}
            </span>

            {/* Saved cloud link */}
            {savedEntry?.cloudinaryUrl && (
              <a href={savedEntry.cloudinaryUrl} target="_blank" rel="noreferrer" className="cloud-link">
                <ExternalLink size={11} /> Cloud Report
              </a>
            )}

            {/* Export button — only if not yet prompted */}
            {!showPrompt && !savedEntry && (
              <button
                type="button"
                className="preset-btn"
                onClick={() => setShowPrompt(true)}
                style={{ padding: '4px 10px', gap: 6, fontSize: '0.72rem' }}
                title="Export / Save this diagnostic report"
              >
                <FileText size={11} /> Report
              </button>
            )}

            {/* Saved badge */}
            {savedEntry && !savedEntry.cloudinaryUrl && (
              <span style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: '0.72rem', color: '#34d399', fontFamily: 'var(--font-mono)' }}>
                <Check size={12} /> Saved
              </span>
            )}
          </div>
        </div>

        {/* Save / View prompt inline */}
        {showPrompt && (
          <ReportPrompt
            result={result}
            onSaved={(entry) => { setSavedEntry(entry); setShowPrompt(false); }}
            onView={() => { setShowViewer(true); setShowPrompt(false); }}
            onClose={() => setShowPrompt(false)}
          />
        )}

        <div className="results-container">
          {/* Risk Banner */}
          <div className={`risk-banner ${isHighRisk ? 'high' : 'low'}`}>
            <div className="risk-info">
              <span className="risk-tag">Classification Verdict</span>
              <div className={`risk-value ${isHighRisk ? 'high' : 'low'}`}>
                {isHighRisk ? (
                  <><AlertOctagon size={28} color="#fb7185" /><span>RISK: HIGH</span></>
                ) : (
                  <><CheckCircle2 size={28} color="#34d399" /><span>RISK: LOW</span></>
                )}
              </div>
              {result.decision_threshold && (
                <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                  Cutoff: {result.decision_threshold} (PR-Tuned)
                </span>
              )}
            </div>
            <div className="prob-meter-card">
              <div className="prob-number" style={{ color: isHighRisk ? '#fb7185' : '#34d399' }}>
                {probPercent}%
              </div>
              <span className="prob-label">Calibrated Probability</span>
            </div>
          </div>

          {/* Action directive */}
          <div className={`action-alert ${isHighRisk ? 'danger' : 'safe'}`}>
            {isHighRisk ? (
              <><AlertOctagon size={18} style={{ flexShrink: 0 }} /><span><strong>Action Required:</strong> Critical wear signature detected. Schedule preventive inspection immediately.</span></>
            ) : (
              <><CheckCircle2 size={18} style={{ flexShrink: 0 }} /><span><strong>Operational Nominal:</strong> Sensor telemetry aligns with baseline healthy tolerances.</span></>
            )}
          </div>

          {/* Root-Cause Prescriptive Action (Plan 1) */}
          {result.suggested_action && (
            <div style={{
              marginTop: 10,
              padding: '12px 14px',
              borderRadius: 8,
              background: isHighRisk ? 'rgba(251, 113, 133, 0.08)' : 'rgba(52, 211, 153, 0.08)',
              border: `1px solid ${isHighRisk ? 'rgba(251, 113, 133, 0.25)' : 'rgba(52, 211, 153, 0.25)'}`,
              display: 'flex',
              flexDirection: 'column',
              gap: 6
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 6 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.74rem', fontWeight: 600, color: isHighRisk ? '#fb7185' : '#34d399', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  <ShieldAlert size={14} />
                  <span>Root Cause Prescriptive Action</span>
                </div>
                {result.top_risk_factor && (
                  <span style={{
                    fontSize: '0.68rem',
                    fontFamily: 'var(--font-mono)',
                    padding: '2px 8px',
                    borderRadius: 4,
                    background: 'rgba(255,255,255,0.06)',
                    border: '1px solid var(--border-subtle)',
                    color: '#ffffff'
                  }}>
                    Primary Driver: <strong style={{ color: isHighRisk ? '#fb7185' : '#38bdf8', textTransform: 'capitalize' }}>{result.top_risk_factor.replace('_', ' ')}</strong>
                    {result.contribution_pct != null && ` (${result.contribution_pct}% attribution)`}
                  </span>
                )}
              </div>
              <div style={{ fontSize: '0.82rem', lineHeight: 1.5, color: '#f4f4f5' }}>
                <strong style={{ color: '#ffffff' }}>Recommended Step:</strong> {result.suggested_action}
              </div>
            </div>
          )}

          {/* Counterfactual "What Would Fix This" Remediation (Plan 2) */}
          {isHighRisk && (
            <div style={{
              marginTop: 10,
              padding: '12px 14px',
              borderRadius: 8,
              background: 'rgba(56, 189, 248, 0.05)',
              border: '1px solid rgba(56, 189, 248, 0.22)',
              display: 'flex',
              flexDirection: 'column',
              gap: 8
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 6 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.74rem', fontWeight: 600, color: '#38bdf8', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  <Wrench size={14} />
                  <span>Counterfactual Remediation (What Would Fix This?)</span>
                </div>
                {!cfLoading && (
                  <button
                    type="button"
                    onClick={handleFetchCounterfactual}
                    className="preset-btn highlight"
                    style={{ padding: '2px 8px', fontSize: '0.68rem', gap: 4 }}
                    title="Re-run counterfactual parameter search"
                  >
                    <Sparkles size={11} /> Recalculate
                  </button>
                )}
              </div>

              {cfLoading && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.74rem', color: 'var(--text-dim)', padding: '4px 0' }}>
                  <Loader2 size={13} className="batch-spin" />
                  <span>Searching parameter space for smallest risk-reversing adjustment...</span>
                </div>
              )}

              {cfError && !cfLoading && (
                <div style={{ fontSize: '0.74rem', color: '#fb7185', fontFamily: 'var(--font-mono)' }}>
                  {cfError}
                </div>
              )}

              {cfData && !cfLoading && (
                <div style={{ fontSize: '0.8rem', color: '#f4f4f5', lineHeight: 1.5 }}>
                  {cfData.already_safe ? (
                    <span style={{ color: '#34d399' }}>Equipment is already operating below the risk threshold.</span>
                  ) : cfData.target_value != null ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                      <div>
                        Throttling <strong style={{ color: '#38bdf8', textTransform: 'capitalize' }}>{cfData.feature_to_change?.replace('_', ' ')}</strong> to{' '}
                        <strong style={{ color: '#34d399' }}>{cfData.target_value}</strong> (from {cfData.current_value},{' '}
                        <strong style={{ color: '#fb7185' }}>-{cfData.reduction_needed_pct}%</strong>) will reverse failure risk:
                      </div>
                      <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 8,
                        fontSize: '0.76rem',
                        fontFamily: 'var(--font-mono)',
                        background: 'rgba(0,0,0,0.3)',
                        padding: '6px 10px',
                        borderRadius: 6,
                        border: '1px solid rgba(255,255,255,0.06)',
                        flexWrap: 'wrap'
                      }}>
                        <span style={{ color: '#fb7185' }}>Risk Before: {cfData.risk_before}%</span>
                        <ArrowRight size={13} style={{ color: '#94a3b8' }} />
                        <span style={{ color: '#34d399', fontWeight: 700 }}>Risk After: {cfData.risk_after}% [NOMINAL]</span>
                      </div>
                    </div>
                  ) : (
                    <span style={{ color: 'var(--text-dim)' }}>
                      {cfData.note || 'No single-parameter adjustment within tested range brings risk below threshold — recommend full inspection.'}
                    </span>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Root cause factors */}
          <div className="factors-section">
            <div className="factors-title">
              <span>Feature Attribution (Root Cause Impact)</span>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)', fontWeight: 400 }}>Ranked by Impact Magnitude</span>
            </div>
            {factors.slice(0, 5).map((factor, index) => {
              const isPositive = factor.impact >= 0;
              const barWidth   = Math.max(8, Math.min(100, Math.round(((factor.importance || Math.abs(factor.impact)) / (maxImp || 1)) * 100)));
              return (
                <div key={factor.factor} className="factor-item">
                  <div className="factor-top-row">
                    <div className="factor-name-wrapper">
                      <span className="factor-rank">{String(index + 1).padStart(2, '0')}</span>
                      <span className="factor-name">{factor.factor}</span>
                    </div>
                    <div className={`factor-impact ${isPositive ? 'positive' : 'negative'}`}>
                      {isPositive ? <TrendingUp size={12} style={{ display: 'inline', marginRight: 3 }} /> : <TrendingDown size={12} style={{ display: 'inline', marginRight: 3 }} />}
                      <span>{isPositive ? `+${factor.impact.toFixed(3)}` : factor.impact.toFixed(3)}</span>
                    </div>
                  </div>
                  <div className="factor-bar-bg">
                    <div className="factor-bar-fill" style={{ width: `${barWidth}%`, backgroundColor: isPositive ? '#fb7185' : '#34d399' }} />
                  </div>
                  <p className="factor-desc">{factor.description}</p>
                </div>
              );
            })}
          </div>

          {/* Footer */}
          {result.prediction_id && (
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.68rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', borderTop: '1px solid var(--border-subtle)', paddingTop: '10px' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Hash size={11} />{result.prediction_id.slice(0, 13)}...
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Clock size={11} />{result.timestamp ? new Date(result.timestamp).toLocaleTimeString() : 'now'}
              </span>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
