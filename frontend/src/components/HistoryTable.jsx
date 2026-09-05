import React, { useState } from 'react';
import { Database, Trash2, ArrowUpRight, Download, Check } from 'lucide-react';

export default function HistoryTable({ history, onSelectRow, onClearHistory, onExport }) {
  const [copiedCsv, setCopiedCsv] = useState(false);

  const handleExport = () => {
    if (onExport) {
      onExport();
      setCopiedCsv(true);
      setTimeout(() => setCopiedCsv(false), 2000);
      return;
    }
    // fallback: client-side CSV from current history prop
    if (!history || history.length === 0) return;
    const headers = ['timestamp', 'temperature', 'rpm', 'pressure', 'vibration', 'operating_hours', 'failure_risk', 'probability'];
    const rows = history.map(r => {
      const input = r.input_features || r;
      return [
        r.timestamp || '',
        input.temperature, input.rpm, input.pressure,
        input.vibration, input.operating_hours,
        r.failure_risk, r.probability
      ].join(',');
    });
    const csv = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows].join('\n');
    const a = document.createElement('a');
    a.href = encodeURI(csv);
    a.download = `pms_audit_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    setCopiedCsv(true);
    setTimeout(() => setCopiedCsv(false), 2000);
  };

  if (!history || history.length === 0) {
    return (
      <div className="glass-panel history-panel">
        <div className="panel-header">
          <h2 className="panel-title">
            <Database size={18} className="panel-icon" />
            <span>Database Prediction Audit Log</span>
          </h2>
          <span className="field-unit">0 RECORDS</span>
        </div>
        <div className="empty-state">
          <p>No telemetry records stored in PostgreSQL yet. Run inference above to record predictions.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="glass-panel history-panel">
      <div className="panel-header">
        <h2 className="panel-title">
          <Database size={18} className="panel-icon" />
          <span>Audit Log Database</span>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontWeight: 400, fontFamily: 'var(--font-mono)' }}>
            [{history.length} events]
          </span>
        </h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            type="button"
            onClick={handleExport}
            className="preset-btn"
            title="Download full audit log as CSV"
            style={{ padding: '4px 8px', fontSize: '0.7rem' }}
          >
            {copiedCsv ? <Check size={12} color="#10b981" /> : <Download size={12} />}
            <span>Export CSV</span>
          </button>
          <button
            type="button"
            onClick={onClearHistory}
            className="preset-btn"
            style={{ padding: '4px 8px', fontSize: '0.7rem', color: '#fda4af', borderColor: 'rgba(244, 63, 94, 0.3)' }}
            title="Clear database records"
          >
            <Trash2 size={12} />
            <span>Clear Log</span>
          </button>
        </div>
      </div>

      <div className="table-responsive">
        <table className="history-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Temp (°C)</th>
              <th>RPM</th>
              <th>Pressure</th>
              <th>Vibration</th>
              <th>Hours</th>
              <th>Verdict</th>
              <th>Calibrated P</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {history.map((row) => {
              const dateStr = row.timestamp
                ? new Date(row.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
                : '—';
              const isHigh = row.failure_risk === 'HIGH';
              const input = row.input_features || row;

              return (
                <tr key={row.prediction_id} onClick={() => onSelectRow(input)}>
                  <td style={{ color: 'var(--text-dim)' }}>{dateStr}</td>
                  <td>{input.temperature}</td>
                  <td>{input.rpm}</td>
                  <td>{input.pressure}</td>
                  <td>{input.vibration}</td>
                  <td>{input.operating_hours}</td>
                  <td>
                    <span className={`badge-risk ${isHigh ? 'high' : 'low'}`}>
                      {row.failure_risk}
                    </span>
                  </td>
                  <td>
                    <span style={{ color: isHigh ? '#fb7185' : '#34d399', fontWeight: 700 }}>
                      {(row.probability * 100).toFixed(1)}%
                    </span>
                  </td>
                  <td>
                    <span style={{ color: '#ffffff', display: 'flex', alignItems: 'center', gap: 3, fontSize: '0.74rem' }}>
                      Load <ArrowUpRight size={12} />
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

