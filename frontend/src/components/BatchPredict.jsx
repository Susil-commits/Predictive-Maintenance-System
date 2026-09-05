import React, { useState, useRef } from 'react';
import {
  Upload, FileText, AlertTriangle, CheckCircle2,
  BarChart3, ChevronDown, ChevronUp, Loader2, X,
  AlertCircle, TrendingUp, TrendingDown, Download
} from 'lucide-react';
import { batchPredict } from '../api';

const ACCEPTED_EXTS = ['.csv', '.json', '.xlsx', '.parquet'];

function RowResult({ row, index }) {
  const [open, setOpen] = useState(false);
  const isErr = Boolean(row.error);
  const isHigh = row.prediction === 'HIGH';

  return (
    <div className="batch-row-card" data-risk={isErr ? 'error' : (isHigh ? 'high' : 'low')}>
      <div
        className="batch-row-header"
        onClick={() => setOpen(o => !o)}
        role="button"
        tabIndex={0}
        onKeyDown={e => e.key === 'Enter' && setOpen(o => !o)}
      >
        <div className="batch-row-left">
          <span className="batch-row-index">#{row.row_index + 1}</span>
          {isErr
            ? <span className="badge-risk" style={{ background: 'rgba(245,158,11,0.12)', color: '#fbbf24', border: '1px solid rgba(245,158,11,0.3)' }}>ERROR</span>
            : <span className={`badge-risk ${isHigh ? 'high' : 'low'}`}>{row.prediction}</span>
          }
          {!isErr && (
            <span className="batch-prob-pill">
              {(row.probability * 100).toFixed(1)}%
            </span>
          )}
        </div>
        <div className="batch-row-right">
          {isErr ? (
            <span className="batch-err-msg" title={row.error}>
              <AlertCircle size={12} style={{ flexShrink: 0 }} /> {row.error}
            </span>
          ) : (
            <span className="field-unit">{row.maintenance_required ? 'ACTION REQUIRED' : 'NOMINAL'}</span>
          )}
          {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </div>
      </div>

      {open && !isErr && (
        <div className="batch-row-detail">
          {/* Input recap */}
          <div className="batch-detail-section">
            <div className="batch-detail-label">Input Telemetry</div>
            <div className="batch-input-chips">
              {Object.entries(row.input_data || {}).map(([k, v]) => (
                <span key={k} className="batch-input-chip">
                  <span className="chip-key">{k}:</span>
                  <span className="chip-val">{typeof v === 'number' ? v.toFixed(2) : v}</span>
                </span>
              ))}
            </div>
          </div>
          {/* Top factors */}
          {row.contributing_factors?.length > 0 && (
            <div className="batch-detail-section">
              <div className="batch-detail-label">Top Contributing Factors</div>
              <div className="batch-factors">
                {row.contributing_factors.slice(0, 3).map((f, i) => (
                  <div key={i} className="batch-factor-row">
                    <span className="batch-factor-name">{f.factor}</span>
                    <div className="batch-factor-bar-bg">
                      <div
                        className={`factor-bar-fill ${f.impact >= 0 ? 'risk-driver' : 'protective'}`}
                        style={{ width: `${Math.min(Math.abs(f.impact) * 400, 100)}%` }}
                      />
                    </div>
                    <span className={`factor-impact ${f.impact >= 0 ? 'positive' : 'negative'}`}>
                      {f.impact >= 0 ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
                      {f.impact >= 0 ? '+' : ''}{f.impact.toFixed(3)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function BatchPredict() {
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const fileInputRef = useRef();

  const processFile = async (f) => {
    if (!f) return;
    const ext = '.' + f.name.split('.').pop().toLowerCase();
    if (!ACCEPTED_EXTS.includes(ext)) {
      setError(`Unsupported file type: ${ext}. Accepted: ${ACCEPTED_EXTS.join(', ')}`);
      return;
    }
    setFile(f);
    setResult(null);
    setError(null);
    setLoading(true);
    try {
      const res = await batchPredict(f);
      setResult(res);
    } catch (err) {
      const msg = err?.response?.data?.detail || err.message || 'Batch prediction failed';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) processFile(f);
  };

  const onFileInput = (e) => {
    const f = e.target.files[0];
    if (f) processFile(f);
  };

  const clearAll = () => {
    setFile(null);
    setResult(null);
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const highRisk = result?.results?.filter(r => r.prediction === 'HIGH') || [];
  const lowRisk  = result?.results?.filter(r => r.prediction === 'LOW' && !r.error) || [];
  const errRows  = result?.results?.filter(r => r.error) || [];

  return (
    <div className="glass-panel" style={{ marginBottom: '24px' }}>
      <div className="panel-header">
        <h2 className="panel-title">
          <Upload size={18} className="panel-icon" />
          <span>Batch Predict</span>
          <span className="field-unit" style={{ marginLeft: 8 }}>CSV / JSON / XLSX / PARQUET</span>
        </h2>
        {(file || result) && (
          <button type="button" className="preset-btn" onClick={clearAll} style={{ padding: '4px 8px', fontSize: '0.7rem' }}>
            <X size={12} /> Clear
          </button>
        )}
      </div>

      {/* Drop Zone */}
      {!result && (
        <div
          className={`batch-dropzone ${dragging ? 'dragging' : ''} ${loading ? 'batch-loading' : ''}`}
          onDragOver={e => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          onClick={() => !loading && fileInputRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={e => e.key === 'Enter' && !loading && fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.json,.xlsx,.xls,.parquet"
            onChange={onFileInput}
            style={{ display: 'none' }}
          />
          {loading ? (
            <>
              <Loader2 size={28} className="batch-spin" style={{ color: 'var(--text-secondary)' }} />
              <p className="batch-drop-text">Running batch inference on <strong>{file?.name}</strong>…</p>
              <p className="batch-drop-sub">SHAP values computing for each row</p>
            </>
          ) : (
            <>
              <FileText size={28} style={{ color: 'var(--text-dim)' }} />
              <p className="batch-drop-text">
                {dragging ? 'Drop to upload' : 'Drag & drop a telemetry file or click to browse'}
              </p>
              <p className="batch-drop-sub">Columns auto-matched: temperature · rpm · pressure · vibration · operating_hours</p>
              <div className="batch-ext-badges">
                {ACCEPTED_EXTS.map(e => (
                  <span key={e} className="batch-ext-badge">{e}</span>
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="action-alert danger" style={{ marginTop: 12 }}>
          <AlertTriangle size={14} />
          <span>{error}</span>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="batch-results">
          {/* Summary bar */}
          <div className="batch-summary-bar">
            <div className="batch-stat">
              <span className="batch-stat-val">{result.total_rows}</span>
              <span className="batch-stat-label">Total Rows</span>
            </div>
            <div className="batch-stat">
              <span className="batch-stat-val" style={{ color: '#fb7185' }}>{result.high_risk_count}</span>
              <span className="batch-stat-label">HIGH Risk</span>
            </div>
            <div className="batch-stat">
              <span className="batch-stat-val" style={{ color: '#34d399' }}>{result.low_risk_count}</span>
              <span className="batch-stat-label">LOW Risk</span>
            </div>
            {result.error_rows > 0 && (
              <div className="batch-stat">
                <span className="batch-stat-val" style={{ color: '#f59e0b' }}>{result.error_rows}</span>
                <span className="batch-stat-label">Errors</span>
              </div>
            )}
            <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
              {result.error_rows === 0 && (
                <span className="action-alert safe" style={{ padding: '4px 10px', gap: 6 }}>
                  <CheckCircle2 size={13} /> All rows processed
                </span>
              )}
            </div>
          </div>

          {/* Risk donut-bar */}
          {(result.high_risk_count + result.low_risk_count) > 0 && (
            <div className="batch-risk-bar-wrap">
              <div className="batch-risk-bar">
                <div
                  className="batch-risk-bar-high"
                  style={{ width: `${(result.high_risk_count / result.processed_rows) * 100}%` }}
                />
                <div
                  className="batch-risk-bar-low"
                  style={{ width: `${(result.low_risk_count / result.processed_rows) * 100}%` }}
                />
              </div>
              <div className="batch-risk-bar-legend">
                <span><span style={{ color: '#fb7185' }}>■</span> HIGH {((result.high_risk_count / result.processed_rows) * 100).toFixed(0)}%</span>
                <span><span style={{ color: '#34d399' }}>■</span> LOW {((result.low_risk_count / result.processed_rows) * 100).toFixed(0)}%</span>
              </div>
            </div>
          )}

          {/* Row cards */}
          <div className="batch-rows-list">
            {result.results.map((row, i) => (
              <RowResult key={i} row={row} index={i} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
