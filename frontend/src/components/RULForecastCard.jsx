import React from 'react';
import { Clock, Activity, AlertTriangle, CheckCircle, RefreshCw, Gauge, ShieldCheck, Wrench } from 'lucide-react';

export default function RULForecastCard({ rulData, loading, onRefresh }) {
  if (!rulData && !loading) {
    return (
      <div className="glass-panel" style={{ marginTop: 16 }}>
        <div className="panel-header">
          <h2 className="panel-title">
            <Clock size={18} className="panel-icon" />
            <span>RUL Degradation Forecast</span>
          </h2>
        </div>
        <div className="empty-state" style={{ padding: '24px 16px' }}>
          <span>Run telemetry inference to calculate equipment remaining useful life (RUL).</span>
        </div>
      </div>
    );
  }

  const cycles = rulData?.estimated_rul_cycles ?? 0;
  const hours = rulData?.estimated_rul_hours ?? (cycles * 0.5);
  const confidence = rulData?.confidence ? Math.round(rulData.confidence * 100) : 85;
  const isUrgent = cycles < 50;
  const recommendation = isUrgent
    ? "Schedule maintenance within 2 weeks"
    : "Continue monitoring — equipment within nominal wear margins";

  // Cycle progress percentage relative to 150-cycle maximum lifetime
  const lifePct = Math.min(100, Math.max(0, Math.round((cycles / 150) * 100)));

  return (
    <div className="glass-panel rul-forecast-panel" style={{ marginTop: 16 }}>
      <div className="panel-header" style={{ justifyContent: 'space-between' }}>
        <h2 className="panel-title">
          <Clock size={18} className="panel-icon" style={{ color: isUrgent ? '#fb7185' : '#38bdf8' }} />
          <span>RUL Forecast</span>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontWeight: 400, fontFamily: 'var(--font-mono)' }}>
            [Time-Series Regression]
          </span>
        </h2>
        {onRefresh && (
          <button
            type="button"
            className="preset-btn"
            onClick={onRefresh}
            disabled={loading}
            style={{ padding: '3px 9px', fontSize: '0.72rem', gap: 5 }}
            title="Refresh RUL degradation calculation"
          >
            <RefreshCw size={11} className={loading ? 'batch-spin' : ''} />
            <span>Recalculate</span>
          </button>
        )}
      </div>

      <div style={{ padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* Main RUL Display */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: 16,
            background: 'rgba(255, 255, 255, 0.02)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 8,
            padding: '16px 20px',
          }}
        >
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>
              Estimated Remaining Useful Life
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
              <span style={{ fontSize: '2rem', fontWeight: 800, fontFamily: 'var(--font-mono)', color: isUrgent ? '#fb7185' : '#38bdf8' }}>
                {cycles}
              </span>
              <span style={{ fontSize: '1rem', color: '#ffffff', fontWeight: 600 }}>cycles</span>
              <span style={{ fontSize: '1rem', color: 'var(--text-dim)' }}>·</span>
              <span style={{ fontSize: '1.1rem', color: '#e2e8f0', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                ({hours.toFixed(1)} hours)
              </span>
            </div>
          </div>

          <div style={{ textAlign: 'right', display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Confidence Metric</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <div
                style={{
                  width: 60,
                  height: 6,
                  background: 'rgba(255,255,255,0.1)',
                  borderRadius: 3,
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    width: `${confidence}%`,
                    height: '100%',
                    background: confidence > 75 ? '#34d399' : '#f59e0b',
                    borderRadius: 3,
                  }}
                />
              </div>
              <span style={{ fontSize: '0.85rem', fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#ffffff' }}>
                {confidence}%
              </span>
            </div>
          </div>
        </div>

        {/* Action Recommendation Banner */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            padding: '12px 16px',
            borderRadius: 8,
            background: isUrgent ? 'rgba(244, 63, 94, 0.08)' : 'rgba(16, 185, 129, 0.08)',
            border: `1px solid ${isUrgent ? 'rgba(244, 63, 94, 0.3)' : 'rgba(16, 185, 129, 0.25)'}`,
          }}
        >
          {isUrgent ? (
            <Wrench size={20} style={{ color: '#fb7185', flexShrink: 0 }} />
          ) : (
            <ShieldCheck size={20} style={{ color: '#34d399', flexShrink: 0 }} />
          )}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <span style={{ fontSize: '0.72rem', textTransform: 'uppercase', fontWeight: 700, color: isUrgent ? '#fda4af' : '#6ee7b7' }}>
              Recommended Action
            </span>
            <span style={{ fontSize: '0.9rem', color: '#ffffff', fontWeight: 600 }}>
              {recommendation}
            </span>
          </div>
        </div>

        {/* Degradation Horizon Meter */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: 6, fontFamily: 'var(--font-mono)' }}>
            <span>0 cycles (Critical Failure)</span>
            <span>Degradation Reserve ({lifePct}%)</span>
            <span>150 cycles (Factory New)</span>
          </div>
          <div style={{ width: '100%', height: 8, background: 'rgba(255,255,255,0.06)', borderRadius: 4, overflow: 'hidden' }}>
            <div
              style={{
                width: `${lifePct}%`,
                height: '100%',
                background: isUrgent
                  ? 'linear-gradient(90deg, #f43f5e 0%, #fb923c 100%)'
                  : 'linear-gradient(90deg, #38bdf8 0%, #34d399 100%)',
                borderRadius: 4,
                transition: 'width 0.4s ease',
              }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
