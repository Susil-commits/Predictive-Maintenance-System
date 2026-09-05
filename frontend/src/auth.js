/**
 * auth.js  –  PMS Frontend Authentication Utilities
 * ===================================================
 * All state is stored in localStorage. No backend required for auth.
 *
 * Admin credentials are injected at build-time from VITE_ADMIN_USERNAME /
 * VITE_ADMIN_PASSWORD in the .env file. They are NEVER hardcoded in source.
 *
 * Storage layout:
 *   pms_users       → JSON array of { id, name, username, password, role, createdAt, createdBy, avatarUrl }
 *   pms_session     → JSON { userId, username, name, role, loginAt, avatarUrl }
 *   pms_access_log  → JSON array of { username, name, role, loginAt, page } (access tracking)
 */

// ── Admin credentials (sourced exclusively from .env — never hardcoded) ──────

function _getAdminCredentials() {
  const username = import.meta.env.VITE_ADMIN_USERNAME;
  const password = import.meta.env.VITE_ADMIN_PASSWORD;

  if (!username || !password) {
    console.error(
      '[PMS Auth] VITE_ADMIN_USERNAME or VITE_ADMIN_PASSWORD is not set in .env. ' +
      'Admin login will not work until these environment variables are configured.'
    );
  }

  return {
    username: username || '__env_missing__',
    password: password || '__env_missing__',
    role: 'admin',
    name: 'Administrator',
    id: 'admin-root',
  };
}

// Export a lazily-evaluated getter so tests / hot-reload pick up changes
export const getAdminCredentials = _getAdminCredentials;

const USERS_KEY   = 'pms_users';
const SESSION_KEY = 'pms_session';
const LOG_KEY     = 'pms_access_log';

// ── User Store ──────────────────────────────────────────────────────────────

export function getUsers() {
  try {
    return JSON.parse(localStorage.getItem(USERS_KEY) || '[]');
  } catch {
    return [];
  }
}

export function saveUsers(users) {
  localStorage.setItem(USERS_KEY, JSON.stringify(users));
}

export function addUser({ name, username, password }) {
  const users = getUsers();
  if (users.find(u => u.username === username)) {
    throw new Error(`Username "${username}" already exists.`);
  }
  const newUser = {
    id: `user-${Date.now()}`,
    name: name.trim(),
    username: username.trim(),
    password,
    role: 'employee',
    createdAt: new Date().toISOString(),
    createdBy: 'admin',
    avatarUrl: null,   // set via updateUserAvatar()
  };
  users.push(newUser);
  saveUsers(users);
  return newUser;
}

export function deleteUser(userId) {
  const users = getUsers().filter(u => u.id !== userId);
  saveUsers(users);
}

/**
 * Update the Cloudinary avatar URL for a user (or the admin).
 * For admin: stored separately under pms_admin_avatar.
 * For employees: stored on the user record in pms_users.
 */
export function updateUserAvatar(userId, avatarUrl) {
  if (userId === 'admin-root') {
    localStorage.setItem('pms_admin_avatar', avatarUrl);
    // Also update current session if admin is logged in
    const session = getSession();
    if (session?.userId === 'admin-root') {
      localStorage.setItem(SESSION_KEY, JSON.stringify({ ...session, avatarUrl }));
    }
    return;
  }
  const users = getUsers().map(u =>
    u.id === userId ? { ...u, avatarUrl } : u
  );
  saveUsers(users);
  // Update live session if this is the current user
  const session = getSession();
  if (session?.userId === userId) {
    localStorage.setItem(SESSION_KEY, JSON.stringify({ ...session, avatarUrl }));
  }
}

export function getAdminAvatar() {
  return localStorage.getItem('pms_admin_avatar') || null;
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
  return getSession() !== null;
}

export function isAdmin() {
  return getSession()?.role === 'admin';
}

/**
 * Attempt login. Returns { ok, session, error, intruder }.
 *   intruder: true  → username not recognised at all
 *   intruder: false → username known but password wrong
 */
export function login(username, password) {
  const ADMIN = getAdminCredentials();

  // Check admin first
  if (username === ADMIN.username) {
    if (password === ADMIN.password) {
      const session = {
        userId: ADMIN.id,
        username: ADMIN.username,
        name: ADMIN.name,
        role: 'admin',
        loginAt: new Date().toISOString(),
        avatarUrl: getAdminAvatar(),
      };
      localStorage.setItem(SESSION_KEY, JSON.stringify(session));
      _logAccess(session);
      return { ok: true, session };
    }
    return { ok: false, intruder: false, error: 'Incorrect password.' };
  }

  // Check employee users
  const users = getUsers();
  const user = users.find(u => u.username === username);

  if (!user) {
    // Username not in system at all → intruder
    return {
      ok: false,
      intruder: true,
      error: 'Access denied. You are not registered in this system. Contact the Administrator.',
    };
  }

  if (user.password !== password) {
    return { ok: false, intruder: false, error: 'Incorrect password.' };
  }

  const session = {
    userId: user.id,
    username: user.username,
    name: user.name,
    role: 'employee',
    loginAt: new Date().toISOString(),
    avatarUrl: user.avatarUrl || null,
  };
  localStorage.setItem(SESSION_KEY, JSON.stringify(session));
  _logAccess(session);
  return { ok: true, session };
}

export function logout() {
  localStorage.removeItem(SESSION_KEY);
}

// ── Access Log ───────────────────────────────────────────────────────────────

function _logAccess(session) {
  try {
    const log = getAccessLog();
    log.unshift({ ...session, page: 'login' });
    // Keep last 200 entries
    localStorage.setItem(LOG_KEY, JSON.stringify(log.slice(0, 200)));
  } catch { /* ignore storage errors */ }
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

// ── Report Store ─────────────────────────────────────────────────────────────
//
// Storage layout (localStorage):
//   pms_reports  ->  { [userId]: Report[] }
//
// Report shape:
//   {
//     reportId:      string,
//     predictionId:  string | null,
//     risk:          'HIGH' | 'LOW',
//     probability:   number,
//     inputData:     object,
//     shapFactors:   array,
//     cloudinaryUrl: string | null,
//     savedAt:       ISO string,
//     userId:        string,
//     userName:      string,
//   }

const REPORTS_KEY = 'pms_reports';

function _getAllReports() {
  try { return JSON.parse(localStorage.getItem(REPORTS_KEY) || '{}'); }
  catch { return {}; }
}

function _saveAllReports(all) {
  localStorage.setItem(REPORTS_KEY, JSON.stringify(all));
}

export function saveReport(report) {
  const all = _getAllReports();
  const { userId } = report;
  if (!userId) throw new Error('report.userId is required');
  const entry = {
    reportId:      'report-' + Date.now() + '-' + Math.random().toString(36).slice(2, 6),
    predictionId:  report.predictionId  || null,
    risk:          report.risk          || 'UNKNOWN',
    probability:   report.probability   ?? null,
    inputData:     report.inputData     || {},
    shapFactors:   report.shapFactors   || [],
    cloudinaryUrl: report.cloudinaryUrl || null,
    savedAt:       new Date().toISOString(),
    userId,
    userName:      report.userName || 'Unknown',
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
  userMap['admin-root'] = 'Administrator';
  return Object.entries(all).flatMap(([userId, reports]) =>
    reports.map(r => ({ ...r, userName: userMap[userId] || r.userName || userId }))
  ).sort((a, b) => new Date(b.savedAt) - new Date(a.savedAt));
}

export function clearAccessLog() {
  localStorage.removeItem(LOG_KEY);
}

export function clearAllReports() {
  localStorage.removeItem(REPORTS_KEY);
}

export function deleteAvatar(userId) {
  if (userId === 'admin-root') {
    localStorage.removeItem('pms_admin_avatar');
    const session = getSession();
    if (session?.userId === 'admin-root') {
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

