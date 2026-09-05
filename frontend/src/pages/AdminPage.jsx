import React, { useState, useRef } from 'react';
import {
  Terminal, Users, Plus, Trash2, Shield, LogOut,
  Eye, EyeOff, Check, AlertCircle, Clock, User,
  Activity, Camera, Loader2, ExternalLink, FileText,
  Filter, Layers, Cloud
} from 'lucide-react';
import {
  getUsers, addUser, deleteUser, getSession, logout,
  getAccessLog, updateUserAvatar, getAdminAvatar,
  getAllReportsGrouped, deleteReport, clearAllReports,
  clearAccessLog, deleteAvatar, syncUsersFromBackend
} from '../auth';
import { uploadAvatar, isCloudinaryConfigured } from '../cloudinary';
import ReportDetailModal from '../components/ReportDetailModal';
import { API_BASE_URL } from '../api';

// ── Avatar Component ──────────────────────────────────────────────────────────

function UserAvatar({ url, name, size = 36 }) {
  const initials = name
    ? name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
    : '??';

  if (url) {
    return (
      <img
        src={url}
        alt={name}
        style={{
          width: size, height: size, borderRadius: '50%',
          objectFit: 'cover', border: '1px solid var(--border-medium)',
          flexShrink: 0
        }}
      />
    );
  }

  return (
    <div style={{
      width: size, height: size, borderRadius: '50%',
      background: '#18181b', border: '1px solid var(--border-subtle)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontFamily: 'var(--font-mono)', fontSize: size * 0.35,
      fontWeight: 700, color: 'var(--text-secondary)', flexShrink: 0,
    }}>
      {initials}
    </div>
  );
}

function AvatarUploadBtn({ userId, currentUrl, name, onUploaded, onDeleted }) {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState('');
  const ref = useRef();

  if (!isCloudinaryConfigured()) return null;

  const handleFile = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) { setError('Images only (JPEG, PNG, WebP)'); return; }
    if (file.size > 4 * 1024 * 1024) { setError('Max 4 MB'); return; }

    setError('');
    setUploading(true);
    setProgress(0);

    try {
      const url = await uploadAvatar(file, userId, setProgress);
      updateUserAvatar(userId, url);
      onUploaded(url);
    } catch (err) {
      setError(err.message || 'Upload failed');
    } finally {
      setUploading(false);
      setProgress(0);
    }
  };

  const handleRemove = () => {
    deleteAvatar(userId);
    if (onDeleted) onDeleted();
  };

  return (
    <div style={{ position: 'relative', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
      <input ref={ref} type="file" accept="image/*" onChange={handleFile} style={{ display: 'none' }} />
      <button
        type="button"
        className="avatar-upload-btn"
        onClick={() => ref.current?.click()}
        disabled={uploading}
        title="Upload profile photo"
      >
        {uploading
          ? <><Loader2 size={11} className="batch-spin" /> {progress}%</>
          : <><Camera size={11} /> {currentUrl ? 'Change' : 'Photo'}</>}
      </button>
      {currentUrl && (
        <button
          type="button"
          className="preset-btn"
          onClick={handleRemove}
          title="Remove photo"
          style={{ padding: '3px 6px', color: '#fda4af', borderColor: 'rgba(244,63,94,0.3)', fontSize: '0.66rem' }}
        >
          <Trash2 size={10} />
        </button>
      )}
      {error && <span style={{ fontSize: '0.64rem', color: '#fb7185', marginLeft: 6 }}>{error}</span>}
    </div>
  );
}

// ── Stat chips ────────────────────────────────────────────────────────────────

function StatChip({ label, value, color }) {
  return (
    <div className="admin-stat-chip">
      <span className="admin-stat-val" style={{ color }}>{value}</span>
      <span className="admin-stat-label">{label}</span>
    </div>
  );
}

// ── Access log panel ──────────────────────────────────────────────────────────

function AccessLogPanel() {
  const [log, setLog] = useState(() => getAccessLog().slice(0, 50));
  const [confirmClear, setConfirmClear] = useState(false);

  const handleClear = () => {
    if (!confirmClear) {
      setConfirmClear(true);
      setTimeout(() => setConfirmClear(false), 3000);
      return;
    }
    clearAccessLog();
    setLog([]);
    setConfirmClear(false);
  };

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
        {log.length > 0 && (
          <button
            type="button"
            className="preset-btn"
            onClick={handleClear}
            style={{
              padding: '4px 10px', fontSize: '0.7rem', gap: 5,
              color: confirmClear ? '#ffffff' : '#fda4af',
              borderColor: confirmClear ? '#f43f5e' : 'rgba(244, 63, 94, 0.3)',
              background: confirmClear ? 'rgba(244, 63, 94, 0.2)' : undefined,
            }}
          >
            <Trash2 size={11} /> {confirmClear ? 'Confirm Clear Log?' : 'Clear Access Log'}
          </button>
        )}
      </div>
      {log.length === 0 ? (
        <div className="empty-state">No access events recorded yet.</div>
      ) : (
        <div className="table-responsive">
          <table className="history-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>User</th>
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

// ── Admin Reports Panel ───────────────────────────────────────────────────────

function AdminReportsPanel({ onSelectReport, reportsVersion, onReportDeleted }) {
  const [reports, setReports] = useState(getAllReportsGrouped);
  const [filterUser, setFilterUser] = useState('ALL');
  const [deleteConfirmId, setDeleteConfirmId] = useState(null);
  const [clearConfirm, setClearConfirm] = useState(false);

  const refresh = () => setReports(getAllReportsGrouped());

  React.useEffect(() => {
    refresh();
  }, [reportsVersion]);

  const handleDelete = (userId, reportId) => {
    if (deleteConfirmId === reportId) {
      deleteReport(userId, reportId);
      refresh();
      setDeleteConfirmId(null);
      if (onReportDeleted) onReportDeleted();
    } else {
      setDeleteConfirmId(reportId);
      setTimeout(() => setDeleteConfirmId(null), 3000);
    }
  };

  const handleClearAll = () => {
    if (!clearConfirm) {
      setClearConfirm(true);
      setTimeout(() => setClearConfirm(false), 3000);
      return;
    }
    clearAllReports();
    refresh();
    setClearConfirm(false);
    if (onReportDeleted) onReportDeleted();
  };

  const userOptions = Array.from(
    new Map(reports.map(r => [r.userId, r.userName || r.userId])).entries()
  );

  const filtered = filterUser === 'ALL'
    ? reports
    : reports.filter(r => r.userId === filterUser);

  return (
    <div className="glass-panel" style={{ marginBottom: 20 }}>
      <div className="panel-header">
        <h2 className="panel-title">
          <FileText size={18} className="panel-icon" />
          <span>Individual Generation Docs &amp; Reports</span>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontWeight: 400, fontFamily: 'var(--font-mono)' }}>
            [{filtered.length} docs{filterUser !== 'ALL' ? ` filtered` : ''}]
          </span>
        </h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {userOptions.length > 1 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <Filter size={12} style={{ color: 'var(--text-dim)' }} />
              <select
                value={filterUser}
                onChange={e => setFilterUser(e.target.value)}
                className="login-input"
                style={{ height: 28, fontSize: '0.72rem', padding: '0 8px', background: '#121215', width: 'auto' }}
              >
                <option value="ALL">All Users ({reports.length})</option>
                {userOptions.map(([id, name]) => (
                  <option key={id} value={id}>{name} ({reports.filter(r => r.userId === id).length})</option>
                ))}
              </select>
            </div>
          )}
          {reports.length > 0 && (
            <button
              type="button"
              className="preset-btn"
              onClick={handleClearAll}
              style={{
                padding: '4px 10px', fontSize: '0.7rem', gap: 5,
                color: clearConfirm ? '#ffffff' : '#fda4af',
                borderColor: clearConfirm ? '#f43f5e' : 'rgba(244, 63, 94, 0.3)',
                background: clearConfirm ? 'rgba(244, 63, 94, 0.2)' : undefined,
              }}
            >
              <Trash2 size={11} /> {clearConfirm ? 'Confirm Clear All Docs?' : 'Clear All Docs'}
            </button>
          )}
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="empty-state">
          {reports.length === 0
            ? 'No generation documents saved by any user yet.'
            : 'No documents match the selected filter.'}
        </div>
      ) : (
        <div className="table-responsive">
          <table className="history-table">
            <thead>
              <tr>
                <th>User</th>
                <th>Saved Time</th>
                <th>Risk Verdict</th>
                <th>Calibrated Prob</th>
                <th>Input Telemetry</th>
                <th>Storage</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(r => (
                <tr key={r.reportId}>
                  <td style={{ color: '#ffffff', fontWeight: 600 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <User size={13} style={{ color: 'var(--text-dim)' }} />
                      <span>{r.userName}</span>
                    </div>
                  </td>
                  <td style={{ color: 'var(--text-dim)' }}>
                    {new Date(r.savedAt).toLocaleString()}
                  </td>
                  <td>
                    <span className={`badge-risk ${r.risk === 'HIGH' ? 'high' : 'low'}`}>
                      {r.risk}
                    </span>
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                    {r.probability != null ? (r.probability * 100).toFixed(1) + '%' : '—'}
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--text-dim)' }}>
                    {r.inputData?.temperature ? `T:${r.inputData.temperature}°C ` : ''}
                    {r.inputData?.rpm ? `RPM:${r.inputData.rpm} ` : ''}
                    {r.inputData?.vibration ? `V:${r.inputData.vibration}` : ''}
                  </td>
                  <td>
                    {r.cloudinaryUrl ? (
                      <a href={r.cloudinaryUrl} target="_blank" rel="noreferrer" className="cloud-link" style={{ fontSize: '0.72rem' }}>
                        <Cloud size={11} /> Cloud Doc
                      </a>
                    ) : (
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                        Local
                      </span>
                    )}
                  </td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <button
                        type="button"
                        className="preset-btn highlight"
                        onClick={() => onSelectReport(r)}
                        style={{ padding: '3px 9px', fontSize: '0.7rem', gap: 4 }}
                      >
                        <Eye size={11} /> View Doc
                      </button>
                      <button
                        type="button"
                        className="preset-btn"
                        onClick={() => handleDelete(r.userId, r.reportId)}
                        style={{
                          padding: '3px 9px', fontSize: '0.7rem', gap: 4,
                          color: deleteConfirmId === r.reportId ? '#ffffff' : '#fda4af',
                          borderColor: deleteConfirmId === r.reportId ? '#f43f5e' : 'rgba(244, 63, 94, 0.3)',
                          background: deleteConfirmId === r.reportId ? 'rgba(244, 63, 94, 0.2)' : undefined,
                        }}
                      >
                        <Trash2 size={11} />
                        {deleteConfirmId === r.reportId ? 'Confirm?' : 'Delete'}
                      </button>
                    </div>
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

// ── Main Admin Page ───────────────────────────────────────────────────────────

export default function AdminPage({ onLogout }) {
  const session = getSession();
  const [users, setUsers]           = useState(getUsers);
  const [adminAvatar, setAdminAvatar] = useState(getAdminAvatar);
  const [showAddForm, setShowAddForm] = useState(false);
  const [name, setName]             = useState('');
  const [username, setUsername]     = useState('');
  const [password, setPassword]     = useState('');
  const [showPwd, setShowPwd]       = useState(false);
  const [addError, setAddError]     = useState('');
  const [addSuccess, setAddSuccess] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [selectedReport, setSelectedReport] = useState(null);
  const [reportsVersion, setReportsVersion] = useState(0);

  const refreshUsers = () => setUsers(getUsers());

  React.useEffect(() => {
    syncUsersFromBackend().then(u => setUsers(u));
  }, []);

  const handleAddUser = async (e) => {
    e.preventDefault();
    setAddError(''); setAddSuccess('');
    if (!name.trim() || !username.trim() || !password) {
      setAddError('All fields are required.'); return;
    }
    try {
      await addUser({ name, username, password });
      setAddSuccess(`User "${name}" added successfully.`);
      setName(''); setUsername(''); setPassword('');
      refreshUsers();
      setTimeout(() => { setAddSuccess(''); setShowAddForm(false); }, 2000);
    } catch (err) {
      const msg = err?.response?.data?.detail || err.message;
      setAddError(msg);
    }
  };

  const handleDelete = async (userId) => {
    if (deleteConfirm === userId) {
      await deleteUser(userId); refreshUsers(); setDeleteConfirm(null);
    } else {
      setDeleteConfirm(userId);
      setTimeout(() => setDeleteConfirm(null), 3000);
    }
  };

  const handleLogout = () => { logout(); onLogout(); };

  const handleUserAvatarUploaded = (userId, url) => {
    setUsers(prev => prev.map(u => u.id === userId ? { ...u, avatarUrl: url } : u));
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
          {/* Admin avatar in header */}
          <UserAvatar url={adminAvatar} name="Administrator" size={32} />
          <div className="model-badge">
            <Shield size={13} />
            <span>{session?.name}</span>
          </div>
          <div className="status-chip" style={{ color: '#ffffff' }}>
            <span className="status-dot" style={{ background: '#10b981', color: '#10b981' }} />
            <span>ADMIN</span>
          </div>
          <a
            href={`${API_BASE_URL}/docs`}
            target="_blank"
            rel="noreferrer"
            className="preset-btn"
            style={{ padding: '6px 12px', gap: 6, textDecoration: 'none', color: 'inherit' }}
            title="Open Interactive Swagger OpenAPI Documentation"
          >
            <ExternalLink size={13} /> API Docs
          </a>
          <button type="button" className="preset-btn" onClick={handleLogout} style={{ padding: '6px 12px', gap: 6 }}>
            <LogOut size={13} /> Sign Out
          </button>
        </div>
      </header>

      {/* Stats bar */}
      <div className="admin-stats-bar">
        <StatChip label="Registered Users" value={users.length} color="#ffffff" />
        <StatChip label="Generated Docs"   value={getAllReportsGrouped().length} color="#34d399" />
        <StatChip label="Access Events"    value={getAccessLog().length} color="var(--text-secondary)" />
        <StatChip label="System Status"    value="LIVE"         color="#10b981" />
        {isCloudinaryConfigured() && (
          <StatChip label="Cloud Storage" value="READY" color="#10b981" />
        )}
      </div>

      {/* Admin own profile card */}
      <div className="glass-panel" style={{ marginBottom: 20 }}>
        <div className="panel-header">
          <h2 className="panel-title">
            <User size={17} className="panel-icon" />
            <span>Admin Profile</span>
          </h2>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <UserAvatar url={adminAvatar} name="Administrator" size={56} />
          <div>
            <div style={{ fontWeight: 700, fontSize: '0.96rem', marginBottom: 4 }}>Administrator</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.74rem', color: 'var(--text-dim)' }}>
              {session?.username || 'admin'}
            </div>
            {adminAvatar && (
              <a href={adminAvatar} target="_blank" rel="noreferrer" className="cloud-link" style={{ marginTop: 4 }}>
                <ExternalLink size={11} /> View on Cloudinary
              </a>
            )}
          </div>
          <div style={{ marginLeft: 'auto' }}>
            <AvatarUploadBtn
              userId="admin-root"
              currentUrl={adminAvatar}
              name="Administrator"
              onUploaded={(url) => setAdminAvatar(url)}
              onDeleted={() => setAdminAvatar(null)}
            />
          </div>
        </div>
      </div>

      {/* User management */}
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

        {/* Add form */}
        {showAddForm && (
          <div className="admin-add-form">
            <div className="admin-add-form-title">Add New Employee</div>
            {addError   && <div className="login-error-msg" style={{ marginBottom: 12 }}><AlertCircle size={13} /> {addError}</div>}
            {addSuccess && <div className="action-alert safe" style={{ marginBottom: 12, gap: 8 }}><Check size={13} /> {addSuccess}</div>}
            <form onSubmit={handleAddUser} className="admin-form-grid">
              <div className="login-field-group">
                <label className="login-label">Full Name</label>
                <div className="login-input-wrap">
                  <span className="login-input-prefix"><User size={13} /></span>
                  <input type="text" value={name} onChange={e => setName(e.target.value)} placeholder="e.g. John Doe" className="login-input" required />
                </div>
              </div>
              <div className="login-field-group">
                <label className="login-label">Username</label>
                <div className="login-input-wrap">
                  <span className="login-input-prefix"><Terminal size={13} /></span>
                  <input type="text" value={username} onChange={e => setUsername(e.target.value)} placeholder="e.g. emp001" className="login-input" required />
                </div>
              </div>
              <div className="login-field-group">
                <label className="login-label">Password</label>
                <div className="login-input-wrap">
                  <span className="login-input-prefix"><Shield size={13} /></span>
                  <input type={showPwd ? 'text' : 'password'} value={password} onChange={e => setPassword(e.target.value)} placeholder="Set password" className="login-input" required />
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

        {/* Users table */}
        {users.length === 0 ? (
          <div className="empty-state">No employees registered yet. Use the button above to add your first employee.</div>
        ) : (
          <div className="table-responsive">
            <table className="history-table">
              <thead>
                <tr>
                  <th>Avatar</th>
                  <th>Name</th>
                  <th>Username</th>
                  <th>Role</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {/* Admin protected row */}
                <tr>
                  <td><UserAvatar url={adminAvatar} name="Administrator" size={30} /></td>
                  <td style={{ color: '#ffffff', fontWeight: 600 }}>Administrator</td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.74rem' }}>
                    {session?.username || 'admin'}
                  </td>
                  <td><span className="badge-risk" style={{ background: 'rgba(255,255,255,0.08)', color: '#fff', border: '1px solid rgba(255,255,255,0.2)' }}>ADMIN</span></td>
                  <td style={{ color: 'var(--text-dim)' }}>System default</td>
                  <td><span style={{ color: 'var(--text-muted)', fontSize: '0.72rem', fontFamily: 'var(--font-mono)' }}>protected</span></td>
                </tr>

                {users.map(u => (
                  <tr key={u.id}>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <UserAvatar url={u.avatarUrl} name={u.name} size={30} />
                        <AvatarUploadBtn
                          userId={u.id}
                          currentUrl={u.avatarUrl}
                          name={u.name}
                          onUploaded={(url) => handleUserAvatarUploaded(u.id, url)}
                          onDeleted={() => handleUserAvatarUploaded(u.id, null)}
                        />
                      </div>
                    </td>
                    <td style={{ color: '#ffffff' }}>{u.name}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.74rem' }}>{u.username}</td>
                    <td><span className="badge-risk low">EMPLOYEE</span></td>
                    <td style={{ color: 'var(--text-dim)' }}>{new Date(u.createdAt).toLocaleDateString()}</td>
                    <td>
                      <button
                        type="button"
                        className="preset-btn"
                        onClick={() => handleDelete(u.id)}
                        style={{
                          padding: '3px 10px', fontSize: '0.7rem', gap: 5,
                          color: deleteConfirm === u.id ? '#ffffff' : '#fda4af',
                          borderColor: deleteConfirm === u.id ? '#f43f5e' : 'rgba(244, 63, 94, 0.3)',
                          background: deleteConfirm === u.id ? 'rgba(244, 63, 94, 0.15)' : undefined,
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

      {/* Reports and Generation Documents Management */}
      <AdminReportsPanel
        onSelectReport={setSelectedReport}
        reportsVersion={reportsVersion}
        onReportDeleted={() => setReportsVersion(v => v + 1)}
      />

      {/* Access log */}
      <AccessLogPanel />

      {/* Report detail modal */}
      {selectedReport && (
        <ReportDetailModal
          report={selectedReport}
          onClose={() => setSelectedReport(null)}
          onDelete={(r) => {
            deleteReport(r.userId, r.reportId);
            setReportsVersion(v => v + 1);
            setSelectedReport(null);
          }}
        />
      )}
    </div>
  );
}
