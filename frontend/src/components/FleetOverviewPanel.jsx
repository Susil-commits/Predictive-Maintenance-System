import React from 'react';
import { Server, AlertTriangle, CheckCircle2, RefreshCw, Play, Loader2 } from 'lucide-react';

export default function FleetOverviewPanel({
  fleet,
  selectedAsset,
  onSelectAsset,
  onRefresh,
  onSimulateStream,
  simulating = false,
}) {
  const assets = fleet?.assets || [];

  return (
    <div className="glass-panel" style={{ marginBottom: 16 }}>
      <div className="panel-header">
        <h2 className="panel-title">
          <Server size={18} className="panel-icon" />
          <span>Multi-Asset Fleet Matrix</span>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontWeight: 400, fontFamily: 'var(--font-mono)' }}>
            [{fleet?.total_assets ?? assets.length} assets · {fleet?.critical_assets ?? 0} critical]
          </span>
        </h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          {selectedAsset && (
            <button
              type="button"
              className="preset-btn highlight"
              onClick={() => onSelectAsset(null)}
              style={{ padding: '3px 9px', fontSize: '0.7rem' }}
            >
              Show All Assets
            </button>
          )}
          {onSimulateStream && (
            <button
              type="button"
              className="preset-btn highlight"
              onClick={onSimulateStream}
              disabled={simulating}
              style={{ padding: '3px 9px', fontSize: '0.7rem', gap: 5 }}
              title="Replay physical degradation curves across multiple assets over WS /ws/telemetry"
            >
              {simulating ? <Loader2 size={11} className="batch-spin" /> : <Play size={11} />}
              <span>{simulating ? 'Streaming...' : 'Simulate Live Fleet'}</span>
            </button>
          )}
          {onRefresh && (
            <button
              type="button"
              className="preset-btn"
              onClick={onRefresh}
              style={{ padding: '3px 9px', fontSize: '0.7rem', gap: 5 }}
              title="Refresh fleet telemetry summary"
            >
              <RefreshCw size={11} />
              <span>Sync Fleet</span>
            </button>
          )}
        </div>
      </div>

      {assets.length === 0 ? (
        <div className="empty-state" style={{ padding: '16px 12px' }}>
          No tracked assets yet. Enable the Context Engineering Envelope or run telemetry inference to populate the fleet matrix.
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(230px, 1fr))', gap: 10 }}>
          {assets.map((asset) => {
            const isHigh = asset.latest_failure_risk === 'HIGH';
            const isSelected = selectedAsset === asset.asset_id;
            return (
              <button
                key={asset.asset_id}
                type="button"
                onClick={() => onSelectAsset(isSelected ? null : asset.asset_id)}
                style={{
                  textAlign: 'left',
                  padding: '10px 12px',
                  borderRadius: 8,
                  cursor: 'pointer',
                  background: isSelected
                    ? 'rgba(56, 189, 248, 0.1)'
                    : isHigh
                      ? 'rgba(244, 63, 94, 0.05)'
                      : 'rgba(255, 255, 255, 0.02)',
                  border: `1px solid ${
                    isSelected
                      ? '#38bdf8'
                      : isHigh
                        ? 'rgba(244, 63, 94, 0.3)'
                        : 'var(--border-subtle)'
                  }`,
                  color: '#f4f4f5',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 6,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 6 }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '0.78rem', color: '#ffffff', display: 'flex', alignItems: 'center', gap: 5 }}>
                    {isHigh ? <AlertTriangle size={13} color="#fb7185" /> : <CheckCircle2 size={13} color="#34d399" />}
                    {asset.asset_id}
                  </span>
                  <span className={`badge-risk ${isHigh ? 'high' : 'low'}`} style={{ fontSize: '0.62rem' }}>
                    {asset.latest_failure_risk}
                  </span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'var(--font-mono)', fontSize: '0.71rem', color: 'var(--text-dim)' }}>
                  <span>P: <strong style={{ color: isHigh ? '#fb7185' : '#34d399' }}>{(asset.latest_probability * 100).toFixed(1)}%</strong></span>
                  <span>T: {asset.latest_temperature}°C · V: {asset.latest_vibration}g</span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                  <span>{asset.latest_regime}</span>
                  <span>{asset.total_evaluations} runs ({asset.high_risk_count} high)</span>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
