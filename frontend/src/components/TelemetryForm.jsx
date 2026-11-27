import React, { useState } from 'react';
import { 
  Thermometer, 
  Gauge, 
  Activity, 
  Clock, 
  Sliders, 
  Play, 
  Copy, 
  Check, 
  RotateCcw,
  Binary,
  Cpu,
  ChevronDown,
  ChevronUp
} from 'lucide-react';

const RUNTIME_OPTIONS = [
  { id: 'xgboost', label: 'XGBoost + SHAP', hint: 'Full calibrated attribution (~2 ms)' },
  { id: 'onnx', label: 'ONNX Edge (C++)', hint: 'Sub-ms fast scoring (~21 µs)' },
  { id: 'hybrid', label: 'Hybrid Router', hint: 'ONNX triage + on-demand SHAP' },
];

const REGIME_OPTIONS = [
  { value: 'idle', label: 'Idle / Standby' },
  { value: 'warmup', label: 'Thermal Warmup' },
  { value: 'steady_state_light', label: 'Steady State (Light)' },
  { value: 'steady_state_heavy', label: 'Steady State (Heavy)' },
  { value: 'shutdown', label: 'Controlled Shutdown' },
];

export default function TelemetryForm({
  formData,
  onChange,
  onSubmit,
  loading,
  onReset,
  runtime = 'xgboost',
  onRuntimeChange,
  contextEnabled = false,
  onToggleContext,
  contextData = {},
  onContextChange,
}) {
  const [copied, setCopied] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    onChange(name, parseFloat(value) || 0);
  };

  const handleCopyPayload = () => {
    navigator.clipboard.writeText(JSON.stringify(formData, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Real-time engineered features calculated client-side matching predictor.py
  const tempPressureIndex = ((formData.temperature * formData.pressure) / 100.0).toFixed(2);
  const vibrationWearIndex = (formData.vibration * (formData.operating_hours / 1000.0)).toFixed(2);
  const thermalExcess = Math.max(0, formData.temperature - 86.0).toFixed(1);
  const overstrainIndex = ((formData.pressure / 25.0) * Math.max(0, formData.vibration - 0.35)).toFixed(2);

  return (
    <div className="glass-panel">
      <div className="panel-header">
        <h2 className="panel-title">
          <Sliders size={18} className="panel-icon" />
          <span>Telemetry Studio</span>
        </h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            type="button"
            onClick={handleCopyPayload}
            className="preset-btn"
            title="Copy current telemetry JSON"
            style={{ padding: '4px 8px', fontSize: '0.7rem' }}
          >
            {copied ? <Check size={12} color="#10b981" /> : <Copy size={12} />}
            <span>{copied ? 'Copied' : 'Copy JSON'}</span>
          </button>
          {onReset && (
            <button
              type="button"
              onClick={onReset}
              className="preset-btn"
              title="Reset to default baseline"
              style={{ padding: '4px 8px', fontSize: '0.7rem' }}
            >
              <RotateCcw size={12} />
              <span>Reset</span>
            </button>
          )}
          <span className="field-unit">5 SENSORS ACTIVE</span>
        </div>
      </div>

      <form onSubmit={onSubmit}>
        <div className="input-grid">
          {/* Temperature */}
          <div className="form-group">
            <div className="form-label-row">
              <label htmlFor="temp-input" className="field-label">
                <Thermometer size={14} color="#f43f5e" />
                <span>Operating Temperature</span>
              </label>
              <span className="field-unit">°C</span>
            </div>
            <div className="input-wrapper">
              <input
                id="temp-input"
                type="number"
                step="0.1"
                name="temperature"
                value={formData.temperature}
                onChange={handleChange}
                className="telemetry-input"
                min="40"
                max="130"
                required
              />
            </div>
            <input
              type="range"
              min="50"
              max="120"
              step="0.5"
              name="temperature"
              value={formData.temperature}
              onChange={handleChange}
              className="slider-control"
            />
          </div>

          {/* RPM */}
          <div className="form-group">
            <div className="form-label-row">
              <label htmlFor="rpm-input" className="field-label">
                <Gauge size={14} color="#ffffff" />
                <span>Rotational Speed (RPM)</span>
              </label>
              <span className="field-unit">rev/min</span>
            </div>
            <div className="input-wrapper">
              <input
                id="rpm-input"
                type="number"
                step="10"
                name="rpm"
                value={formData.rpm}
                onChange={handleChange}
                className="telemetry-input"
                min="800"
                max="3600"
                required
              />
            </div>
            <input
              type="range"
              min="1000"
              max="3500"
              step="50"
              name="rpm"
              value={formData.rpm}
              onChange={handleChange}
              className="slider-control"
            />
          </div>

          {/* Pressure */}
          <div className="form-group">
            <div className="form-label-row">
              <label htmlFor="pressure-input" className="field-label">
                <Activity size={14} color="#e4e4e7" />
                <span>Hydraulic System Pressure</span>
              </label>
              <span className="field-unit">bar</span>
            </div>
            <div className="input-wrapper">
              <input
                id="pressure-input"
                type="number"
                step="0.1"
                name="pressure"
                value={formData.pressure}
                onChange={handleChange}
                className="telemetry-input"
                min="10"
                max="50"
                required
              />
            </div>
            <input
              type="range"
              min="15"
              max="45"
              step="0.5"
              name="pressure"
              value={formData.pressure}
              onChange={handleChange}
              className="slider-control"
            />
          </div>

          {/* Vibration */}
          <div className="form-group">
            <div className="form-label-row">
              <label htmlFor="vibration-input" className="field-label">
                <Activity size={14} color="#f59e0b" />
                <span>Vibration Amplitude</span>
              </label>
              <span className="field-unit">g (RMS)</span>
            </div>
            <div className="input-wrapper">
              <input
                id="vibration-input"
                type="number"
                step="0.01"
                name="vibration"
                value={formData.vibration}
                onChange={handleChange}
                className="telemetry-input"
                min="0.05"
                max="1.50"
                required
              />
            </div>
            <input
              type="range"
              min="0.10"
              max="1.20"
              step="0.02"
              name="vibration"
              value={formData.vibration}
              onChange={handleChange}
              className="slider-control"
            />
          </div>

          {/* Operating Hours */}
          <div className="form-group">
            <div className="form-label-row">
              <label htmlFor="hours-input" className="field-label">
                <Clock size={14} color="#10b981" />
                <span>Operating Service Hours</span>
              </label>
              <span className="field-unit">cumulative</span>
            </div>
            <div className="input-wrapper">
              <input
                id="hours-input"
                type="number"
                step="10"
                name="operating_hours"
                value={formData.operating_hours}
                onChange={handleChange}
                className="telemetry-input"
                min="50"
                max="8000"
                required
              />
            </div>
            <input
              type="range"
              min="200"
              max="6500"
              step="50"
              name="operating_hours"
              value={formData.operating_hours}
              onChange={handleChange}
              className="slider-control"
            />
          </div>

          {/* 6th Slot: Real-Time Engineered Features Matrix */}
          <div className="form-group" style={{ background: '#050507', borderColor: 'rgba(255, 255, 255, 0.06)' }}>
            <div className="form-label-row">
              <span className="field-label" style={{ color: 'var(--text-dim)' }}>
                <Binary size={14} color="#71717a" />
                <span>Derived Engineered Features</span>
              </span>
              <span className="field-unit">REAL-TIME</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '5px', marginTop: '2px', fontFamily: 'var(--font-mono)', fontSize: '0.72rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #18181b', paddingBottom: '2px' }}>
                <span style={{ color: '#71717a' }}>thermal_excess:</span>
                <span style={{ color: parseFloat(thermalExcess) > 0 ? '#f43f5e' : '#ffffff', fontWeight: 600 }}>{thermalExcess}°C</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #18181b', paddingBottom: '2px' }}>
                <span style={{ color: '#71717a' }}>overstrain_idx:</span>
                <span style={{ color: parseFloat(overstrainIndex) > 0 ? '#f59e0b' : '#ffffff', fontWeight: 600 }}>{overstrainIndex}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #18181b', paddingBottom: '2px' }}>
                <span style={{ color: '#71717a' }}>vibration_wear:</span>
                <span style={{ color: '#ffffff', fontWeight: 600 }}>{vibrationWearIndex}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#71717a' }}>temp_pressure:</span>
                <span style={{ color: '#ffffff', fontWeight: 600 }}>{tempPressureIndex}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Multi-Runtime Inference Selector & Context Engineering Toggle */}
        <div style={{ marginTop: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
          {onRuntimeChange && (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8, padding: '8px 12px', background: 'rgba(255,255,255,0.02)', borderRadius: 8, border: '1px solid var(--border-subtle)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>
                <Cpu size={13} color="#38bdf8" />
                <span>INFERENCE RUNTIME</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                {RUNTIME_OPTIONS.map((rt) => (
                  <button
                    key={rt.id}
                    type="button"
                    onClick={() => onRuntimeChange(rt.id)}
                    title={rt.hint}
                    className={`preset-btn ${runtime === rt.id ? 'highlight' : ''}`}
                    style={{
                      padding: '4px 10px',
                      fontSize: '0.7rem',
                      fontFamily: 'var(--font-mono)',
                      borderColor: runtime === rt.id ? '#38bdf8' : undefined,
                      color: runtime === rt.id ? '#38bdf8' : undefined,
                    }}
                  >
                    {rt.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {onToggleContext && (
            <div style={{ background: 'rgba(255,255,255,0.02)', borderRadius: 8, border: '1px solid var(--border-subtle)', overflow: 'hidden' }}>
              <button
                type="button"
                onClick={onToggleContext}
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '8px 12px',
                  background: 'transparent',
                  border: 'none',
                  color: '#e4e4e7',
                  cursor: 'pointer',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.72rem',
                }}
              >
                <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ color: contextEnabled ? '#34d399' : '#71717a' }}>●</span>
                  <span>CONTEXT ENGINEERING ENVELOPE (Regime · Ambient ΔT · dT/dt · Crest Factor)</span>
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-dim)' }}>
                  <span>{contextEnabled ? 'ACTIVE' : 'OPTIONAL'}</span>
                  {contextEnabled ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                </span>
              </button>

              {contextEnabled && onContextChange && (
                <div style={{ padding: '10px 12px 12px', borderTop: '1px solid var(--border-subtle)', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(145px, 1fr))', gap: 10 }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.66rem', color: 'var(--text-dim)', marginBottom: 4, fontFamily: 'var(--font-mono)' }}>MACHINE ID</label>
                    <input
                      type="text"
                      value={contextData.machine_id || ''}
                      onChange={(e) => onContextChange('machine_id', e.target.value)}
                      className="telemetry-input"
                      style={{ fontSize: '0.76rem', padding: '6px 8px' }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.66rem', color: 'var(--text-dim)', marginBottom: 4, fontFamily: 'var(--font-mono)' }}>OPERATIONAL REGIME</label>
                    <select
                      value={contextData.regime || 'steady_state_heavy'}
                      onChange={(e) => onContextChange('regime', e.target.value)}
                      className="telemetry-input"
                      style={{ fontSize: '0.76rem', padding: '6px 8px', background: '#09090b' }}
                    >
                      {REGIME_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.66rem', color: 'var(--text-dim)', marginBottom: 4, fontFamily: 'var(--font-mono)' }}>AMBIENT TEMP (°C)</label>
                    <input
                      type="number"
                      step="0.5"
                      min="-20"
                      max="60"
                      value={contextData.ambient_temperature ?? 25.0}
                      onChange={(e) => onContextChange('ambient_temperature', parseFloat(e.target.value) || 0)}
                      className="telemetry-input"
                      style={{ fontSize: '0.76rem', padding: '6px 8px' }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.66rem', color: 'var(--text-dim)', marginBottom: 4, fontFamily: 'var(--font-mono)' }}>dT/dt (°C/min)</label>
                    <input
                      type="number"
                      step="0.1"
                      value={contextData.temp_rate_of_change ?? 0.0}
                      onChange={(e) => onContextChange('temp_rate_of_change', parseFloat(e.target.value) || 0)}
                      className="telemetry-input"
                      style={{ fontSize: '0.76rem', padding: '6px 8px' }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.66rem', color: 'var(--text-dim)', marginBottom: 4, fontFamily: 'var(--font-mono)' }}>VIB CREST FACTOR</label>
                    <input
                      type="number"
                      step="0.1"
                      min="1"
                      max="20"
                      value={contextData.vibration_crest_factor ?? 2.5}
                      onChange={(e) => onContextChange('vibration_crest_factor', parseFloat(e.target.value) || 0)}
                      className="telemetry-input"
                      style={{ fontSize: '0.76rem', padding: '6px 8px' }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.66rem', color: 'var(--text-dim)', marginBottom: 4, fontFamily: 'var(--font-mono)' }}>24H PRIOR FAULTS</label>
                    <input
                      type="number"
                      min="0"
                      max="100"
                      value={contextData.recent_fault_count_24h ?? 0}
                      onChange={(e) => onContextChange('recent_fault_count_24h', parseInt(e.target.value, 10) || 0)}
                      className="telemetry-input"
                      style={{ fontSize: '0.76rem', padding: '6px 8px' }}
                    />
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="action-row">
          <button
            id="predict-submit-btn"
            type="submit"
            className="submit-btn"
            disabled={loading}
          >
            {loading ? (
              <>
                <span className="spinner" style={{ borderColor: '#888', borderTopColor: '#000' }} />
                <span>EVALUATING SENSOR RISK...</span>
              </>
            ) : (
              <>
                <Play size={15} fill="#000000" />
                <span>EVALUATE TELEMETRY</span>
                <span className="kbd">⌘+ENTER</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}

