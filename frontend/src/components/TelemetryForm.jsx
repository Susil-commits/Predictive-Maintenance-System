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
  Binary
} from 'lucide-react';

export default function TelemetryForm({ formData, onChange, onSubmit, loading, onReset }) {
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
  const rpmVibRatio = ((formData.rpm * formData.vibration) / 1000.0).toFixed(2);
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
                <span>RUNNING SHAP INFERENCE...</span>
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

