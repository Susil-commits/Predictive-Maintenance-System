import React from 'react';
import { 
  AlertOctagon, 
  CheckCircle2, 
  TrendingUp, 
  TrendingDown, 
  Terminal, 
  ShieldAlert,
  Hash,
  Clock
} from 'lucide-react';

export default function PredictionResult({ result }) {
  if (!result) {
    return (
      <div className="glass-panel">
        <div className="panel-header">
          <h2 className="panel-title">
            <ShieldAlert size={18} className="panel-icon" />
            <span>Diagnostics & SHAP Waterfall</span>
          </h2>
          <span className="field-unit">STANDBY</span>
        </div>
        <div className="empty-state">
          <div style={{
            width: 44,
            height: 44,
            borderRadius: '10px',
            background: '#121215',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: 16,
            color: '#71717a'
          }}>
            <Terminal size={22} />
          </div>
          <p style={{ maxWidth: 360, lineHeight: 1.6 }}>
            Telemetry stream idle. Select a preset or configure sensors, then click <strong style={{ color: '#ffffff' }}>EVALUATE TELEMETRY</strong> to run tree-explainer inference.
          </p>
        </div>
      </div>
    );
  }

  const isHighRisk = result.failure_risk === 'HIGH';
  const probPercent = (result.probability * 100).toFixed(1);
  const factors = result.contributing_factors || [];

  // Proportional bar width
  const maxImportance = factors.length > 0 ? Math.max(...factors.map(f => f.importance || Math.abs(f.impact))) : 1;

  return (
    <div className="glass-panel">
      <div className="panel-header">
        <h2 className="panel-title">
          <ShieldAlert size={18} className="panel-icon" />
          <span>Diagnostic Evaluation</span>
        </h2>
        <span className="field-unit">
          TREE-EXPLAINER {result.model_version ? `// ${result.model_version.toUpperCase()}` : ''}
        </span>
      </div>

      <div className="results-container">
        {/* Risk Banner */}
        <div className={`risk-banner ${isHighRisk ? 'high' : 'low'}`}>
          <div className="risk-info">
            <span className="risk-tag">Classification Verdict</span>
            <div className={`risk-value ${isHighRisk ? 'high' : 'low'}`}>
              {isHighRisk ? (
                <>
                  <AlertOctagon size={28} color="#fb7185" />
                  <span>RISK: HIGH</span>
                </>
              ) : (
                <>
                  <CheckCircle2 size={28} color="#34d399" />
                  <span>RISK: LOW</span>
                </>
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

        {/* Maintenance Action Directive */}
        <div className={`action-alert ${isHighRisk ? 'danger' : 'safe'}`}>
          {isHighRisk ? (
            <>
              <AlertOctagon size={18} style={{ flexShrink: 0 }} />
              <span><strong>Action Required:</strong> Critical wear signature detected. Schedule preventive inspection immediately.</span>
            </>
          ) : (
            <>
              <CheckCircle2 size={18} style={{ flexShrink: 0 }} />
              <span><strong>Operational Nominal:</strong> Sensor telemetry aligns with baseline healthy tolerances.</span>
            </>
          )}
        </div>

        {/* Contributing Factors (SHAP) */}
        <div className="factors-section">
          <div className="factors-title">
            <span>Feature Attribution (Tree-SHAP)</span>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)', fontWeight: 400 }}>Ranked by Impact Magnitude</span>
          </div>

          {factors.slice(0, 5).map((factor, index) => {
            const isPositive = factor.impact >= 0;
            const barWidth = Math.max(8, Math.min(100, Math.round(((factor.importance || Math.abs(factor.impact)) / (maxImportance || 1)) * 100)));

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
                  <div
                    className="factor-bar-fill"
                    style={{
                      width: `${barWidth}%`,
                      backgroundColor: isPositive ? '#fb7185' : '#34d399'
                    }}
                  />
                </div>

                <p className="factor-desc">{factor.description}</p>
              </div>
            );
          })}
        </div>

        {/* Monospace Metadata Footer */}
        {result.prediction_id && (
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            fontSize: '0.68rem',
            fontFamily: 'var(--font-mono)',
            color: 'var(--text-dim)',
            borderTop: '1px solid var(--border-subtle)',
            paddingTop: '10px'
          }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Hash size={11} />
              {result.prediction_id.slice(0, 13)}...
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Clock size={11} />
              {result.timestamp ? new Date(result.timestamp).toLocaleTimeString() : 'now'}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

