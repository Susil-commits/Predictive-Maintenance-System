import React from 'react';
import { AlertOctagon, CheckCircle2, TrendingUp, TrendingDown, HelpCircle, ShieldAlert } from 'lucide-react';

export default function PredictionResult({ result }) {
  if (!result) {
    return (
      <div className="glass-panel">
        <div className="panel-header">
          <h2 className="panel-title">
            <ShieldAlert size={20} className="panel-icon" />
            Diagnostics & SHAP Explanation
          </h2>
        </div>
        <div className="empty-state">
          <HelpCircle size={44} style={{ color: '#475569', marginBottom: 14 }} />
          <p>Configure equipment telemetry and click <strong>[ PREDICT ]</strong> to evaluate real-time failure probability and SHAP attribution.</p>
        </div>
      </div>
    );
  }

  const isHighRisk = result.failure_risk === 'HIGH';
  const probPercent = Math.round(result.probability * 100);
  const factors = result.contributing_factors || [];

  // Find max importance to calculate proportional bar width
  const maxImportance = factors.length > 0 ? Math.max(...factors.map(f => f.importance || Math.abs(f.impact))) : 1;

  return (
    <div className="glass-panel">
      <div className="panel-header">
        <h2 className="panel-title">
          <ShieldAlert size={20} className="panel-icon" />
          Health Evaluation & Explanation
        </h2>
        <span className="field-unit">SHAP TREE-EXPLAINER</span>
      </div>

      <div className="results-container">
        {/* Risk Banner */}
        <div className={`risk-banner ${isHighRisk ? 'high' : 'low'}`}>
          <div className="risk-info">
            <span className="risk-tag">Equipment Status</span>
            <div className={`risk-value ${isHighRisk ? 'high' : 'low'}`}>
              {isHighRisk ? (
                <>
                  <AlertOctagon size={36} color="#fb7185" />
                  Risk: HIGH
                </>
              ) : (
                <>
                  <CheckCircle2 size={36} color="#34d399" />
                  Risk: LOW
                </>
              )}
            </div>
          </div>

          <div className="prob-meter-card">
            <div className="prob-number" style={{ color: isHighRisk ? '#fb7185' : '#34d399' }}>
              {probPercent}%
            </div>
            <span className="prob-label">Failure Probability</span>
          </div>
        </div>

        {/* Maintenance Action Directive */}
        <div className={`action-alert ${isHighRisk ? 'danger' : 'safe'}`}>
          {isHighRisk ? (
            <>
              <AlertOctagon size={20} />
              <span><strong>Action Required:</strong> Immediate mechanical inspection and preventive maintenance recommended.</span>
            </>
          ) : (
            <>
              <CheckCircle2 size={20} />
              <span><strong>Operational Nominal:</strong> Telemetry operating within safe operational parameters.</span>
            </>
          )}
        </div>

        {/* Contributing Factors (SHAP) */}
        <div className="factors-section">
          <div className="factors-title">
            <span>Main Contributing Factors</span>
            <span style={{ fontSize: '0.74rem', color: '#64748b' }}>Ranked by Impact</span>
          </div>

          {factors.slice(0, 4).map((factor, index) => {
            const isPositive = factor.impact >= 0;
            const barWidth = Math.max(12, Math.min(100, Math.round(((factor.importance || Math.abs(factor.impact)) / (maxImportance || 1)) * 100)));

            return (
              <div key={factor.factor} className="factor-item">
                <div className="factor-top-row">
                  <div className="factor-name-wrapper">
                    <span className="factor-rank">{index + 1}</span>
                    <span className="factor-name">{factor.factor}</span>
                  </div>
                  <div className={`factor-impact ${isPositive ? 'positive' : 'negative'}`}>
                    {isPositive ? <TrendingUp size={14} style={{ display: 'inline', marginRight: 4 }} /> : <TrendingDown size={14} style={{ display: 'inline', marginRight: 4 }} />}
                    {isPositive ? `+${factor.impact.toFixed(3)}` : factor.impact.toFixed(3)}
                  </div>
                </div>

                <div className="factor-bar-bg">
                  <div
                    className="factor-bar-fill"
                    style={{
                      width: `${barWidth}%`,
                      background: isPositive
                        ? 'linear-gradient(90deg, #f43f5e, #fb7185)'
                        : 'linear-gradient(90deg, #0284c7, #38bdf8)'
                    }}
                  ></div>
                </div>

                <p className="factor-desc">{factor.description}</p>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
