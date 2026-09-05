import React, { useState } from 'react';
import {
  GitBranch,
  AlertTriangle,
  CheckCircle2,
  Activity,
  Layers,
  Cpu,
  ArrowRight,
  RotateCcw,
  Zap
} from 'lucide-react';
import { triggerRetrain, resetDriftStatus } from '../api';

export default function DriftMonitor({
  driftStatus,
  modelInfo,
  onRefresh
}) {
  const [retraining, setRetraining] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [actionMsg, setActionMsg] = useState(null);

  const handleRetrain = async () => {
    setRetraining(true);
    setActionMsg("executing pipeline: recalibrating decision thresholds, updating baseline distributions...");
    try {
      await triggerRetrain();
      setActionMsg("recalibration complete: updated predictive core deployed.");
      setTimeout(() => {
        if (onRefresh) onRefresh();
        setRetraining(false);
      }, 3500);
    } catch (err) {
      console.error("Retraining error:", err);
      setActionMsg("err: automated retraining pipeline returned non-zero exit.");
      setRetraining(false);
    }
  };

  const handleReset = async () => {
    setResetting(true);
    try {
      await resetDriftStatus();
      setActionMsg("telemetry buffer purged: PSI baseline re-initialized.");
      if (onRefresh) onRefresh();
    } catch (err) {
      console.error("Reset error:", err);
    } finally {
      setResetting(false);
      setTimeout(() => setActionMsg(null), 3000);
    }
  };

  const total = driftStatus?.total_predictions || 0;
  const isDrift = driftStatus?.drift_detected;
  const isWarmup = total < 10;
  const maxPsi = driftStatus?.max_psi ?? 0;
  const features = driftStatus?.features || {};

  return (
    <div className="glass-panel" style={{ marginTop: '20px' }}>
      <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
        <h2 className="panel-title">
          <Layers size={18} className="panel-icon" />
          <span>System Stability & Drift Monitor</span>
        </h2>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <span className="field-unit" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <GitBranch size={12} />
            <span>System Registry:</span>
            <strong style={{ color: '#ffffff' }}>PMS Core [{modelInfo?.version || 'v12'}]</strong>
          </span>
        </div>
      </div>

      {/* Metric Cards Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
        gap: '12px',
        margin: '16px 0'
      }}>
        {/* Model Version Card */}
        <div style={{
          padding: '14px 16px',
          background: 'var(--bg-card-subtle)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-md)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.04em', fontFamily: 'var(--font-mono)' }}>Active Engine</span>
            <Cpu size={14} color="#a1a1aa" />
          </div>
          <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#ffffff', display: 'flex', alignItems: 'baseline', gap: '6px', fontFamily: 'var(--font-mono)' }}>
            {modelInfo?.version || 'v12'}
            <span style={{ fontSize: '0.74rem', color: '#10b981', fontWeight: 600 }}>[PROD]</span>
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', marginTop: '4px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontFamily: 'var(--font-mono)' }}>
            Build: {modelInfo?.mlflow_run_id ? modelInfo.mlflow_run_id.slice(0, 10) : 'production'}
          </div>
        </div>

        {/* Telemetry Buffer Card */}
        <div style={{
          padding: '14px 16px',
          background: 'var(--bg-card-subtle)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-md)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.04em', fontFamily: 'var(--font-mono)' }}>Telemetry Window</span>
            <Activity size={14} color="#a1a1aa" />
          </div>
          <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#ffffff', fontFamily: 'var(--font-mono)' }}>
            {total} <span style={{ fontSize: '0.78rem', color: 'var(--text-dim)', fontWeight: 400 }}>inferences</span>
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', marginTop: '4px', fontFamily: 'var(--font-mono)' }}>
            {isWarmup ? 'Buffer: collecting sample window' : 'Window: full statistical analysis active'}
          </div>
        </div>

        {/* Drift Status Card */}
        <div style={{
          padding: '14px 16px',
          background: isWarmup
            ? 'var(--bg-card-subtle)'
            : isDrift
              ? 'rgba(244, 63, 94, 0.1)'
              : 'rgba(16, 185, 129, 0.08)',
          border: isWarmup
            ? '1px solid var(--border-subtle)'
            : isDrift
              ? '1px solid rgba(244, 63, 94, 0.35)'
              : '1px solid rgba(16, 185, 129, 0.3)',
          borderRadius: 'var(--radius-md)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.04em', fontFamily: 'var(--font-mono)' }}>PSI Drift State</span>
            {isDrift ? <AlertTriangle size={14} color="#f43f5e" /> : <CheckCircle2 size={14} color="#10b981" />}
          </div>
          <div style={{
            fontSize: '1.25rem',
            fontWeight: 800,
            fontFamily: 'var(--font-mono)',
            color: isWarmup ? '#ffffff' : isDrift ? '#fb7185' : '#34d399'
          }}>
            {isWarmup ? 'WARMING UP' : isDrift ? 'DRIFT DETECTED' : 'NOMINAL STABLE'}
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', marginTop: '4px', fontFamily: 'var(--font-mono)' }}>
            Max PSI: <strong style={{ color: '#ffffff' }}>{maxPsi.toFixed(3)}</strong> (Cutoff: 0.250)
          </div>
        </div>
      </div>

      {/* Decision Path */}
      <div style={{
        margin: '14px 0',
        padding: '12px 16px',
        background: '#050507',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-sm)'
      }}>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px', fontFamily: 'var(--font-mono)' }}>
          System Calibration Topology
        </div>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          flexWrap: 'wrap',
          fontSize: '0.78rem',
          fontFamily: 'var(--font-mono)',
          color: '#e4e4e7'
        }}>
          <span style={{ background: '#121215', padding: '3px 8px', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
            01. Telemetry Ingest
          </span>
          <ArrowRight size={12} color="#52525b" />
          <span style={{ background: '#121215', padding: '3px 8px', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
            02. PSI Vector Diff
          </span>
          <ArrowRight size={12} color="#52525b" />
          <span style={{
            background: isDrift ? 'rgba(244, 63, 94, 0.15)' : 'rgba(16, 185, 129, 0.1)',
            padding: '3px 8px',
            borderRadius: '4px',
            border: isDrift ? '1px solid rgba(244, 63, 94, 0.3)' : '1px solid rgba(16, 185, 129, 0.25)',
            color: isDrift ? '#fda4af' : '#a7f3d0'
          }}>
            {isDrift ? '03. PSI >= 0.25 → Retrain Alert' : '03. PSI < 0.25 → Steady State'}
          </span>
        </div>
      </div>

      {/* Feature-Level PSI Breakdown */}
      {Object.keys(features).length > 0 && (
        <div style={{ marginTop: '16px' }}>
          <div style={{ fontSize: '0.76rem', color: 'var(--text-dim)', marginBottom: '8px', fontWeight: 600, fontFamily: 'var(--font-mono)', textTransform: 'uppercase' }}>
            Feature Stability Indices (PSI):
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '8px' }}>
            {Object.entries(features).map(([feat, m]) => {
              const psiVal = m.psi ?? 0;
              const isWarning = psiVal >= 0.10 && psiVal < 0.25;
              const isDanger = psiVal >= 0.25;
              const barColor = isDanger ? '#f43f5e' : isWarning ? '#f59e0b' : '#ffffff';
              const statusText = isDanger ? 'DRIFT' : isWarning ? 'SHIFT' : 'STABLE';

              return (
                <div key={feat} style={{
                  background: '#09090b',
                  padding: '8px 12px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-subtle)'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.74rem', marginBottom: '4px', fontFamily: 'var(--font-mono)' }}>
                    <span style={{ color: '#ffffff' }}>{feat.replace('_', ' ')}</span>
                    <span style={{ color: barColor, fontWeight: 700 }}>{statusText} {psiVal.toFixed(3)}</span>
                  </div>
                  <div style={{ width: '100%', height: '3px', background: '#18181b', borderRadius: '2px', overflow: 'hidden' }}>
                    <div style={{
                      height: '100%',
                      width: `${Math.min(100, Math.round((psiVal / 0.3) * 100))}%`,
                      backgroundColor: barColor,
                      transition: 'width 0.3s ease'
                    }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Terminal Feedback Output */}
      {actionMsg && (
        <div className="terminal-console" style={{ marginTop: '14px' }}>
          <div className="terminal-line">
            <span className="terminal-prompt">$</span>
            <span>{actionMsg}</span>
            <span className="terminal-cursor" />
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div style={{ display: 'flex', gap: '8px', marginTop: '16px', flexWrap: 'wrap' }}>
        <button
          type="button"
          className="submit-btn"
          onClick={handleRetrain}
          disabled={retraining}
          style={{ flex: 'none', padding: '10px 18px', fontSize: '0.78rem' }}
        >
          {retraining ? (
            <>
              <span className="spinner" style={{ width: 14, height: 14, borderColor: '#888', borderTopColor: '#000' }} />
              <span>RECALIBRATING ENGINE...</span>
            </>
          ) : (
            <>
              <Zap size={14} fill="#000000" />
              <span>TRIGGER RECALIBRATION</span>
            </>
          )}
        </button>

        <button
          type="button"
          className="preset-btn"
          onClick={handleReset}
          disabled={resetting}
          style={{ padding: '10px 16px', fontSize: '0.78rem' }}
        >
          <RotateCcw size={13} />
          <span>Reset Telemetry Window</span>
        </button>
      </div>
    </div>
  );
}

