/**
 * App.jsx  –  PMS Root Router
 * ============================
 * Handles routing between: Landing → Login → Admin | Dashboard
 * No external router library needed (simple state machine).
 */
import React, { useState, useEffect } from 'react';
import LandingPage  from './pages/LandingPage';
import LoginPage    from './pages/LoginPage';
import AdminPage    from './pages/AdminPage';
import DashboardPage from './pages/DashboardPage';
import { getSession, isLoggedIn } from './auth';

/**
 * Pages: 'landing' | 'login' | 'admin' | 'dashboard'
 */
function resolveInitialPage() {
  if (!isLoggedIn()) return 'landing';
  const session = getSession();
  return session?.role === 'admin' ? 'admin' : 'dashboard';
}

export default function App() {
  const [page, setPage] = useState(resolveInitialPage);

  // Handle browser back/forward — keep state in sync with hash
  useEffect(() => {
    const hash = window.location.hash;
    if (hash === '#login') setPage('login');
    else if (hash === '#admin' && isLoggedIn() && getSession()?.role === 'admin') setPage('admin');
    else if (hash === '#dashboard' && isLoggedIn()) setPage('dashboard');
  }, []);

  const goTo = (p) => {
    window.location.hash = p;
    setPage(p);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleLoginSuccess = (session) => {
    if (session.role === 'admin') goTo('admin');
    else goTo('dashboard');
  };

  const handleLogout = () => {
    goTo('landing');
  };

  switch (page) {
    case 'login':
      return (
        <LoginPage
          onLoginSuccess={handleLoginSuccess}
          onBack={() => goTo('landing')}
        />
      );
    case 'admin':
      return (
        <AdminPage onLogout={handleLogout} />
      );
    case 'dashboard':
      return (
        <DashboardPage onLogout={handleLogout} />
      );
    case 'landing':
    default:
      return (
        <LandingPage onNavigateLogin={() => goTo('login')} />
      );
  }
}
