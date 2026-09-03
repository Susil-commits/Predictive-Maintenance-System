import React from 'react';
import { History, Trash2, ArrowUpRight } from 'lucide-react';

export default function HistoryTable({ history, onSelectRow, onClearHistory }) {
  if (!history || history.length === 0) {
    return (
      <div className="glass-panel history-panel">
        <div className="panel-header">
          <h2 className="panel-title">
            <History size={18} className="panel-icon" />
            Database Prediction Audit Log
          </h2>
        </div>
        <p className="empty-state">No predictions recorded yet. Run a prediction above to log to database.</p>
      </div>
    );
  }

  return (
    <div className="glass-panel history-panel">
      <div className="panel-header">
        <h2 className="panel-title">
          <History size={18} className="panel-icon" />
          Database Audit Log ({history.length} records)
        </h2>
        <button
          type="button"
          onClick={onClearHistory}
          className="preset-btn"
          style={{ fontSize: '0.76rem', padding: '5px 10px' }}
          title="Clear database records"
        >
          <Trash2 size={13} />
          Clear Log
        </button>
      </div>

      <div className="table-responsive">
        <table className="history-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Temp (°C)</th>
              <th>RPM</th>
              <th>Pressure (bar)</th>
              <th>Vibration (g)</th>
              <th>Hours</th>
              <th>Risk</th>
              <th>Probability</th>
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
                  <td style={{ color: '#94a3b8' }}>{dateStr}</td>
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
                      {Math.round(row.probability * 100)}%
                    </span>
                  </td>
                  <td>
                    <span style={{ color: '#38bdf8', display: 'flex', alignItems: 'center', gap: 2, fontSize: '0.78rem' }}>
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
