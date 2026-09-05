import React from 'react';
import { Terminal, Cpu, Radio } from 'lucide-react';

export default function Header({ health, modelInfo }) {
  const isHealthy = health?.status === 'healthy';

  return (
    <header className="app-header">
      <div className="brand-wrapper">
        <div className="brand-icon" title="Predictive Maintenance System">
          <Terminal size={20} />
        </div>
        <div className="brand-title-group">
          <h1 className="brand-title">
            <span>pms://telemetry</span>
            <span style={{ color: 'var(--text-dim)', fontWeight: 400 }}>//</span>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
              inference-core
            </span>
          </h1>
          <p className="brand-tagline">
            Calibrated XGBoost • SHAP Waterfall Diagnostics • Drift Radar
          </p>
        </div>
      </div>

      <div className="header-status">
        {modelInfo?.metrics?.roc_auc && (
          <div className="model-badge">
            <Cpu size={13} />
            <span>XGBoost [{modelInfo.version || 'v12'}]</span>
            <span style={{ color: 'var(--text-dim)' }}>•</span>
            <span>AUC {(modelInfo.metrics.roc_auc * 100).toFixed(1)}%</span>
          </div>
        )}
        <div 
          className="status-chip" 
          title={isHealthy ? "Backend connected and ready" : "Connecting to Render service..."}
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
      </div>
    </header>
  );
}

