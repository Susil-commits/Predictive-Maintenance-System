import React, { useState, useEffect } from 'react';
import { Terminal, Eye, EyeOff, AlertTriangle, Shield, ArrowLeft, Wifi } from 'lucide-react';
import { login } from '../auth';

const BOOT_LINES = [
  'Establishing secure channel...',
  'Verifying endpoint certificates...',
  'Connecting to PMS inference core...',
];

function MiniBootSequence({ onDone }) {
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (step >= BOOT_LINES.length) { onDone(); return; }
    const t = setTimeout(() => setStep(s => s + 1), 500);
    return () => clearTimeout(t);
  }, [step, onDone]);

  return (
    <div className="login-boot">
      {BOOT_LINES.slice(0, step).map((l, i) => (
        <div key={i} className="login-boot-line">
          <span className="land-prompt">$</span>
          <span className="land-cmd">{l}</span>
          <span className="land-ok" style={{ marginLeft: 8 }}>[OK]</span>
        </div>
      ))}
      {step < BOOT_LINES.length && (
        <div className="login-boot-line">
          <span className="land-prompt">$</span>
          <span className="land-cmd">{BOOT_LINES[step]}</span>
          <span className="terminal-cursor" />
        </div>
      )}
    </div>
  );
}

export default function LoginPage({ onLoginSuccess, onBack }) {
  const [ready, setReady] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPwd, setShowPwd] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isIntruder, setIsIntruder] = useState(false);
  const [shake, setShake] = useState(false);
  const [attempts, setAttempts] = useState(0);

  const triggerShake = () => {
    setShake(true);
    setTimeout(() => setShake(false), 600);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!username.trim() || !password) return;
    setLoading(true);
    setError(null);
    setIsIntruder(false);

    // Simulate slight network delay for realism
    await new Promise(r => setTimeout(r, 600));

    const result = await login(username.trim(), password);
    setLoading(false);

    if (result.ok) {
      onLoginSuccess(result.session);
    } else {
      setAttempts(a => a + 1);
      triggerShake();
      setError(result.error);
      setIsIntruder(!!result.intruder);
    }
  };

  return (
    <div className="login-root">
      <div className="login-bg-grid" />
      <div className="login-bg-glow" />

      {/* Back to landing */}
      <button className="login-back-btn" onClick={onBack}>
        <ArrowLeft size={14} /> Back
      </button>

      <div className={`login-card ${shake ? 'login-shake' : ''} ${isIntruder ? 'login-card-intruder' : ''}`}>
        {/* Header */}
        <div className="login-card-header">
          <div className="brand-icon" style={{ width: 44, height: 44 }}>
            <Terminal size={22} />
          </div>
          <div>
            <div className="login-card-title">pms://auth</div>
            <div className="login-card-sub">Predictive Maintenance System</div>
          </div>
        </div>

        {/* Boot sequence */}
        {!ready && <MiniBootSequence onDone={() => setReady(true)} />}

        {ready && (
          <>
            {/* Intruder Alert */}
            {isIntruder && (
              <div className="login-intruder-alert">
                <div className="login-intruder-header">
                  <AlertTriangle size={18} className="login-intruder-icon" />
                  <span>INTRUSION DETECTED</span>
                </div>
                <p className="login-intruder-body">
                  Your credentials do not match any registered user in this system.
                  This access attempt has been logged.
                </p>
                <p className="login-intruder-body" style={{ marginTop: 6, color: '#fbbf24', fontWeight: 600 }}>
                  You are not authorised. Contact the Administrator for access.
                </p>
                <div className="login-intruder-meta">
                  <Shield size={11} /> Attempt #{attempts} logged · {new Date().toLocaleTimeString()}
                </div>
              </div>
            )}

            {/* Regular error */}
            {error && !isIntruder && (
              <div className="login-error-msg">
                <AlertTriangle size={13} />
                <span>{error}</span>
              </div>
            )}

            {/* Form */}
            <form onSubmit={handleSubmit} className="login-form">
              <div className="login-field-group">
                <label className="login-label" htmlFor="login-username">Username</label>
                <div className="login-input-wrap">
                  <span className="login-input-prefix">
                    <Wifi size={13} />
                  </span>
                  <input
                    id="login-username"
                    type="text"
                    autoComplete="username"
                    value={username}
                    onChange={e => setUsername(e.target.value)}
                    placeholder="Enter your username"
                    className="login-input"
                    required
                    disabled={loading}
                    autoFocus
                  />
                </div>
              </div>

              <div className="login-field-group">
                <label className="login-label" htmlFor="login-password">Password</label>
                <div className="login-input-wrap">
                  <span className="login-input-prefix">
                    <Shield size={13} />
                  </span>
                  <input
                    id="login-password"
                    type={showPwd ? 'text' : 'password'}
                    autoComplete="current-password"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    placeholder="Enter your password"
                    className="login-input"
                    required
                    disabled={loading}
                  />
                  <button
                    type="button"
                    className="login-eye-btn"
                    onClick={() => setShowPwd(v => !v)}
                    tabIndex={-1}
                  >
                    {showPwd ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                className="submit-btn"
                disabled={loading || !username.trim() || !password}
                style={{ marginTop: 8 }}
              >
                {loading ? (
                  <>
                    <span className="spinner" style={{ borderColor: '#333', borderTopColor: '#000' }} />
                    <span>AUTHENTICATING...</span>
                  </>
                ) : (
                  <>
                    <Terminal size={15} />
                    <span>SIGN IN</span>
                  </>
                )}
              </button>
            </form>

            <div className="login-footer-note">
              <Shield size={11} />
              <span>Restricted access. All login attempts are logged and monitored.</span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
