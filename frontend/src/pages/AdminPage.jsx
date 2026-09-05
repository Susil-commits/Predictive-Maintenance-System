import React, { useState, useEffect } from 'react';
import {
  Terminal, Users, Plus, Trash2, Shield, LogOut,
  Eye, EyeOff, Check, AlertCircle, Clock, User, Activity
} from 'lucide-react';
import { getUsers, addUser, deleteUser, getSession, logout, getAccessLog } from '../auth';

function StatChip({ label, value, color }) {
  return (
    <div className="admin-stat-chip">
      <span className="admin-stat-val" style={{ color }}>{value}</span>
      <span className="admin-stat-label">{label}</span>
    </div>
  );
}

function AccessLogPanel() {
  const log = getAccessLog().slice(0, 30);
  return (
    <div className="glass-panel" style={{ marginTop: 20 }}>
      <div className="panel-header">
        <h2 className="panel-title">
          <Activity size={17} className="panel-icon" />
          <span>Access Log</span>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontWeight: 400, fontFamily: 'var(--font-mono)' }}>
            [{log.length} events]
          </span>
        </h2>
      </div>
      {log.length === 0 ? (
        <div className="empty-state">No access events recorded yet.</div>
      ) : (
        <div className="table-responsive">
          <table className="history-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Name</th>
                <th>Username</th>
                <th>Role</th>
                <th>Event</th>
              </tr>
            </thead>
            <tbody>
              {log.map((entry, i) => (
                <tr key={i}>
                  <td style={{ color: 'var(--text-dim)' }}>
                    {new Date(entry.loginAt || entry.accessedAt).toLocaleString()}
                  </td>
                  <td style={{ color: '#ffffff' }}>{entry.name}</td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.74rem' }}>{entry.username}</td>
                  <td>
                    <span className="badge-risk" style={entry.role === 'admin'
                      ? { background: 'rgba(255,255,255,0.08)', color: '#fff', border: '1px solid rgba(255,255,255,0.2)' }
                      : { background: 'rgba(16,185,129,0.1)', color: '#34d399', border: '1px solid rgba(16,185,129,0.25)' }
                    }>
                      {entry.role?.toUpperCase()}
                    </span>
                  </td>
                  <td style={{ color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', fontSize: '0.72rem' }}>
                    {entry.page || 'login'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function AdminPage({ onLogout }) {
  const session = getSession();
  const [users, setUsers] = useState(getUsers());
  const [showAddForm, setShowAddForm] = useState(false);
  const [name, setName] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPwd, setShowPwd] = useState(false);
  const [addError, setAddError] = useState('');
  const [addSuccess, setAddSuccess] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState(null);

  const refreshUsers = () => setUsers(getUsers());

  const handleAddUser = (e) => {
    e.preventDefault();
    setAddError('');
    setAddSuccess('');
    if (!name.trim() || !username.trim() || !password) {
      setAddError('All fields are required.');
      return;
    }
    try {
      addUser({ name, username, password });
      setAddSuccess(`User "${name}" added successfully.`);
      setName(''); setUsername(''); setPassword('');
      refreshUsers();
      setTimeout(() => { setAddSuccess(''); setShowAddForm(false); }, 2000);
    } catch (err) {
      setAddError(err.message);
    }
  };

  const handleDelete = (userId, userName) => {
    if (deleteConfirm === userId) {
      deleteUser(userId);
      refreshUsers();
      setDeleteConfirm(null);
    } else {
      setDeleteConfirm(userId);
      setTimeout(() => setDeleteConfirm(null), 3000);
    }
  };

  const handleLogout = () => {
    logout();
    onLogout();
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="brand-wrapper">
          <div className="brand-icon"><Terminal size={20} /></div>
          <div className="brand-title-group">
            <h1 className="brand-title">
              <span>pms://admin</span>
              <span style={{ color: 'var(--text-dim)', fontWeight: 400 }}>//</span>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', fontWeight: 500 }}>control-panel</span>
            </h1>
            <p className="brand-tagline">Administrator · User Management · Access Logs</p>
          </div>
        </div>
        <div className="header-status">
          <div className="model-badge">
            <Shield size={13} />
            <span>{session?.name}</span>
          </div>
          <div className="status-chip" style={{ color: '#ffffff' }}>
            <span className="status-dot" style={{ background: '#10b981', color: '#10b981' }} />
            <span>ADMIN</span>
          </div>
          <button
            type="button"
            className="preset-btn"
            onClick={handleLogout}
            style={{ padding: '6px 12px', gap: 6 }}
          >
            <LogOut size={13} /> Sign Out
          </button>
        </div>
      </header>

      {/* Stats */}
      <div className="admin-stats-bar">
        <StatChip label="Registered Users" value={users.length} color="#ffffff" />
        <StatChip label="Admin Accounts" value={1} color="var(--text-secondary)" />
        <StatChip label="Access Events" value={getAccessLog().length} color="var(--text-secondary)" />
        <StatChip label="System Status" value="LIVE" color="#10b981" />
      </div>

      {/* User Management Panel */}
      <div className="glass-panel" style={{ marginBottom: 20 }}>
        <div className="panel-header">
          <h2 className="panel-title">
            <Users size={18} className="panel-icon" />
            <span>Registered Employees</span>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontWeight: 400, fontFamily: 'var(--font-mono)' }}>
              [{users.length} users]
            </span>
          </h2>
          <button
            type="button"
            className={`preset-btn ${showAddForm ? '' : 'highlight'}`}
            onClick={() => { setShowAddForm(v => !v); setAddError(''); setAddSuccess(''); }}
            style={{ padding: '6px 14px', gap: 6 }}
          >
            <Plus size={13} />
            {showAddForm ? 'Cancel' : 'Add Employee'}
          </button>
        </div>

        {/* Add User Form */}
        {showAddForm && (
          <div className="admin-add-form">
            <div className="admin-add-form-title">Add New Employee</div>
            {addError && (
              <div className="login-error-msg" style={{ marginBottom: 12 }}>
                <AlertCircle size={13} /> {addError}
              </div>
            )}
            {addSuccess && (
              <div className="action-alert safe" style={{ marginBottom: 12, gap: 8 }}>
                <Check size={13} /> {addSuccess}
              </div>
            )}
            <form onSubmit={handleAddUser} className="admin-form-grid">
              <div className="login-field-group">
                <label className="login-label">Full Name</label>
                <div className="login-input-wrap">
                  <span className="login-input-prefix"><User size={13} /></span>
                  <input
                    type="text"
                    value={name}
                    onChange={e => setName(e.target.value)}
                    placeholder="e.g. John Doe"
                    className="login-input"
                    required
                  />
                </div>
              </div>
              <div className="login-field-group">
                <label className="login-label">Username</label>
                <div className="login-input-wrap">
                  <span className="login-input-prefix"><Terminal size={13} /></span>
                  <input
                    type="text"
                    value={username}
                    onChange={e => setUsername(e.target.value)}
                    placeholder="e.g. emp001"
                    className="login-input"
                    required
                  />
                </div>
              </div>
              <div className="login-field-group">
                <label className="login-label">Password</label>
                <div className="login-input-wrap">
                  <span className="login-input-prefix"><Shield size={13} /></span>
                  <input
                    type={showPwd ? 'text' : 'password'}
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    placeholder="Set password"
                    className="login-input"
                    required
                  />
                  <button type="button" className="login-eye-btn" onClick={() => setShowPwd(v => !v)} tabIndex={-1}>
                    {showPwd ? <EyeOff size={13} /> : <Eye size={13} />}
                  </button>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'flex-end' }}>
                <button type="submit" className="submit-btn" style={{ height: '42px', padding: '0 20px' }}>
                  <Plus size={14} /> Add Employee
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Users Table */}
        {users.length === 0 ? (
          <div className="empty-state">
            <p>No employees registered yet. Use the button above to add your first employee.</p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="history-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Username</th>
                  <th>Role</th>
                  <th>Created At</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {/* Admin row (always show) */}
                <tr>
                  <td style={{ color: '#ffffff', fontWeight: 600 }}>Administrator</td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.74rem' }}>PMS123@987321</td>
                  <td>
                    <span className="badge-risk" style={{ background: 'rgba(255,255,255,0.08)', color: '#fff', border: '1px solid rgba(255,255,255,0.2)' }}>
                      ADMIN
                    </span>
                  </td>
                  <td style={{ color: 'var(--text-dim)' }}>System default</td>
                  <td><span style={{ color: 'var(--text-muted)', fontSize: '0.72rem', fontFamily: 'var(--font-mono)' }}>protected</span></td>
                </tr>
                {users.map(u => (
                  <tr key={u.id}>
                    <td style={{ color: '#ffffff' }}>{u.name}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.74rem' }}>{u.username}</td>
                    <td>
                      <span className="badge-risk low">EMPLOYEE</span>
                    </td>
                    <td style={{ color: 'var(--text-dim)' }}>
                      {new Date(u.createdAt).toLocaleDateString()}
                    </td>
                    <td>
                      <button
                        type="button"
                        className="preset-btn"
                        onClick={() => handleDelete(u.id, u.name)}
                        style={{
                          padding: '3px 10px',
                          fontSize: '0.7rem',
                          color: deleteConfirm === u.id ? '#ffffff' : '#fda4af',
                          borderColor: deleteConfirm === u.id ? '#f43f5e' : 'rgba(244, 63, 94, 0.3)',
                          background: deleteConfirm === u.id ? 'rgba(244, 63, 94, 0.15)' : undefined,
                          gap: 5
                        }}
                      >
                        <Trash2 size={12} />
                        {deleteConfirm === u.id ? 'Confirm Delete' : 'Remove'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Access Log */}
      <AccessLogPanel />
    </div>
  );
}
