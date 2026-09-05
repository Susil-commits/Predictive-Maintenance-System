import React, { useState } from 'react';
import {
  Thermometer, Activity, Gauge, RotateCw, Clock,
  FileSpreadsheet, Database, Cpu, Radio, Shield,
  BarChart3, Zap, AlertTriangle, Play,
  Pause, Eye
} from 'lucide-react';

const SOURCES = [
  { id: 'all',       label: 'ANY SENSOR BUS',     sub: 'CAN-Bus / Modbus 500Hz',   icon: Database,        val: 'Active Stream',   color: '#34d399', y: 50 },
  { id: 'temp',      label: 'THERMAL SENSORS',    sub: 'Thermocouple Matrix',       icon: Thermometer,     val: '84.2 °C [Nominal]', color: '#f59e0b', y: 125 },
  { id: 'vib',       label: 'VIBRATION ACCEL',    sub: 'Harmonic Tri-Axial',       icon: Activity,        val: '0.24 g [Stable]',   color: '#10b981', y: 200 },
  { id: 'pressure',  label: 'HYDRAULIC PRESSURE', sub: 'Pneumatic Fluid Line',     icon: Gauge,           val: '22.4 bar [Loaded]', color: '#06b6d4', y: 275 },
  { id: 'rpm',       label: 'ROTOR SPEED (RPM)',  sub: 'Dynamic Tachometer',       icon: RotateCw,        val: '1820 RPM [Synch]',  color: '#8b5cf6', y: 350 },
  { id: 'hours',     label: 'OPERATING HOURS',    sub: 'Cumulative Service Wear',   icon: Clock,           val: '1240.5 hrs',        color: '#a1a1aa', y: 425 },
  { id: 'batch',     label: 'BATCH INGESTION',    sub: 'Parquet / CSV / Excel',    icon: FileSpreadsheet, val: '5000 Rows/Batch',   color: '#38bdf8', y: 500 },
];

const DESTINATIONS = [
  { id: 'studio',    label: 'REAL-TIME STUDIO',   sub: 'Calibrated Risk Gauge',    icon: Radio,           out: 'Prob: 0.12 (LOW RISK)',   color: '#10b981', y: 70 },
  { id: 'shap',      label: 'SHAP EXPLAINER',     sub: 'TreeExplainer Waterfall',  icon: BarChart3,       out: 'Vib: +0.14, Temp: -0.08', color: '#a78bfa', y: 170 },
  { id: 'drift',     label: 'MLOPS DRIFT RADAR',  sub: 'Population Stability Index', icon: Shield,        out: 'PSI: 0.04 (NO DRIFT)',    color: '#34d399', y: 275 },
  { id: 'audit',     label: 'POSTGRESQL AUDIT',   sub: 'Compliance Event Store',   icon: Database,        out: 'Record ID: #b94e-28af',   color: '#38bdf8', y: 380 },
  { id: 'trip',      label: 'SCADA TRIP ORDERS',  sub: 'Automated Safety Dispatch', icon: Zap,            out: 'Status: Standby / Armed', color: '#f43f5e', y: 480 },
];

export default function TelemetryPipelineFlow() {
  const [selectedNode, setSelectedNode] = useState(null);
  const [anomalyMode, setAnomalyMode] = useState(false);
  const [isPaused, setIsPaused] = useState(false);

  const activeColor = anomalyMode ? '#f43f5e' : '#10b981';

  return (
    <div className="flow-pipeline-container">
      {/* Header controls bar */}
      <div className="flow-controls-bar">
        <div className="flow-status-pill">
          <span
            className="status-dot"
            style={{
              backgroundColor: anomalyMode ? '#f43f5e' : '#10b981',
              boxShadow: `0 0 10px ${anomalyMode ? '#f43f5e' : '#10b981'}`,
              color: anomalyMode ? '#f43f5e' : '#10b981'
            }}
          />
          <span className="flow-status-text">
            PIPELINE: {anomalyMode ? 'ANOMALY OVERHEAT DETECTED' : 'NOMINAL STREAM (500 Hz)'}
          </span>
        </div>

        <div className="flow-actions-group">
          <button
            type="button"
            className={`flow-toggle-btn ${anomalyMode ? 'anomaly-active' : ''}`}
            onClick={() => setAnomalyMode(!anomalyMode)}
            title="Toggle normal telemetry vs high-risk equipment anomaly injection"
          >
            <AlertTriangle size={13} />
            <span>{anomalyMode ? 'Clear Anomaly' : 'Inject Anomaly'}</span>
          </button>

          <button
            type="button"
            className="flow-toggle-btn"
            onClick={() => setIsPaused(!isPaused)}
            title="Pause/resume packet animation"
          >
            {isPaused ? <Play size={13} /> : <Pause size={13} />}
            <span>{isPaused ? 'Resume' : 'Pause'}</span>
          </button>
        </div>
      </div>

      {/* Main SVG Flow Diagram Canvas (Shrinks fluidly to fit any screen on desktop, tablet, and mobile with zero scrollbar and zero loader) */}
      <div className="flow-canvas-wrapper">
        <svg
          viewBox="0 0 1200 590"
          preserveAspectRatio="xMidYMid meet"
          className="flow-svg-canvas"
          style={{ width: '100%', height: 'auto', display: 'block' }}
        >
            <defs>
              {/* Soft Central Aura Radial Glow */}
              <radialGradient id="centerAura" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor={anomalyMode ? '#f43f5e' : '#10b981'} stopOpacity="0.28" />
                <stop offset="50%" stopColor={anomalyMode ? '#f59e0b' : '#06b6d4'} stopOpacity="0.12" />
                <stop offset="100%" stopColor="#000000" stopOpacity="0" />
              </radialGradient>

              {/* Glow filter */}
              <filter id="nodeGlow" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="6" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
              </filter>
            </defs>

            {/* Central Radial Aura Light */}
            <circle cx="600" cy="295" r="190" fill="url(#centerAura)" />

            {/* ================================================================= */}
            {/* 1. LEFT CONVERGING CURVES (Sources -> Central Ingest)             */}
            {/* ================================================================= */}
            {SOURCES.map((s) => {
              const isSelected = selectedNode?.id === s.id;
              const startX = 205;
              const startY = s.y + 20;
              const endX = 512;
              const endY = 295;
              const c1x = startX + 160;
              const c1y = startY;
              const c2x = endX - 80;
              const c2y = endY;
              const pathD = `M ${startX} ${startY} C ${c1x} ${c1y}, ${c2x} ${c2y}, ${endX} ${endY}`;

              return (
                <g key={`curve-in-${s.id}`}>
                  {/* Background track curve */}
                  <path
                    d={pathD}
                    fill="none"
                    stroke={isSelected ? (anomalyMode ? '#f43f5e' : '#10b981') : 'rgba(255,255,255,0.08)'}
                    strokeWidth={isSelected ? 2.5 : 1.5}
                    strokeLinecap="round"
                  />

                  {/* Animated flowing stream line */}
                  {!isPaused && (
                    <path
                      d={pathD}
                      fill="none"
                      stroke={anomalyMode ? '#f59e0b' : '#10b981'}
                      strokeWidth={isSelected ? 2.5 : 1.8}
                      strokeDasharray="6, 12"
                      strokeOpacity={isSelected ? 0.95 : 0.55}
                      className="flowing-dash"
                    />
                  )}
                </g>
              );
            })}

            {/* ================================================================= */}
            {/* 2. RIGHT DIVERGING CURVES (Central Route -> Destinations)         */}
            {/* ================================================================= */}
            {DESTINATIONS.map((d) => {
              const isSelected = selectedNode?.id === d.id;
              const startX = 688;
              const startY = 295;
              const midX = 770;
              const midY = 295;
              const endX = 995;
              const endY = d.y + 20;
              const c1x = midX + 60;
              const c1y = midY;
              const c2x = endX - 110;
              const c2y = endY;
              const pathD = `M ${startX} ${startY} L ${midX} ${midY} C ${c1x} ${c1y}, ${c2x} ${c2y}, ${endX} ${endY}`;

              return (
                <g key={`curve-out-${d.id}`}>
                  {/* Track curve */}
                  <path
                    d={pathD}
                    fill="none"
                    stroke={isSelected ? (anomalyMode ? '#f43f5e' : '#10b981') : 'rgba(255,255,255,0.08)'}
                    strokeWidth={isSelected ? 2.5 : 1.5}
                    strokeLinecap="round"
                  />

                  {/* Animated dash line */}
                  {!isPaused && (
                    <path
                      d={pathD}
                      fill="none"
                      stroke={anomalyMode ? '#f43f5e' : '#34d399'}
                      strokeWidth={isSelected ? 2.5 : 1.8}
                      strokeDasharray="6, 12"
                      strokeOpacity={isSelected ? 0.95 : 0.55}
                      className="flowing-dash-reverse"
                    />
                  )}
                </g>
              );
            })}

            {/* ================================================================= */}
            {/* 3. ANIMATED GLIDING PACKET BADGES                                 */}
            {/* ================================================================= */}
            {!isPaused && (
              <g className="flow-gliding-layer" style={{ pointerEvents: 'none' }}>
                {/* Event Badge 1 on Source 1 (Temp) */}
                <g className="flow-gliding-packet" style={{ pointerEvents: 'none' }}>
                  <animateMotion
                    path="M 205 70 C 365 70, 432 295, 512 295"
                    dur={anomalyMode ? '2.2s' : '3.6s'}
                    repeatCount="indefinite"
                    rotate="auto"
                  />
                  <rect x="-26" y="-10" width="52" height="20" rx="10" fill="#18181b" stroke={anomalyMode ? '#f43f5e' : '#f59e0b'} strokeWidth="1.2" />
                  <polygon points="-18,2 -13,-6 -8,2" fill={anomalyMode ? '#f43f5e' : '#f59e0b'} />
                  <text x="3" y="3.5" textAnchor="middle" fill="#ffffff" fontSize="8.5" fontFamily="var(--font-mono)" fontWeight="700">
                    {anomalyMode ? '98.4°C' : 'EVENT'}
                  </text>
                </g>

                {/* Event Badge 2 on Source 2 (Vibration) */}
                <g className="flow-gliding-packet" style={{ pointerEvents: 'none' }}>
                  <animateMotion
                    path="M 205 145 C 365 145, 432 295, 512 295"
                    dur={anomalyMode ? '1.9s' : '3.2s'}
                    repeatCount="indefinite"
                    rotate="auto"
                  />
                  <rect x="-28" y="-10" width="56" height="20" rx="10" fill="#18181b" stroke={anomalyMode ? '#f43f5e' : '#f59e0b'} strokeWidth="1.2" />
                  <polygon points="-20,2 -15,-6 -10,2" fill="#f59e0b" />
                  <text x="3" y="3.5" textAnchor="middle" fill="#ffffff" fontSize="8.5" fontFamily="var(--font-mono)" fontWeight="700">
                    {anomalyMode ? 'ALERTS' : 'EVENTS'}
                  </text>
                </g>

                {/* Event Badge 3 on Source 3 (Pressure) */}
                <g className="flow-gliding-packet" style={{ pointerEvents: 'none' }}>
                  <animateMotion
                    path="M 205 220 C 365 220, 432 295, 512 295"
                    dur={anomalyMode ? '2.4s' : '3.8s'}
                    repeatCount="indefinite"
                    rotate="auto"
                  />
                  <rect x="-25" y="-9" width="50" height="18" rx="9" fill="#18181b" stroke="#10b981" strokeWidth="1.2" />
                  <circle cx="-14" cy="0" r="3.5" fill="#10b981" />
                  <text x="4" y="3.5" textAnchor="middle" fill="#ffffff" fontSize="8" fontFamily="var(--font-mono)" fontWeight="700">
                    STREAM
                  </text>
                </g>

                {/* Event Badge 4 on Source 4 (RPM) */}
                <g className="flow-gliding-packet" style={{ pointerEvents: 'none' }}>
                  <animateMotion
                    path="M 205 295 C 365 295, 432 295, 512 295"
                    dur={anomalyMode ? '1.8s' : '3.0s'}
                    repeatCount="indefinite"
                    rotate="auto"
                  />
                  <rect x="-26" y="-10" width="52" height="20" rx="10" fill="#18181b" stroke={anomalyMode ? '#f43f5e' : '#06b6d4'} strokeWidth="1.2" />
                  <text x="0" y="3.5" textAnchor="middle" fill="#ffffff" fontSize="8.5" fontFamily="var(--font-mono)" fontWeight="700">
                    {anomalyMode ? '0.42g' : 'EVENT'}
                  </text>
                </g>

                {/* Event Badge 5 on Source 6 (Operating Hours) */}
                <g className="flow-gliding-packet" style={{ pointerEvents: 'none' }}>
                  <animateMotion
                    path="M 205 445 C 365 445, 432 295, 512 295"
                    dur="4.0s"
                    repeatCount="indefinite"
                    rotate="auto"
                  />
                  <rect x="-25" y="-9" width="50" height="18" rx="9" fill="#18181b" stroke="#a1a1aa" strokeWidth="1.2" />
                  <text x="0" y="3" textAnchor="middle" fill="#ffffff" fontSize="8" fontFamily="var(--font-mono)" fontWeight="700">
                    EVENT
                  </text>
                </g>

                {/* Exit Trunk Badge: "ALERT" with Warning / Check icon */}
                <g className="flow-gliding-packet" style={{ pointerEvents: 'none' }}>
                  <animateMotion
                    path="M 688 295 L 770 295 C 830 295, 880 190, 995 190"
                    dur={anomalyMode ? '2.1s' : '3.3s'}
                    repeatCount="indefinite"
                    rotate="auto"
                  />
                  <rect
                    x="-28" y="-11" width="56" height="22" rx="11"
                    fill="#0a0a0c"
                    stroke={anomalyMode ? '#f43f5e' : '#10b981'}
                    strokeWidth="1.4"
                  />
                  <circle cx="-16" cy="0" r="4.5" fill={anomalyMode ? '#f43f5e' : '#10b981'} />
                  <path d="M -18 -0.5 L -16 1.5 L -13 -2" fill="none" stroke="#000000" strokeWidth="1.2" strokeLinecap="round" />
                  <text x="5" y="3.5" textAnchor="middle" fill="#ffffff" fontSize="9" fontFamily="var(--font-mono)" fontWeight="700">
                    {anomalyMode ? 'TRIP' : 'ALERT'}
                  </text>
                </g>

                {/* Output Branch Badge: "EVENT" to Cloud Storage / DB */}
                <g className="flow-gliding-packet" style={{ pointerEvents: 'none' }}>
                  <animateMotion
                    path="M 770 295 C 830 295, 880 380, 995 380"
                    dur="3.4s"
                    repeatCount="indefinite"
                    rotate="auto"
                  />
                  <rect x="-26" y="-10" width="52" height="20" rx="10" fill="#0a0a0c" stroke="#38bdf8" strokeWidth="1.2" />
                  <text x="0" y="3.5" textAnchor="middle" fill="#38bdf8" fontSize="8.5" fontFamily="var(--font-mono)" fontWeight="700">
                    EVENT
                  </text>
                </g>
              </g>
            )}

            {/* ================================================================= */}
            {/* 4. CENTRAL PROCESSING DIAMOND (The Core Hub)                      */}
            {/* ================================================================= */}
            <g transform="translate(600, 295)">
              {/* Top Lobe: REDUCE / FEATURE ENG */}
              <g
                className="flow-diamond-petal"
                onClick={() => setSelectedNode({
                  id: 'reduce',
                  label: 'FEATURE ENGINEERING (REDUCE)',
                  sub: 'Interaction Feature Generation',
                  val: 'Computes Thermal Excess, Overstrain Index, Vibration Wear Index, and RPM-Pressure mechanical load.'
                })}
              >
                <rect
                  x="-46" y="-100" width="92" height="42" rx="10"
                  fill="#0f1715"
                  stroke={anomalyMode ? '#f43f5e' : 'rgba(16, 185, 129, 0.45)'}
                  strokeWidth="1.5"
                />
                <text x="0" y="-76" textAnchor="middle" fill={anomalyMode ? '#fda4af' : '#6ee7b7'} fontSize="10.5" fontFamily="var(--font-mono)" fontWeight="700" letterSpacing="0.04em">
                  REDUCE
                </text>
                <text x="0" y="-65" textAnchor="middle" fill="var(--text-dim)" fontSize="7.5" fontFamily="var(--font-mono)">
                  FEATURE ENG
                </text>
              </g>

              {/* Left Lobe: INGEST */}
              <g
                className="flow-diamond-petal"
                onClick={() => setSelectedNode({
                  id: 'ingest',
                  label: 'INGESTION ENGINE',
                  sub: '500Hz Sensory Input Validator',
                  val: 'Fuzzy column mapping, bounds checking (e.g. Temp 20-200°C, Vib 0-10g), and NaN/Inf rejection.'
                })}
              >
                <rect
                  x="-106" y="-21" width="52" height="42" rx="10"
                  fill="#0f1715"
                  stroke={anomalyMode ? '#f43f5e' : 'rgba(16, 185, 129, 0.45)'}
                  strokeWidth="1.5"
                />
                <text x="-80" y="4" textAnchor="middle" fill={anomalyMode ? '#fda4af' : '#6ee7b7'} fontSize="10.5" fontFamily="var(--font-mono)" fontWeight="700" letterSpacing="0.04em">
                  INGEST
                </text>
              </g>

              {/* Bottom Lobe: NORMALIZE */}
              <g
                className="flow-diamond-petal"
                onClick={() => setSelectedNode({
                  id: 'normalize',
                  label: 'CALIBRATION & NORMALIZATION',
                  sub: 'Platt Scaling & Robust Scaler',
                  val: 'CalibratedClassifierCV ensures sigmoid output maps to mathematically true posterior probabilities.'
                })}
              >
                <rect
                  x="-52" y="58" width="104" height="42" rx="10"
                  fill="#0f1715"
                  stroke={anomalyMode ? '#f43f5e' : 'rgba(16, 185, 129, 0.45)'}
                  strokeWidth="1.5"
                />
                <text x="0" y="82" textAnchor="middle" fill={anomalyMode ? '#fda4af' : '#6ee7b7'} fontSize="10.5" fontFamily="var(--font-mono)" fontWeight="700" letterSpacing="0.04em">
                  NORMALIZE
                </text>
                <text x="0" y="93" textAnchor="middle" fill="var(--text-dim)" fontSize="7.5" fontFamily="var(--font-mono)">
                  PLATT SCALING
                </text>
              </g>

              {/* Right Lobe: ROUTE / INFERENCE */}
              <g
                className="flow-diamond-petal"
                onClick={() => setSelectedNode({
                  id: 'route',
                  label: 'INFERENCE & ROUTING CORE',
                  sub: 'PR-Tuned Decision Threshold Engine',
                  val: 'Evaluates XGBoost decision boundary (Threshold: 0.6444) and routes outputs to SHAP and live webhooks.'
                })}
              >
                <rect
                  x="54" y="-21" width="52" height="42" rx="10"
                  fill="#0f1715"
                  stroke={anomalyMode ? '#f43f5e' : 'rgba(16, 185, 129, 0.45)'}
                  strokeWidth="1.5"
                />
                <text x="80" y="4" textAnchor="middle" fill={anomalyMode ? '#fda4af' : '#6ee7b7'} fontSize="10.5" fontFamily="var(--font-mono)" fontWeight="700" letterSpacing="0.04em">
                  ROUTE
                </text>
              </g>

              {/* Central Circle with Rotating Ring of 12 Dots */}
              <circle cx="0" cy="0" r="42" fill="#ffffff" stroke="rgba(255,255,255,0.2)" strokeWidth="1" />
              <circle cx="0" cy="0" r="38" fill="#f8fafc" />

              {/* Rotating 12-Dot Radial Array */}
              <g className="rotating-dots-group">
                {[...Array(12)].map((_, i) => {
                  const angle = (i * 30 * Math.PI) / 180;
                  const r = 24;
                  const dx = r * Math.cos(angle);
                  const dy = r * Math.sin(angle);
                  return (
                    <circle
                      key={i}
                      cx={dx}
                      cy={dy}
                      r={i % 3 === 0 ? 3.5 : 2.5}
                      fill={anomalyMode ? (i % 2 === 0 ? '#f43f5e' : '#09090b') : (i % 2 === 0 ? '#09090b' : '#10b981')}
                    />
                  );
                })}
              </g>

              {/* Pulsing Core Center Dot */}
              <circle cx="0" cy="0" r="7" fill={anomalyMode ? '#f43f5e' : '#09090b'} />
              <circle cx="0" cy="0" r="3.5" fill="#ffffff" />
            </g>

            {/* ================================================================= */}
            {/* 5. LEFT SOURCE NODES (Interactive Pill Cards)                     */}
            {/* ================================================================= */}
            {SOURCES.map((s) => {
              const isSelected = selectedNode?.id === s.id;
              const IconComp = s.icon;
              return (
                <g
                  key={`source-pill-${s.id}`}
                  className="flow-node-group"
                  transform={`translate(30, ${s.y})`}
                  onClick={() => setSelectedNode(s)}
                >
                  {/* Rounded Pill Box */}
                  <rect
                    x="0" y="0" width="175" height="40" rx="20"
                    fill={isSelected ? 'rgba(255,255,255,0.1)' : '#0d0d12'}
                    stroke={isSelected ? s.color : 'rgba(255,255,255,0.14)'}
                    strokeWidth={isSelected ? 2 : 1}
                  />
                  {/* Node Icon */}
                  <circle cx="20" cy="20" r="11" fill="rgba(255,255,255,0.05)" />
                  <g transform="translate(13.5, 13.5)">
                    <IconComp size={13} color={isSelected ? s.color : '#a1a1aa'} />
                  </g>
                  {/* Label & Subtitle */}
                  <text x="38" y="19" fill="#f4f4f5" fontSize="9" fontFamily="var(--font-mono)" fontWeight="700" letterSpacing="0.04em">
                    {s.label}
                  </text>
                  <text x="38" y="29" fill="var(--text-dim)" fontSize="7.2" fontFamily="var(--font-mono)">
                    {s.sub}
                  </text>
                </g>
              );
            })}

            {/* ================================================================= */}
            {/* 6. RIGHT DESTINATION NODES (Interactive Output Cards)              */}
            {/* ================================================================= */}
            {DESTINATIONS.map((d) => {
              const isSelected = selectedNode?.id === d.id;
              const IconComp = d.icon;
              return (
                <g
                  key={`dest-pill-${d.id}`}
                  className="flow-node-group"
                  transform={`translate(995, ${d.y})`}
                  onClick={() => setSelectedNode(d)}
                >
                  {/* Rounded Pill Box */}
                  <rect
                    x="0" y="0" width="180" height="40" rx="20"
                    fill={isSelected ? 'rgba(255,255,255,0.1)' : '#0d0d12'}
                    stroke={isSelected ? d.color : (anomalyMode && d.id === 'trip' ? '#f43f5e' : 'rgba(255,255,255,0.14)')}
                    strokeWidth={isSelected ? 2 : 1}
                  />
                  {/* Node Icon */}
                  <circle cx="20" cy="20" r="11" fill="rgba(255,255,255,0.05)" />
                  <g transform="translate(13.5, 13.5)">
                    <IconComp size={13} color={isSelected ? d.color : (anomalyMode && d.id === 'trip' ? '#f43f5e' : '#a1a1aa')} />
                  </g>
                  {/* Label & Subtitle */}
                  <text x="38" y="19" fill="#f4f4f5" fontSize="9" fontFamily="var(--font-mono)" fontWeight="700" letterSpacing="0.04em">
                    {d.label}
                  </text>
                  <text x="38" y="29" fill="var(--text-dim)" fontSize="7.2" fontFamily="var(--font-mono)">
                    {d.sub}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>

      {/* Interactive Node Telemetry Inspector Drawer */}
      <div className="flow-inspect-panel">
        <div className="flow-inspect-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Eye size={14} color={activeColor} />
            <span style={{ fontSize: '0.78rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: '#ffffff' }}>
              {selectedNode ? `NODE INSPECTION: ${selectedNode.label}` : 'PIPELINE TELEMETRY LIVE MONITOR'}
            </span>
          </div>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
            CLICK ANY COMPONENT TO AUDIT PAYLOAD
          </span>
        </div>

        <div className="flow-inspect-body">
          {selectedNode ? (
            <div className="flow-inspect-grid">
              <div className="flow-inspect-item">
                <span className="flow-inspect-label">SUB-MODULE</span>
                <span className="flow-inspect-val">{selectedNode.sub}</span>
              </div>
              <div className="flow-inspect-item">
                <span className="flow-inspect-label">TELEMETRY / OUTPUT VALUE</span>
                <span className="flow-inspect-val" style={{ color: activeColor }}>
                  {selectedNode.val || selectedNode.out}
                </span>
              </div>
              <div className="flow-inspect-item">
                <span className="flow-inspect-label">PROCESSING STATUS</span>
                <span className="flow-inspect-val" style={{ color: '#10b981' }}>
                  ACTIVE (0.02ms latency)
                </span>
              </div>
            </div>
          ) : (
            <div className="flow-inspect-grid">
              <div className="flow-inspect-item">
                <span className="flow-inspect-label">ACTIVE SENSORS</span>
                <span className="flow-inspect-val">5 Streams (Temp, Vib, Press, RPM, Hrs)</span>
              </div>
              <div className="flow-inspect-item">
                <span className="flow-inspect-label">CORE MODEL</span>
                <span className="flow-inspect-val">Calibrated XGBoost (v13, AUC 99.4%)</span>
              </div>
              <div className="flow-inspect-item">
                <span className="flow-inspect-label">EXPLAINABILITY</span>
                <span className="flow-inspect-val">SHAP TreeExplainer Waterfall Active</span>
              </div>
              <div className="flow-inspect-item">
                <span className="flow-inspect-label">SIMULATION STATE</span>
                <span className="flow-inspect-val" style={{ color: activeColor }}>
                  {anomalyMode ? 'HIGH ANOMALY (Thermal Overheat & Overstrain)' : 'NORMAL OPERATIONAL TELEMETRY'}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
