import React from 'react';
import { Thermometer, Gauge, Activity, Clock, Sliders, Zap } from 'lucide-react';

export default function TelemetryForm({ formData, onChange, onSubmit, loading }) {
  const handleChange = (e) => {
    const { name, value } = e.target;
    onChange(name, parseFloat(value) || 0);
  };

  return (
    <div className="glass-panel">
      <div className="panel-header">
        <h2 className="panel-title">
          <Sliders size={20} className="panel-icon" />
          Vehicle Health Telemetry
        </h2>
        <span className="field-unit">5 SENSORS ACTIVE</span>
      </div>

      <form onSubmit={onSubmit}>
        <div className="input-grid">
          {/* Temperature */}
          <div className="form-group">
            <div className="form-label-row">
              <label htmlFor="temp-input" className="field-label">
                <Thermometer size={16} color="#fb7185" />
                Temperature
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
                <Gauge size={16} color="#38bdf8" />
                Rotational Speed (RPM)
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
                <Activity size={16} color="#a78bfa" />
                Hydraulic / System Pressure
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
                <Activity size={16} color="#fbbf24" />
                Vibration Amplitude
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
                <Clock size={16} color="#34d399" />
                Operating Service Hours
              </label>
              <span className="field-unit">hrs</span>
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
        </div>

        <button
          id="predict-submit-btn"
          type="submit"
          className="predict-btn"
          disabled={loading}
        >
          {loading ? (
            <>
              <span className="spinner"></span>
              Computing SHAP Inference...
            </>
          ) : (
            <>
              <Zap size={20} />
              [ PREDICT ]
            </>
          )}
        </button>
      </form>
    </div>
  );
}
