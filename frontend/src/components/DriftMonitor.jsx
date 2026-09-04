import React, { useState } from 'react';
import {
  GitBranch,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  Activity,
  Layers,
  Cpu,
  ArrowRight,
  RotateCcw,
  Sparkles
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
    setActionMsg("Automated pipeline started: training XGBoost, evaluating metrics, and logging to MLflow...");
    try {
      await triggerRetrain();
      setActionMsg(`Retraining initiated in background! Version will advance to next iteration.`);
      setTimeout(() => {
        if (onRefresh) onRefresh();
        setRetraining(false);
      }, 3500);
    } catch (err) {
      console.error("Retraining error:", err);
      setActionMsg("Failed to trigger retraining pipeline.");
      setRetraining(false);
    }
  };

  const handleReset = async () => {
    setResetting(true);
    try {
      await resetDriftStatus();
      setActionMsg("Production telemetry buffer reset.");
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
    <div className="glass-panel" style={{ marginTop: '24px' }}>
      <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
        <h2 className="panel-title">
          <Layers size={20} className="panel-icon" />
          MLOps Drift & Lifecycle Engine
        </h2>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <span className="field-unit" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <GitBranch size={13} />
            MLflow Registry: <strong>PMS-XGBoost</strong> ({modelInfo?.version || 'v2'})
          </span>
        </div>
      </div>

      {/* Overview Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
        gap: '14px',
        margin: '18px 0'
      }}>
        {/* Model Version Card */}
        <div style={{
          padding: '14px 16px',
          background: 'rgba(15, 23, 42, 0.6)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: '12px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
            <span style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Active Model</span>
            <Cpu size={16} color="#06b6d4" />
          </div>
          <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#f8fafc', display: 'flex', alignItems: 'baseline', gap: '6px' }}>
            {modelInfo?.version || 'v2'}
            <span style={{ fontSize: '0.78rem', color: '#38bdf8', fontWeight: 500 }}>Production</span>
          </div>
          <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '4px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            MLflow Run: {modelInfo?.mlflow_run_id ? modelInfo.mlflow_run_id.slice(0, 8) + '...' : 'local'}
          </div>
        </div>

        {/* Telemetry Buffer Card */}
        <div style={{
          padding: '14px 16px',
          background: 'rgba(15, 23, 42, 0.6)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: '12px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
            <span style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Telemetry Window</span>
            <Activity size={16} color="#6366f1" />
          </div>
          <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#f8fafc' }}>
            {total} <span style={{ fontSize: '0.85rem', color: '#94a3b8', fontWeight: 400 }}>inferences</span>
          </div>
          <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '4px' }}>
            {isWarmup ? `Min 10 samples needed (eval active)` : 'Full statistical window active'}
          </div>
        </div>

        {/* Drift Status Card */}
        <div style={{
          padding: '14px 16px',
          background: isWarmup
            ? 'rgba(15, 23, 42, 0.6)'
            : isDrift
              ? 'rgba(244, 63, 94, 0.15)'
              : 'rgba(16, 185, 129, 0.12)',
          border: isWarmup
            ? '1px solid rgba(255, 255, 255, 0.08)'
            : isDrift
              ? '1px solid rgba(244, 63, 94, 0.4)'
              : '1px solid rgba(16, 185, 129, 0.3)',
          borderRadius: '12px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
            <span style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>PSI Drift Status</span>
            {isDrift ? <AlertTriangle size={16} color="#f43f5e" /> : <CheckCircle2 size={16} color="#10b981" />}
          </div>
          <div style={{
            fontSize: '1.2rem',
            fontWeight: 700,
            color: isWarmup ? '#e2e8f0' : isDrift ? '#fb7185' : '#34d399'
          }}>
            {isWarmup ? 'BUFFERING' : isDrift ? 'DRIFT DETECTED' : 'NOMINAL'}
          </div>
          <div style={{ fontSize: '0.72rem', color: '#94a3b8', marginTop: '4px' }}>
            Max PSI: <strong>{maxPsi.toFixed(3)}</strong> (Threshold: 0.250)
          </div>
        </div>
      </div>

      {/* Decision Workflow Diagram */}
      <div style={{
        margin: '16px 0',
        padding: '14px 18px',
        background: 'rgba(2, 6, 23, 0.5)',
        border: '1px solid rgba(255, 255, 255, 0.06)',
        borderRadius: '12px'
      }}>
        <div style={{ fontSize: '0.76rem', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '10px' }}>
          MLOps Decision Path
        </div>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          flexWrap: 'wrap',
          fontSize: '0.82rem',
          color: '#cbd5e1'
        }}>
          <span style={{ background: 'rgba(30, 41, 59, 0.8)', padding: '4px 10px', borderRadius: '6px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
            📡 Telemetry Ingest
          </span>
          <ArrowRight size={14} color="#64748b" />
          <span style={{ background: 'rgba(30, 41, 59, 0.8)', padding: '4px 10px', borderRadius: '6px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
            📊 PSI Drift Analysis
          </span>
          <ArrowRight size={14} color="#64748b" />
          <span style={{
            background: isDrift ? 'rgba(244, 63, 94, 0.2)' : 'rgba(16, 185, 129, 0.15)',
            padding: '4px 10px',
            borderRadius: '6px',
            border: isDrift ? '1px solid rgba(244, 63, 94, 0.4)' : '1px solid rgba(16, 185, 129, 0.3)',
            color: isDrift ? '#fda4af' : '#6ee7b7',
            fontWeight: 600
          }}>
            {isDrift ? '⚠️ Drift (PSI ≥ 0.25) → Retrain Triggered' : '✅ Stable (PSI < 0.25) → Continue Inference'}
          </span>
        </div>
      </div>

      {/* Feature-level PSI breakdown */}
      {Object.keys(features).length > 0 && (
        <div style={{ marginTop: '16px' }}>
          <div style={{ fontSize: '0.78rem', color: '#94a3b8', marginBottom: '10px', fontWeight: 600 }}>
            Feature-Level Population Stability Index (PSI):
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '10px' }}>
            {Object.entries(features).map(([feat, m]) => {
              const psiVal = m.psi ?? 0;
              const isWarning = psiVal >= 0.10 && psiVal < 0.25;
              const isDanger = psiVal >= 0.25;
              const barColor = isDanger ? '#f43f5e' : isWarning ? '#f59e0b' : '#10b981';
              const statusText = isDanger ? 'DRIFT' : isWarning ? 'SHIFT' : 'STABLE';

              return (
                <div key={feat} style={{
                  background: 'rgba(15, 23, 42, 0.4)',
                  padding: '10px 12px',
                  borderRadius: '8px',
                  border: '1px solid rgba(255, 255, 255, 0.05)'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', marginBottom: '4px' }}>
                    <span style={{ color: '#cbd5e1', textTransform: 'capitalize' }}>{feat.replace('_', ' ')}</span>
                    <span style={{ color: barColor, fontWeight: 600, fontSize: '0.72rem' }}>{statusText} ({psiVal.toFixed(3)})</span>
                  </div>
                  <div style={{ width: '100%', height: '4px', background: 'rgba(255, 255, 255, 0.1)', borderRadius: '2px', overflow: 'hidden' }}>
                    <div style={{
                      height: '100%',
                      width: `${Math.min(100, Math.round((psiVal / 0.3) * 100))}%`,
                      background: barColor,
                      transition: 'width 0.4s ease'
                    }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Action Notice */}
      {actionMsg && (
        <div style={{
          marginTop: '16px',
          padding: '10px 14px',
          background: 'rgba(6, 182, 212, 0.12)',
          border: '1px solid rgba(6, 182, 212, 0.3)',
          borderRadius: '8px',
          color: '#a5f3fc',
          fontSize: '0.82rem'
        }}>
          {actionMsg}
        </div>
      )}

      {/* Action Buttons */}
      <div style={{ display: 'flex', gap: '10px', marginTop: '18px', flexWrap: 'wrap' }}>
        <button
          className="btn-primary"
          onClick={handleRetrain}
          disabled={retraining}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '10px 18px',
            fontSize: '0.85rem'
          }}
        >
          {retraining ? <RefreshCw size={15} className="spin" /> : <Sparkles size={15} />}
          {retraining ? 'Retraining Model...' : 'Trigger Automated Retraining'}
        </button>

        <button
          className="btn-outline"
          onClick={handleReset}
          disabled={resetting}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '10px 16px',
            fontSize: '0.85rem'
          }}
        >
          <RotateCcw size={14} />
          Reset Telemetry Buffer
        </button>
      </div>
    </div>
  );
}
