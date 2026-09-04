import React from 'react';
import { Activity, Cpu } from 'lucide-react';

export default function Header({ health, modelInfo }) {
  const isHealthy = health?.status === 'healthy';

  return (
    <header className="app-header">
      <div className="brand-wrapper">
        <div className="brand-icon">
          <Activity size={24} />
        </div>
        <div>
          <h1 className="brand-title">Predictive Maintenance System</h1>
          <p className="brand-subtitle">
            Vehicle & Heavy Equipment Telemetry • XGBoost + SHAP Explainability
          </p>
        </div>
      </div>

      <div className="header-status">
        {modelInfo?.metrics?.roc_auc && (
          <div className="model-badge">
            <Cpu size={14} style={{ display: 'inline', marginRight: 6, verticalAlign: 'middle' }} />
            XGBoost {modelInfo.version ? `[${modelInfo.version}]` : ''} • ROC-AUC {(modelInfo.metrics.roc_auc * 100).toFixed(1)}%
          </div>
        )}
        <div className="status-chip" title={isHealthy ? "API and Inference Engine Operational" : "Connecting to API..."}>
          <span className="status-dot" style={{ background: isHealthy ? '#10b981' : '#f59e0b' }}></span>
          <span>{isHealthy ? 'LIVE' : 'CONNECTING'}</span>
        </div>
      </div>
    </header>
  );
}
