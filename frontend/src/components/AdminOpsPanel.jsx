import React, { useState, useEffect, useCallback } from 'react';
import {
  ShieldCheck,
  Cpu,
  GitBranch,
  CalendarClock,
  RefreshCw,
  Play,
  Check,
  X,
  Zap,
  Lock,
  Loader2,
  AlertTriangle,
  Database,
} from 'lucide-react';
import {
  getInferenceBenchmark,
  getCanaryStatus,
  startCanaryRollout,
  promoteCanaryModel,
  abortCanaryRollout,
  getSchedulerJobs,
  runScheduledDriftCheck,
  getSecurityTelemetry,
  getSecurityAuditTrail,
  verifyAuditChain,
  getFeedbackMetrics,
  exportFeedbackDataset,
} from '../api';

export default function AdminOpsPanel() {
  const [benchmark, setBenchmark] = useState(null);
  const [benchLoading, setBenchLoading] = useState(false);

  const [canary, setCanary] = useState(null);
  const [canaryBusy, setCanaryBusy] = useState(false);

  const [scheduler, setScheduler] = useState(null);
  const [schedBusy, setSchedBusy] = useState(false);

  const [security, setSecurity] = useState(null);
  const [auditEvents, setAuditEvents] = useState([]);
  const [chainValid, setChainValid] = useState(null);
  const [chainError, setChainError] = useState(null);
  const [feedbackMetrics, setFeedbackMetrics] = useState(null);
  const [exportStatus, setExportStatus] = useState('');
  const [exportBusy, setExportBusy] = useState(false);
  const [opsError, setOpsError] = useState('');
  const [loadingAll, setLoadingAll] = useState(true);

  const loadAllOps = useCallback(async (showSpinner = true) => {
    if (showSpinner) setLoadingAll(true);
    setOpsError('');
    try {
      const [canaryRes, schedRes, secRes, auditRes, fbRes] = await Promise.all([
        getCanaryStatus().catch(() => null),
        getSchedulerJobs().catch(() => null),
        getSecurityTelemetry().catch(() => null),
        getSecurityAuditTrail().catch(() => null),
        getFeedbackMetrics().catch(() => null),
      ]);
      if (canaryRes) setCanary(canaryRes);
      if (schedRes) setScheduler(schedRes);
      if (secRes) setSecurity(secRes);
      if (auditRes) {
        setAuditEvents(auditRes.events || []);
        setChainValid(auditRes.chain_verified);
      }
      if (fbRes) setFeedbackMetrics(fbRes);
    } catch (err) {
      setOpsError(err?.message || 'Failed to load MLOps & Security telemetry');
    } finally {
      setLoadingAll(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    Promise.resolve().then(() => {
      if (active) loadAllOps(false);
    });
    return () => { active = false; };
  }, [loadAllOps]);

  const handleRunBenchmark = async () => {
    setBenchLoading(true);
    setOpsError('');
    try {
      const res = await getInferenceBenchmark(100);
      setBenchmark(res);
    } catch (err) {
      setOpsError(err?.response?.data?.detail || err.message || 'Benchmark failed');
    } finally {
      setBenchLoading(false);
    }
  };

  const handleCanaryAction = async (actionFn) => {
    setCanaryBusy(true);
    setOpsError('');
    try {
      await actionFn();
      const updated = await getCanaryStatus();
      setCanary(updated);
    } catch (err) {
      setOpsError(err?.response?.data?.detail || err.message || 'Canary operation failed');
    } finally {
      setCanaryBusy(false);
    }
  };

  const handleRunDriftCheck = async () => {
    setSchedBusy(true);
    setOpsError('');
    try {
      await runScheduledDriftCheck();
      const updated = await getSchedulerJobs();
      setScheduler(updated);
    } catch (err) {
      setOpsError(err?.response?.data?.detail || err.message || 'Drift check failed');
    } finally {
      setSchedBusy(false);
    }
  };

  const handleVerifyChain = async () => {
    setOpsError('');
    try {
      const res = await verifyAuditChain();
      setChainValid(res.is_valid);
      setChainError(res.error || null);
      const trail = await getSecurityAuditTrail().catch(() => null);
      if (trail) setAuditEvents(trail.events || []);
    } catch (err) {
      setOpsError(err?.response?.data?.detail || err.message || 'Chain verification failed');
    }
  };

  const handleExportFeedback = async () => {
    setExportBusy(true);
    setOpsError('');
    setExportStatus('');
    try {
      const res = await exportFeedbackDataset();
      setExportStatus(`Exported ${res.exported_samples} labeled samples (${res.confirmed_faults} faults, ${res.false_alarms} false alarms).`);
    } catch (err) {
      setOpsError(err?.response?.data?.detail || err.message || 'Feedback export failed');
    } finally {
      setExportBusy(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20, marginBottom: 20 }}>
      {opsError && (
        <div className="notification-banner">
          <span>{opsError}</span>
          <button type="button" onClick={() => setOpsError('')} className="preset-btn" style={{ padding: '2px 8px', fontSize: '0.68rem' }}>
            Dismiss
          </button>
        </div>
      )}

      {/* Multi-Runtime ONNX vs XGBoost Benchmark + Canary Rollout + Scheduler */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 20 }}>
        {/* Inference Benchmark */}
        <div className="glass-panel">
          <div className="panel-header">
            <h2 className="panel-title">
              <Cpu size={17} className="panel-icon" />
              <span>Multi-Runtime Benchmark</span>
            </h2>
            <button
              type="button"
              className="preset-btn highlight"
              onClick={handleRunBenchmark}
              disabled={benchLoading}
              style={{ padding: '4px 10px', fontSize: '0.7rem', gap: 5 }}
            >
              {benchLoading ? <Loader2 size={11} className="batch-spin" /> : <Zap size={11} />}
              <span>{benchLoading ? 'Benchmarking...' : 'Run 100-Iter Test'}</span>
            </button>
          </div>

          {!benchmark ? (
            <div className="empty-state" style={{ padding: '18px 10px' }}>
              Compare C++ ONNX Runtime vs. Python XGBoost latency &amp; throughput on live server hardware.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 10px', background: 'rgba(56,189,248,0.06)', borderRadius: 6, border: '1px solid rgba(56,189,248,0.2)' }}>
                <span style={{ color: '#94a3b8' }}>ONNX Speedup</span>
                <strong style={{ color: '#38bdf8' }}>{benchmark.speedup_factor}x faster</strong>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                <div style={{ padding: '8px 10px', background: 'rgba(255,255,255,0.02)', borderRadius: 6, border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.66rem', color: 'var(--text-dim)' }}>ONNX RUNTIME</div>
                  <div style={{ color: '#34d399', fontWeight: 700, marginTop: 2 }}>
                    {benchmark.onnx?.mean_latency_ms != null ? `${benchmark.onnx.mean_latency_ms} ms` : 'N/A'}
                  </div>
                  <div style={{ fontSize: '0.66rem', color: 'var(--text-dim)', marginTop: 2 }}>
                    P95: {benchmark.onnx?.p95_latency_ms ?? '—'} ms · {benchmark.onnx?.throughput_req_sec ?? '—'} req/s
                  </div>
                </div>
                <div style={{ padding: '8px 10px', background: 'rgba(255,255,255,0.02)', borderRadius: 6, border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.66rem', color: 'var(--text-dim)' }}>XGBOOST + SHAP</div>
                  <div style={{ color: '#ffffff', fontWeight: 700, marginTop: 2 }}>
                    {benchmark.xgboost?.mean_latency_ms} ms
                  </div>
                  <div style={{ fontSize: '0.66rem', color: 'var(--text-dim)', marginTop: 2 }}>
                    P95: {benchmark.xgboost?.p95_latency_ms} ms · {benchmark.xgboost?.throughput_req_sec} req/s
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Canary Rollout Controller */}
        <div className="glass-panel">
          <div className="panel-header">
            <h2 className="panel-title">
              <GitBranch size={17} className="panel-icon" />
              <span>Canary Rollout</span>
            </h2>
            <span className={`badge-risk ${canary?.is_active ? 'high' : 'low'}`} style={{ fontSize: '0.65rem' }}>
              {canary?.is_active ? 'SHADOW ACTIVE' : 'STANDBY'}
            </span>
          </div>

          {canary ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontFamily: 'var(--font-mono)', fontSize: '0.73rem' }}>
                <div style={{ padding: '7px 10px', background: 'rgba(255,255,255,0.02)', borderRadius: 6, border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.64rem', color: 'var(--text-dim)' }}>PRIMARY / CANDIDATE</div>
                  <div style={{ color: '#fff', fontWeight: 700 }}>{canary.primary_version} → {canary.canary_version}</div>
                </div>
                <div style={{ padding: '7px 10px', background: 'rgba(255,255,255,0.02)', borderRadius: 6, border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.64rem', color: 'var(--text-dim)' }}>AGREEMENT / PROGRESS</div>
                  <div style={{ color: '#34d399', fontWeight: 700 }}>
                    {(canary.agreement_rate * 100).toFixed(1)}% ({canary.evaluated_requests}/{canary.evaluated_requests + canary.remaining_requests})
                  </div>
                </div>
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {!canary.is_active ? (
                  <button
                    type="button"
                    className="preset-btn highlight"
                    disabled={canaryBusy}
                    onClick={() => handleCanaryAction(startCanaryRollout)}
                    style={{ padding: '4px 10px', fontSize: '0.7rem', gap: 5 }}
                  >
                    <Play size={11} /> Start 50-Req Shadow
                  </button>
                ) : (
                  <>
                    <button
                      type="button"
                      className="preset-btn highlight"
                      disabled={canaryBusy}
                      onClick={() => handleCanaryAction(promoteCanaryModel)}
                      style={{ padding: '4px 10px', fontSize: '0.7rem', gap: 5, color: '#34d399', borderColor: 'rgba(52,211,153,0.4)' }}
                    >
                      <Check size={11} /> Promote Candidate
                    </button>
                    <button
                      type="button"
                      className="preset-btn"
                      disabled={canaryBusy}
                      onClick={() => handleCanaryAction(abortCanaryRollout)}
                      style={{ padding: '4px 10px', fontSize: '0.7rem', gap: 5, color: '#fda4af', borderColor: 'rgba(244,63,94,0.35)' }}
                    >
                      <X size={11} /> Abort
                    </button>
                  </>
                )}
              </div>
            </div>
          ) : (
            <div className="empty-state" style={{ padding: '18px 10px' }}>
              {loadingAll ? 'Loading canary state...' : 'Canary telemetry unavailable.'}
            </div>
          )}
        </div>

        {/* MLOps Drift Scheduler */}
        <div className="glass-panel">
          <div className="panel-header">
            <h2 className="panel-title">
              <CalendarClock size={17} className="panel-icon" />
              <span>Drift Scheduler</span>
            </h2>
            <button
              type="button"
              className="preset-btn highlight"
              onClick={handleRunDriftCheck}
              disabled={schedBusy}
              style={{ padding: '4px 10px', fontSize: '0.7rem', gap: 5 }}
            >
              {schedBusy ? <Loader2 size={11} className="batch-spin" /> : <RefreshCw size={11} />}
              <span>Run Drift Check</span>
            </button>
          </div>

          {scheduler ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontFamily: 'var(--font-mono)', fontSize: '0.73rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 10px', background: 'rgba(255,255,255,0.02)', borderRadius: 6, border: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-dim)' }}>Max PSI</span>
                <strong style={{ color: scheduler.drift_detected ? '#fb7185' : '#34d399' }}>
                  {Number(scheduler.max_psi || 0).toFixed(4)} ({scheduler.drift_detected ? 'DRIFT' : 'NOMINAL'})
                </strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 10px', background: 'rgba(255,255,255,0.02)', borderRadius: 6, border: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-dim)' }}>Last Check</span>
                <span style={{ color: '#e4e4e7' }}>
                  {scheduler.last_check_timestamp ? new Date(scheduler.last_check_timestamp).toLocaleString() : 'Never'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 10px', background: 'rgba(255,255,255,0.02)', borderRadius: 6, border: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-dim)' }}>Active Jobs</span>
                <span style={{ color: '#38bdf8' }}>{scheduler.active_jobs?.length || 0} scheduled</span>
              </div>
            </div>
          ) : (
            <div className="empty-state" style={{ padding: '18px 10px' }}>
              {loadingAll ? 'Loading scheduler...' : 'Scheduler status unavailable.'}
            </div>
          )}
        </div>

        {/* Closed-Loop Active Learning & Live Precision */}
        <div className="glass-panel">
          <div className="panel-header">
            <h2 className="panel-title">
              <Database size={17} className="panel-icon" />
              <span>Active Learning Feedback</span>
            </h2>
            <button
              type="button"
              className="preset-btn highlight"
              onClick={handleExportFeedback}
              disabled={exportBusy}
              style={{ padding: '4px 10px', fontSize: '0.7rem', gap: 5 }}
            >
              {exportBusy ? <Loader2 size={11} className="batch-spin" /> : <Zap size={11} />}
              <span>Export Feedback CSV</span>
            </button>
          </div>

          {feedbackMetrics ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontFamily: 'var(--font-mono)', fontSize: '0.73rem' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                <div style={{ padding: '7px 10px', background: 'rgba(255,255,255,0.02)', borderRadius: 6, border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.64rem', color: 'var(--text-dim)' }}>LIVE PRECISION</div>
                  <div style={{ color: '#34d399', fontWeight: 700 }}>
                    {feedbackMetrics.production_precision != null ? `${(feedbackMetrics.production_precision * 100).toFixed(1)}%` : 'Pending'}
                  </div>
                </div>
                <div style={{ padding: '7px 10px', background: 'rgba(255,255,255,0.02)', borderRadius: 6, border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.64rem', color: 'var(--text-dim)' }}>FALSE ALARM RATE</div>
                  <div style={{ color: '#fb7185', fontWeight: 700 }}>
                    {feedbackMetrics.false_alarm_rate != null ? `${(feedbackMetrics.false_alarm_rate * 100).toFixed(1)}%` : 'Pending'}
                  </div>
                </div>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 10px', background: 'rgba(255,255,255,0.02)', borderRadius: 6, border: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-dim)' }}>Resolved Labels</span>
                <span style={{ color: '#e4e4e7' }}>
                  {feedbackMetrics.resolved_with_feedback} ({feedbackMetrics.confirmed_faults} faults · {feedbackMetrics.false_alarms} nominal)
                </span>
              </div>
              {exportStatus && (
                <div style={{ fontSize: '0.7rem', color: '#34d399' }}>{exportStatus}</div>
              )}
            </div>
          ) : (
            <div className="empty-state" style={{ padding: '18px 10px' }}>
              {loadingAll ? 'Loading feedback metrics...' : 'Feedback telemetry unavailable.'}
            </div>
          )}
        </div>
      </div>

      {/* Enterprise Security, Circuit Breakers & SHA-256 Audit Chain */}
      <div className="glass-panel">
        <div className="panel-header">
          <h2 className="panel-title">
            <ShieldCheck size={18} className="panel-icon" />
            <span>Enterprise AI Security &amp; Tamper-Evident Audit Chain</span>
          </h2>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            {chainValid !== null && (
              <span className={`badge-risk ${chainValid ? 'low' : 'high'}`} style={{ fontSize: '0.66rem' }}>
                {chainValid ? 'SHA-256 CHAIN VERIFIED' : 'CHAIN TAMPER ALERT'}
              </span>
            )}
            <button
              type="button"
              className="preset-btn highlight"
              onClick={handleVerifyChain}
              style={{ padding: '4px 10px', fontSize: '0.7rem', gap: 5 }}
            >
              <Lock size={11} /> Verify Hash Chain
            </button>
            <button
              type="button"
              className="preset-btn"
              onClick={() => loadAllOps(true)}
              style={{ padding: '4px 10px', fontSize: '0.7rem', gap: 5 }}
            >
              <RefreshCw size={11} /> Refresh
            </button>
          </div>
        </div>

        {chainError && (
          <div className="action-alert danger" style={{ marginBottom: 12 }}>
            <AlertTriangle size={15} />
            <span>{chainError}</span>
          </div>
        )}

        {security && (
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 14 }}>
            {[
              { label: 'Guardrails', on: security.guardrails_active },
              { label: 'Anti-Prompt-Injection', on: security.anti_prompt_injection },
              { label: 'Canary Honeytokens', on: security.canary_traps_enabled },
              { label: 'PII Redaction', on: security.pii_redaction_enabled },
            ].map((item) => (
              <span
                key={item.label}
                className="field-unit"
                style={{
                  color: item.on ? '#34d399' : '#fda4af',
                  borderColor: item.on ? 'rgba(52,211,153,0.3)' : 'rgba(244,63,94,0.3)',
                  background: item.on ? 'rgba(52,211,153,0.06)' : 'rgba(244,63,94,0.06)',
                }}
              >
                {item.label}: {item.on ? 'ACTIVE' : 'OFF'}
              </span>
            ))}
            {(security.circuit_breakers || []).map((cb) => (
              <span
                key={cb.provider}
                className="field-unit"
                style={{
                  color: cb.state === 'CLOSED' ? '#38bdf8' : '#f59e0b',
                  borderColor: 'rgba(56,189,248,0.28)',
                  background: 'rgba(56,189,248,0.06)',
                }}
              >
                CB[{cb.provider}]: {cb.state}
              </span>
            ))}
          </div>
        )}

        {auditEvents.length === 0 ? (
          <div className="empty-state" style={{ padding: '16px 10px' }}>
            No cryptographic audit events recorded in the active session yet.
          </div>
        ) : (
          <div className="table-responsive">
            <table className="history-table">
              <thead>
                <tr>
                  <th>Idx</th>
                  <th>Timestamp</th>
                  <th>Event Type</th>
                  <th>Actor</th>
                  <th>Status</th>
                  <th>SHA-256 Event Hash</th>
                </tr>
              </thead>
              <tbody>
                {auditEvents.slice(0, 15).map((ev) => (
                  <tr key={`${ev.index}-${ev.event_hash}`}>
                    <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>#{ev.index}</td>
                    <td style={{ color: 'var(--text-dim)' }}>{new Date(ev.timestamp * 1000).toLocaleString()}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.73rem', color: '#ffffff' }}>{ev.event_type}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.73rem', color: '#38bdf8' }}>{ev.actor_id}</td>
                    <td>
                      <span className={`badge-risk ${ev.status === 'SUCCESS' ? 'low' : 'high'}`}>
                        {ev.status}
                      </span>
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                      {ev.event_hash?.slice(0, 20)}...
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
