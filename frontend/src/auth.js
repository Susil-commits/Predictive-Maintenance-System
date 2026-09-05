/**
 * auth.js  –  PMS Frontend Authentication Utilities
 * ===================================================
 * Secured via PostgreSQL DB, bcrypt password hashing, and JWT tokens.
 *
 * Plaintext passwords and admin credentials are NEVER stored in localStorage
 * or bundled into Vite source.
 *
 * Storage layout:
 *   pms_token       → signed JWT access token string
 *   pms_session     → JSON { userId, username, name, role, loginAt, avatarUrl }
 *   pms_users_cache → JSON array of { id, name, username, role, createdAt, avatarUrl } (no passwords)
 *   pms_access_log  → JSON array of { username, name, role, loginAt, page } (access tracking)
 */

import { loginApi, getUsersApi, createUserApi, deleteUserApi } from './api';

const TOKEN_KEY   = 'pms_token';
const SESSION_KEY = 'pms_session';
const LOG_KEY     = 'pms_access_log';
const USERS_KEY   = 'pms_users_cache';
const REPORTS_KEY = 'pms_reports';

// ── Token Management ────────────────────────────────────────────────────────

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY) || null;
  } catch {
    return null;
  }
}

export function setToken(token) {
  try {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
  } catch { /* ignore storage errors */ }
}

// ── Session ─────────────────────────────────────────────────────────────────

export function getSession() {
  try {
    return JSON.parse(localStorage.getItem(SESSION_KEY) || 'null');
  } catch {
    return null;
  }
}

export function isLoggedIn() {
  return getToken() !== null && getSession() !== null;
}

export function isAdmin() {
  return getSession()?.role === 'admin';
}

/**
 * Authenticate against the backend POST /auth/login.
 * Returns { ok, session, error, intruder }.
 */
export async function login(username, password) {
  try {
    const data = await loginApi(username.trim(), password);
    const { access_token, user } = data;

    setToken(access_token);

    const session = {
      userId: user.id,
      username: user.username,
      name: user.role === 'admin' ? 'Administrator' : user.username,
      role: user.role,
      designation: user.designation || (user.role === 'admin' ? 'System Administrator' : 'Maintenance Specialist'),
      loginAt: new Date().toISOString(),
      avatarUrl: user.role === 'admin' ? getAdminAvatar() : null,
    };

    localStorage.setItem(SESSION_KEY, JSON.stringify(session));
    _logAccess(session);

    return { ok: true, session };
  } catch (err) {
    const detail = err?.response?.data?.detail || err.message || 'Login failed';
    const isUserNotFound =
      err?.response?.headers?.['x-auth-reason'] === 'user_not_found' ||
      detail.toLowerCase().includes('not registered');

    return {
      ok: false,
      intruder: isUserNotFound,
      error: detail,
    };
  }
}

export function logout() {
  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(SESSION_KEY);
  } catch { /* ignore */ }
}

// ── User Management (Backend Synchronized, NO stored passwords) ─────────────

export function getUsers() {
  try {
    return JSON.parse(localStorage.getItem(USERS_KEY) || '[]');
  } catch {
    return [];
  }
}

export function saveUsers(users) {
  try {
    localStorage.setItem(USERS_KEY, JSON.stringify(users));
  } catch { /* ignore */ }
}

/**
 * Refresh users from backend PostgreSQL DB.
 */
export async function syncUsersFromBackend() {
  try {
    const dbUsers = await getUsersApi();
    const local = getUsers();
    const avatarMap      = Object.fromEntries(local.map(u => [u.id, u.avatarUrl]));
    const nameMap        = Object.fromEntries(local.map(u => [u.id, u.name]));
    const designationMap = Object.fromEntries(local.map(u => [u.id, u.designation]));

    const merged = dbUsers
      .filter(u => u.role !== 'admin')
      .map(u => ({
        id: u.id,
        username: u.username,
        name: nameMap[u.id] || u.username,
        designation: u.designation || designationMap[u.id] || 'Maintenance Specialist',
        role: u.role,
        createdAt: u.created_at || new Date().toISOString(),
        avatarUrl: avatarMap[u.id] || null,
      }));

    saveUsers(merged);
    return merged;
  } catch (err) {
    console.warn('[PMS Auth] Could not sync users from backend:', err.message);
    return getUsers();
  }
}

export async function addUser({ name, username, password, designation }) {
  const cleanDesignation = (designation || '').trim() || 'Maintenance Specialist';
  const created = await createUserApi({
    username: username.trim(),
    password,
    role: 'employee',
    designation: cleanDesignation,
  });

  const users = getUsers().filter(u => u.id !== created.id);
  const newUser = {
    id: created.id,
    name: name.trim() || created.username,
    username: created.username,
    designation: created.designation || cleanDesignation,
    role: created.role,
    createdAt: created.created_at || new Date().toISOString(),
    avatarUrl: null,
  };
  users.push(newUser);
  saveUsers(users);
  return newUser;
}

export async function deleteUser(userId) {
  try {
    await deleteUserApi(userId);
  } catch (err) {
    console.warn('[PMS Auth] Backend user deletion note:', err.message);
  }
  const users = getUsers().filter(u => u.id !== userId);
  saveUsers(users);
}

// ── Avatars (Cloudinary) ────────────────────────────────────────────────────

export function updateUserAvatar(userId, avatarUrl) {
  if (userId === 'admin-root' || getSession()?.userId === userId && isAdmin()) {
    localStorage.setItem('pms_admin_avatar', avatarUrl);
    const session = getSession();
    if (session) {
      localStorage.setItem(SESSION_KEY, JSON.stringify({ ...session, avatarUrl }));
    }
    return;
  }
  const users = getUsers().map(u =>
    u.id === userId ? { ...u, avatarUrl } : u
  );
  saveUsers(users);
  const session = getSession();
  if (session?.userId === userId) {
    localStorage.setItem(SESSION_KEY, JSON.stringify({ ...session, avatarUrl }));
  }
}

export function getAdminAvatar() {
  try {
    return localStorage.getItem('pms_admin_avatar') || null;
  } catch {
    return null;
  }
}

export function deleteAvatar(userId) {
  if (userId === 'admin-root' || (getSession()?.userId === userId && isAdmin())) {
    localStorage.removeItem('pms_admin_avatar');
    const session = getSession();
    if (session) {
      localStorage.setItem(SESSION_KEY, JSON.stringify({ ...session, avatarUrl: null }));
    }
    return;
  }
  const users = getUsers().map(u =>
    u.id === userId ? { ...u, avatarUrl: null } : u
  );
  saveUsers(users);
  const session = getSession();
  if (session?.userId === userId) {
    localStorage.setItem(SESSION_KEY, JSON.stringify({ ...session, avatarUrl: null }));
  }
}

// ── Access Log ───────────────────────────────────────────────────────────────

function _logAccess(session) {
  try {
    const log = getAccessLog();
    log.unshift({ ...session, page: 'login' });
    localStorage.setItem(LOG_KEY, JSON.stringify(log.slice(0, 200)));
  } catch { /* ignore */ }
}

export function getAccessLog() {
  try {
    return JSON.parse(localStorage.getItem(LOG_KEY) || '[]');
  } catch {
    return [];
  }
}

export function logPageAccess(page) {
  const session = getSession();
  if (!session) return;
  try {
    const log = getAccessLog();
    log.unshift({ ...session, page, accessedAt: new Date().toISOString() });
    localStorage.setItem(LOG_KEY, JSON.stringify(log.slice(0, 200)));
  } catch { /* ignore */ }
}

export function clearAccessLog() {
  try {
    localStorage.removeItem(LOG_KEY);
  } catch { /* ignore */ }
}

// ── Report Store ─────────────────────────────────────────────────────────────

function _getAllReports() {
  try {
    return JSON.parse(localStorage.getItem(REPORTS_KEY) || '{}');
  } catch {
    return {};
  }
}

function _saveAllReports(all) {
  try {
    localStorage.setItem(REPORTS_KEY, JSON.stringify(all));
  } catch { /* ignore */ }
}

export function saveReport(report) {
  const all = _getAllReports();
  const { userId } = report;
  if (!userId) throw new Error('report.userId is required');
  const entry = {
    reportId:        'report-' + Date.now() + '-' + Math.random().toString(36).slice(2, 6),
    predictionId:    report.predictionId  || null,
    risk:            report.risk          || 'UNKNOWN',
    probability:     report.probability   ?? null,
    inputData:       report.inputData     || {},
    shapFactors:     report.shapFactors   || [],
    cloudinaryUrl:   report.cloudinaryUrl || null,
    savedAt:         new Date().toISOString(),
    userId,
    userName:        report.userName || 'Unknown',
    userDesignation: report.userDesignation || 'Maintenance Specialist',
  };
  all[userId] = [entry, ...(all[userId] || [])].slice(0, 100);
  _saveAllReports(all);
  return entry;
}

export function getReportsForUser(userId) {
  return (_getAllReports()[userId] || []);
}

export function deleteReport(userId, reportId) {
  const all = _getAllReports();
  if (all[userId]) {
    all[userId] = all[userId].filter(r => r.reportId !== reportId);
    if (all[userId].length === 0) delete all[userId];
  }
  _saveAllReports(all);
}

export function getAllReportsGrouped() {
  const all = _getAllReports();
  const users = getUsers();
  const userMap = Object.fromEntries(users.map(u => [u.id, u.name]));
  const desigMap = Object.fromEntries(users.map(u => [u.id, u.designation]));
  userMap['admin-root'] = 'Administrator';
  desigMap['admin-root'] = 'System Administrator';
  return Object.entries(all).flatMap(([userId, reports]) =>
    reports.map(r => ({
      ...r,
      userName: userMap[userId] || r.userName || userId,
      userDesignation: r.userDesignation || desigMap[userId] || 'Maintenance Specialist'
    }))
  ).sort((a, b) => new Date(b.savedAt) - new Date(a.savedAt));
}

export function clearAllReports() {
  try {
    localStorage.removeItem(REPORTS_KEY);
  } catch { /* ignore */ }
}
