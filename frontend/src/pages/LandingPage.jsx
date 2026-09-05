import React, { useEffect, useRef, useState } from 'react';
import { Terminal, Cpu, Activity, Shield, Zap, BarChart3, ArrowRight, Radio } from 'lucide-react';

const TYPEWRITER_LINES = [
  '> initializing predictive_maintenance_system...',
  '> loading xgboost_calibrated.pkl              [OK]',
  '> shap_explainer: TreeExplainer ready         [OK]',
  '> drift_detector: PSI baseline loaded         [OK]',
  '> telemetry endpoints: /predict /batch-predict [OK]',
  '> system status: ALL SYSTEMS OPERATIONAL      [OK]',
];

function TypewriterConsole() {
  const [lines, setLines] = useState([]);
  const [curLine, setCurLine] = useState(0);
  const [curChar, setCurChar] = useState(0);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (curLine >= TYPEWRITER_LINES.length) { setDone(true); return; }
    const target = TYPEWRITER_LINES[curLine];
    if (curChar < target.length) {
      const t = setTimeout(() => setCurChar(c => c + 1), 22);
      return () => clearTimeout(t);
    } else {
      const t = setTimeout(() => {
        setLines(prev => [...prev, target]);
        setCurLine(l => l + 1);
        setCurChar(0);
      }, 180);
      return () => clearTimeout(t);
    }
  }, [curLine, curChar]);

  const partial = curLine < TYPEWRITER_LINES.length ? TYPEWRITER_LINES[curLine].slice(0, curChar) : '';

  return (
    <div className="land-console">
      <div className="land-console-bar">
        <span className="land-dot red" />
        <span className="land-dot yellow" />
        <span className="land-dot green" />
        <span className="land-console-title">pms://boot-sequence</span>
      </div>
      <div className="land-console-body">
        {lines.map((l, i) => (
          <div key={i} className="land-console-line">
            <span className="land-prompt">$</span>
            <span className={l.includes('[OK]') ? 'land-ok' : 'land-cmd'}>{l}</span>
          </div>
        ))}
        {!done && (
          <div className="land-console-line">
            <span className="land-prompt">$</span>
            <span className="land-cmd">{partial}</span>
            <span className="terminal-cursor" />
          </div>
        )}
        {done && (
          <div className="land-console-line" style={{ marginTop: 6 }}>
            <span className="land-prompt">$</span>
            <span style={{ color: '#10b981', fontWeight: 700 }}>READY — all subsystems nominal</span>
            <span className="terminal-cursor" style={{ background: '#10b981' }} />
          </div>
        )}
      </div>
    </div>
  );
}

const FEATURES = [
  {
    icon: <Cpu size={22} />,
    label: 'Calibrated XGBoost',
    desc: 'PR-curve optimised threshold, CalibratedClassifierCV, Platt scaling for true probabilities.',
  },
  {
    icon: <Activity size={22} />,
    label: 'SHAP Waterfall',
    desc: 'Per-prediction feature attribution. Real-time TreeExplainer for human-readable insights.',
  },
  {
    icon: <BarChart3 size={22} />,
    label: 'Drift Radar (PSI)',
    desc: 'Population Stability Index across 5 telemetry signals. Auto-retrain trigger on drift.',
  },
  {
    icon: <Zap size={22} />,
    label: 'Batch Inference',
    desc: 'Upload CSV / JSON / XLSX / Parquet. Row-by-row SHAP + fuzzy column matching.',
  },
  {
    icon: <Shield size={22} />,
    label: 'Role-Based Access',
    desc: 'Admin manages employees. Intruder detection on every login attempt.',
  },
  {
    icon: <Radio size={22} />,
    label: 'Live Telemetry Studio',
    desc: '5-sensor real-time input with engineered features computed client-side.',
  },
];

const STATS = [
  { val: '97.2%', label: 'Model Accuracy' },
  { val: '0.994', label: 'ROC-AUC' },
  { val: '< 50ms', label: 'Inference Latency' },
  { val: '5', label: 'Telemetry Sensors' },
];

export default function LandingPage({ onNavigateLogin }) {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 30);
    window.addEventListener('scroll', handler);
    return () => window.removeEventListener('scroll', handler);
  }, []);

  return (
    <div className="land-root">
      {/* Nav */}
      <nav className={`land-nav ${scrolled ? 'land-nav-scrolled' : ''}`}>
        <div className="land-nav-inner">
          <div className="brand-wrapper" style={{ gap: 10 }}>
            <div className="brand-icon">
              <Terminal size={18} />
            </div>
            <div className="brand-title-group">
              <span className="brand-title" style={{ fontSize: '1rem' }}>pms://telemetry</span>
              <span className="brand-tagline">Predictive Maintenance System</span>
            </div>
          </div>
          <button className="land-signin-btn" onClick={onNavigateLogin}>
            Sign In <ArrowRight size={14} />
          </button>
        </div>
      </nav>

      {/* Hero */}
      <section className="land-hero">
        <div className="land-hero-grid-bg" />
        <div className="land-hero-glow" />

        <div className="land-hero-content">
          <div className="land-badge">
            <span className="status-dot" style={{ background: '#10b981', color: '#10b981', width: 7, height: 7, borderRadius: '50%', boxShadow: '0 0 8px currentColor' }} />
            <span>Industrial IoT · Machine Learning · MLOps</span>
          </div>

          <h1 className="land-headline">
            Predict Equipment Failure<br />
            <span className="land-headline-accent">Before It Happens</span>
          </h1>

          <p className="land-subline">
            Real-time telemetry inference powered by calibrated XGBoost + SHAP waterfall diagnostics.
            Built for industrial maintenance teams who need answers, not black boxes.
          </p>

          <div className="land-hero-actions">
            <button className="land-cta-primary" onClick={onNavigateLogin}>
              <Terminal size={16} /> Access System
            </button>
            <div className="land-cta-hint">
              Authorised personnel only
            </div>
          </div>

          {/* Stats row */}
          <div className="land-stats-row">
            {STATS.map((s, i) => (
              <div key={i} className="land-stat-chip">
                <span className="land-stat-val">{s.val}</span>
                <span className="land-stat-label">{s.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Console */}
        <div className="land-hero-console">
          <TypewriterConsole />
        </div>
      </section>

      {/* Features */}
      <section className="land-features-section">
        <div className="land-section-label">CAPABILITIES</div>
        <h2 className="land-section-title">Everything you need for predictive maintenance</h2>
        <div className="land-features-grid">
          {FEATURES.map((f, i) => (
            <div key={i} className="land-feature-card">
              <div className="land-feature-icon">{f.icon}</div>
              <div className="land-feature-label">{f.label}</div>
              <div className="land-feature-desc">{f.desc}</div>
            </div>
          ))}
        </div>
      </section>

      {/* CTA band */}
      <section className="land-cta-band">
        <div className="land-cta-band-inner">
          <div>
            <h2 className="land-cta-band-title">Ready to run diagnostics?</h2>
            <p className="land-cta-band-sub">Sign in with your authorised credentials to access the telemetry studio.</p>
          </div>
          <button className="land-cta-primary" onClick={onNavigateLogin} style={{ whiteSpace: 'nowrap' }}>
            Sign In <ArrowRight size={14} />
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="land-footer">
        <div className="land-footer-inner">
          <span className="brand-tagline">pms://telemetry · Predictive Maintenance System</span>
          <span className="brand-tagline">Calibrated XGBoost · SHAP · Drift Radar · MLflow</span>
        </div>
      </footer>
    </div>
  );
}
