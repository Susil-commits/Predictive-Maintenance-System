import React from 'react';
import { AlertOctagon, RefreshCw, Home, ChevronDown, ChevronUp } from 'lucide-react';

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      showDetails: false,
    };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo });
    console.error('[PMS ErrorBoundary] Uncaught component error:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null, showDetails: false });
  };

  handleReload = () => {
    window.location.reload();
  };

  handleGoHome = () => {
    this.setState({ hasError: false, error: null, errorInfo: null, showDetails: false });
    window.location.hash = '#landing';
    window.dispatchEvent(new Event('hashchange'));
  };

  render() {
    if (this.state.hasError) {
      const { error, errorInfo, showDetails } = this.state;

      return (
        <div style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '24px',
          background: 'radial-gradient(ellipse at 50% 20%, #1e293b 0%, #0f172a 60%, #020617 100%)',
          color: '#f8fafc',
          fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
        }}>
          <div style={{
            maxWidth: '620px',
            width: '100%',
            background: 'rgba(30, 41, 59, 0.75)',
            backdropFilter: 'blur(16px)',
            WebkitBackdropFilter: 'blur(16px)',
            border: '1px solid rgba(239, 68, 68, 0.25)',
            borderRadius: '16px',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.6), 0 0 30px rgba(239, 68, 68, 0.1)',
            padding: '32px',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '20px' }}>
              <div style={{
                width: '48px',
                height: '48px',
                borderRadius: '12px',
                background: 'rgba(239, 68, 68, 0.15)',
                border: '1px solid rgba(239, 68, 68, 0.35)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#f87171',
                flexShrink: 0,
              }}>
                <AlertOctagon size={26} />
              </div>
              <div>
                <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 600, color: '#f8fafc', letterSpacing: '-0.02em' }}>
                  Component Anomaly Encountered
                </h2>
                <p style={{ margin: '4px 0 0 0', fontSize: '0.875rem', color: '#94a3b8' }}>
                  An isolated rendering error was safely intercepted to protect system integrity.
                </p>
              </div>
            </div>

            <div style={{
              background: 'rgba(15, 23, 42, 0.6)',
              border: '1px solid rgba(51, 65, 85, 0.6)',
              borderRadius: '8px',
              padding: '14px 16px',
              marginBottom: '24px',
              fontSize: '0.875rem',
              color: '#cbd5e1',
            }}>
              <span style={{ color: '#f87171', fontWeight: 600 }}>Error: </span>
              {error?.message || 'An unexpected exception occurred during rendering.'}
            </div>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', marginBottom: '20px' }}>
              <button
                onClick={this.handleReset}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '9px 18px',
                  borderRadius: '8px',
                  border: 'none',
                  background: 'linear-gradient(135deg, #0284c7 0%, #0369a1 100%)',
                  color: '#ffffff',
                  fontSize: '0.875rem',
                  fontWeight: 500,
                  cursor: 'pointer',
                  transition: 'opacity 0.15s ease',
                }}
              >
                <RefreshCw size={15} /> Try Recovering
              </button>

              <button
                onClick={this.handleReload}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '9px 18px',
                  borderRadius: '8px',
                  border: '1px solid rgba(148, 163, 184, 0.25)',
                  background: 'rgba(30, 41, 59, 0.8)',
                  color: '#e2e8f0',
                  fontSize: '0.875rem',
                  fontWeight: 500,
                  cursor: 'pointer',
                }}
              >
                Reload Page
              </button>

              <button
                onClick={this.handleGoHome}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '9px 18px',
                  borderRadius: '8px',
                  border: '1px solid rgba(148, 163, 184, 0.25)',
                  background: 'transparent',
                  color: '#94a3b8',
                  fontSize: '0.875rem',
                  fontWeight: 500,
                  cursor: 'pointer',
                  marginLeft: 'auto',
                }}
              >
                <Home size={15} /> Home
              </button>
            </div>

            {errorInfo && (
              <div>
                <button
                  onClick={() => this.setState(s => ({ showDetails: !s.showDetails }))}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: '#64748b',
                    fontSize: '0.75rem',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    padding: 0,
                  }}
                >
                  {showDetails ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  {showDetails ? 'Hide technical diagnostics' : 'Show technical diagnostics'}
                </button>

                {showDetails && (
                  <pre style={{
                    marginTop: '12px',
                    padding: '12px',
                    background: 'rgba(2, 6, 23, 0.8)',
                    borderRadius: '8px',
                    border: '1px solid rgba(51, 65, 85, 0.5)',
                    fontSize: '0.75rem',
                    color: '#f43f5e',
                    overflowX: 'auto',
                    whiteSpace: 'pre-wrap',
                    maxHeight: '200px',
                  }}>
                    {error?.stack}
                    {'\n\nComponent Stack:'}
                    {errorInfo.componentStack}
                  </pre>
                )}
              </div>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
