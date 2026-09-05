/**
 * auth.js  –  PMS Frontend Authentication Utilities
 * ===================================================
 * All state is stored in localStorage. No backend required for auth.
 *
 * Storage layout:
 *   pms_users       → JSON array of { id, name, username, password, role, createdAt, createdBy }
 *   pms_session     → JSON { userId, username, name, role, loginAt }
 *   pms_access_log  → JSON array of { username, name, role, loginAt, page } (access tracking)
 */

// ── Constants ───────────────────────────────────────────────────────────────

export const ADMIN_CREDENTIALS = {
  username: 'PMS123@987321',
  password: 'Susil@2004',
  role: 'admin',
  name: 'Administrator',
  id: 'admin-root',
};

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
  };
  users.push(newUser);
  saveUsers(users);
  return newUser;
}

export function deleteUser(userId) {
  const users = getUsers().filter(u => u.id !== userId);
  saveUsers(users);
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
  // Check admin first
  if (username === ADMIN_CREDENTIALS.username) {
    if (password === ADMIN_CREDENTIALS.password) {
      const session = {
        userId: ADMIN_CREDENTIALS.id,
        username: ADMIN_CREDENTIALS.username,
        name: ADMIN_CREDENTIALS.name,
        role: 'admin',
        loginAt: new Date().toISOString(),
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
