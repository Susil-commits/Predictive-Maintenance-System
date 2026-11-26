import React, { useState } from 'react';
import { Wrench, CheckCircle2, Play, RefreshCw, AlertTriangle } from 'lucide-react';
import { updateWorkOrderStatus } from '../api';

export default function WorkOrdersPanel({ workOrders = [], selectedAsset = null, onRefresh }) {
  const [busyId, setBusyId] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');

  const handleTransition = async (workOrderId, nextStatus, failureConfirmed = null) => {
    setBusyId(workOrderId);
    setErrorMsg('');
    try {
      const payload = { status: nextStatus };
      if (failureConfirmed !== null) {
        payload.actual_failure_confirmed = failureConfirmed;
        payload.resolution_notes = failureConfirmed
          ? 'Technician confirmed physical degradation during inspection.'
          : 'Inspection completed — false alarm / nominal hardware condition.';
      }
      await updateWorkOrderStatus(workOrderId, payload);
      if (onRefresh) await onRefresh();
    } catch (err) {
      setErrorMsg(err?.response?.data?.detail || err.message || 'Failed to update work order');
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="glass-panel" style={{ marginTop: 16 }}>
      <div className="panel-header">
        <h2 className="panel-title">
          <Wrench size={18} className="panel-icon" />
          <span>CMMS Work Orders &amp; Ground-Truth Feedback</span>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontWeight: 400, fontFamily: 'var(--font-mono)' }}>
            [{workOrders.length} orders{selectedAsset ? ` · ${selectedAsset}` : ''}]
          </span>
        </h2>
        {onRefresh && (
          <button
            type="button"
            className="preset-btn"
            onClick={onRefresh}
            style={{ padding: '4px 9px', fontSize: '0.7rem', gap: 5 }}
          >
            <RefreshCw size={11} />
            <span>Sync Orders</span>
          </button>
        )}
      </div>

      {errorMsg && (
        <div className="notification-banner" style={{ marginBottom: 10 }}>
          <span>{errorMsg}</span>
          <button type="button" onClick={() => setErrorMsg('')} className="preset-btn" style={{ padding: '2px 8px', fontSize: '0.68rem' }}>
            Dismiss
          </button>
        </div>
      )}

      {workOrders.length === 0 ? (
        <div className="empty-state" style={{ padding: '18px 12px' }}>
          No CMMS work orders dispatched yet. Run a prediction and click <strong style={{ color: '#fff' }}>Dispatch SAP PM Work Order</strong>.
        </div>
      ) : (
        <div className="table-responsive">
          <table className="history-table">
            <thead>
              <tr>
                <th>Work Order</th>
                <th>Asset</th>
                <th>Failure Mode</th>
                <th>Priority</th>
                <th>Status</th>
                <th>Ground Truth</th>
                <th>Lifecycle Actions</th>
              </tr>
            </thead>
            <tbody>
              {workOrders.map((wo) => {
                const isResolved = wo.status === 'RESOLVED';
                const isInProgress = wo.status === 'IN_PROGRESS';
                const isBusy = busyId === wo.work_order_id;
                return (
                  <tr key={wo.work_order_id}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.73rem', color: '#ffffff', fontWeight: 600 }}>
                      {wo.work_order_id}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: '#38bdf8' }}>
                      {wo.asset_id}
                    </td>
                    <td style={{ fontSize: '0.75rem' }}>{wo.failure_mode || '—'}</td>
                    <td>
                      <span className={`badge-risk ${wo.priority === 'CRITICAL' || wo.priority === 'HIGH' ? 'high' : 'low'}`}>
                        {wo.priority || 'HIGH'}
                      </span>
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.71rem', color: isResolved ? '#34d399' : isInProgress ? '#fbbf24' : '#e4e4e7' }}>
                      {wo.status}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.71rem' }}>
                      {wo.actual_failure_confirmed === true ? (
                        <span style={{ color: '#fb7185', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                          <AlertTriangle size={11} /> Confirmed Fault
                        </span>
                      ) : wo.actual_failure_confirmed === false ? (
                        <span style={{ color: '#34d399', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                          <CheckCircle2 size={11} /> False Alarm
                        </span>
                      ) : (
                        <span style={{ color: 'var(--text-dim)' }}>Pending</span>
                      )}
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                        {!isInProgress && !isResolved && (
                          <button
                            type="button"
                            className="preset-btn"
                            disabled={isBusy}
                            onClick={() => handleTransition(wo.work_order_id, 'IN_PROGRESS')}
                            style={{ padding: '3px 8px', fontSize: '0.68rem', gap: 4 }}
                          >
                            <Play size={10} /> Start
                          </button>
                        )}
                        {!isResolved && (
                          <>
                            <button
                              type="button"
                              className="preset-btn highlight"
                              disabled={isBusy}
                              onClick={() => handleTransition(wo.work_order_id, 'RESOLVED', true)}
                              style={{ padding: '3px 8px', fontSize: '0.68rem', color: '#fb7185', borderColor: 'rgba(244,63,94,0.35)' }}
                            >
                              Resolve (Fault)
                            </button>
                            <button
                              type="button"
                              className="preset-btn"
                              disabled={isBusy}
                              onClick={() => handleTransition(wo.work_order_id, 'RESOLVED', false)}
                              style={{ padding: '3px 8px', fontSize: '0.68rem', color: '#34d399', borderColor: 'rgba(52,211,153,0.35)' }}
                            >
                              Resolve (Nominal)
                            </button>
                          </>
                        )}
                        {isResolved && (
                          <span style={{ fontSize: '0.68rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                            Closed
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
