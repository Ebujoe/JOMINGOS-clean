'use client';

import { useEffect, useState } from 'react';
import { apiFetch } from '@/lib/api';

interface Alert {
  id: number;
  patient: number;
  patient_name: string;
  alert_type: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
  status: 'active' | 'acknowledged' | 'resolved';
  trigger_reason: string;
  triggered_at: string;
}

export default function AlertDashboard() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const fetchAlerts = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiFetch<Alert[]>('/alerts/active_alerts/');
      setAlerts(data);
      setLastRefresh(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      console.error('Error fetching alerts:', err);
    } finally {
      setLoading(false);
    }
  };

  const acknowledgeAlert = async (alertId: number) => {
    try {
      await apiFetch(`/alerts/${alertId}/acknowledge/`, {
        method: 'POST',
      });
      setAlerts(alerts.filter(a => a.id !== alertId));
    } catch (err) {
      console.error('Error acknowledging alert:', err);
      alert('Failed to acknowledge alert');
    }
  };

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 30000);
    return () => clearInterval(interval);
  }, []);

  const getPriorityColor = (priority: string) => {
    const colors: Record<string, { border: string; bg: string; text: string; icon: string }> = {
      critical: { border: '#dc2626', bg: 'rgba(220, 38, 38, 0.08)', text: '#7f1d1d', icon: '🚨' },
      high: { border: '#ea580c', bg: 'rgba(234, 88, 12, 0.08)', text: '#7c2d12', icon: '⚠️' },
      medium: { border: '#ca8a04', bg: 'rgba(202, 138, 4, 0.08)', text: '#713f12', icon: '⚡' },
      low: { border: '#16a34a', bg: 'rgba(22, 163, 74, 0.08)', text: '#15803d', icon: '✓' }
    };
    return colors[priority] || colors.low;
  };

  return (
    <div style={{
      background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%)',
      minHeight: '100vh',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Oxygen", "Ubuntu", "Cantarell", sans-serif'
    }}>
      {/* Premium Header */}
      <div style={{
        background: 'linear-gradient(180deg, rgba(255,255,255,0.97) 0%, rgba(255,255,255,0.92) 100%)',
        borderBottom: '1px solid rgba(15, 23, 42, 0.08)',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.08)',
        backdropFilter: 'blur(20px)'
      }} className="sticky top-0 z-50">
        <div className="mx-auto max-w-7xl px-6 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 style={{ fontSize: '2rem', fontWeight: '800', color: '#0f172a', letterSpacing: '-0.02em' }} className="mb-1">
                Active Alerts
              </h1>
              <p style={{ color: '#64748b', fontSize: '0.95rem' }}>
                Real-time patient deterioration monitoring
              </p>
            </div>
            <div className="flex items-center gap-6">
              <button
                onClick={fetchAlerts}
                disabled={loading}
                style={{
                  background: 'linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)',
                  boxShadow: '0 4px 12px rgba(37, 99, 235, 0.25)',
                  border: 'none',
                  borderRadius: '10px'
                }}
                className="inline-flex items-center gap-2 px-6 py-2.5 text-white font-semibold hover:shadow-lg transition-all disabled:opacity-50 cursor-pointer"
              >
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Refresh
              </button>
              <div style={{ borderLeft: '1px solid #e2e8f0', paddingLeft: '1.5rem' }}>
                <p style={{ fontSize: '0.8rem', color: '#94a3b8', fontWeight: '500', letterSpacing: '0.02em', textTransform: 'uppercase' }}>Last Updated</p>
                <p style={{ fontSize: '1rem', fontWeight: '600', color: '#0f172a' }}>
                  {lastRefresh.toLocaleTimeString()}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="mx-auto max-w-7xl px-6 py-12">
        {/* Error State */}
        {error && (
          <div style={{
            background: 'rgba(239, 68, 68, 0.12)',
            border: '1.5px solid #dc2626',
            borderRadius: '14px',
            backdropFilter: 'blur(10px)'
          }} className="mb-8 p-6">
            <div className="flex gap-4 items-start">
              <span style={{ fontSize: '1.5rem' }}>❌</span>
              <div>
                <h3 style={{ color: '#dc2626', fontWeight: '700', fontSize: '1rem' }}>Error Loading Alerts</h3>
                <p style={{ color: '#991b1b', marginTop: '0.5rem', fontSize: '0.95rem' }}>{error}</p>
                {error.includes('token') && (
                  <p style={{ color: '#7f1d1d', marginTop: '0.75rem', fontSize: '0.85rem' }}>
                    Please log in again to refresh your session.
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Loading State */}
        {loading && !error && (
          <div className="space-y-6">
            {[1, 2].map(i => (
              <div key={i} style={{
                background: 'rgba(255, 255, 255, 0.1)',
                borderRadius: '14px',
                height: '220px',
                animation: 'pulse 2s infinite'
              }} />
            ))}
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && alerts.length === 0 && (
          <div style={{
            background: 'linear-gradient(135deg, rgba(34, 197, 94, 0.12) 0%, rgba(22, 163, 74, 0.08) 100%)',
            border: '2px dashed #16a34a',
            borderRadius: '16px',
            backdropFilter: 'blur(10px)'
          }} className="py-20 px-8 text-center">
            <div style={{ fontSize: '3.5rem', marginBottom: '1rem' }}>✅</div>
            <h3 style={{ color: '#15803d', fontWeight: '700', fontSize: '1.75rem', letterSpacing: '-0.01em' }}>All Clear</h3>
            <p style={{ color: '#16a34a', marginTop: '0.75rem', fontSize: '1rem' }}>
              No active patient alerts at this time
            </p>
            <p style={{ color: '#22c55e', marginTop: '0.5rem', fontSize: '0.9rem' }}>
              System monitoring 24/7 • Auto-refresh every 30 seconds
            </p>
          </div>
        )}

        {/* Alerts Grid */}
        <div className="grid gap-8 lg:grid-cols-2">
          {alerts.map(alert => {
            const color = getPriorityColor(alert.priority);
            const alertTime = new Date(alert.triggered_at);
            const timeAgo = Math.round((Date.now() - alertTime.getTime()) / 60000);

            return (
              <div
                key={alert.id}
                style={{
                  background: `linear-gradient(135deg, ${color.bg} 0%, rgba(255, 255, 255, 0.05) 100%)`,
                  border: `1.5px solid ${color.border}`,
                  borderRadius: '16px',
                  boxShadow: `0 8px 32px ${color.border}20, inset 0 1px 1px rgba(255, 255, 255, 0.5)`,
                  backdropFilter: 'blur(10px)',
                  transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                  padding: '24px',
                  cursor: 'default'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = 'translateY(-4px)';
                  e.currentTarget.style.boxShadow = `0 16px 48px ${color.border}30, inset 0 1px 1px rgba(255, 255, 255, 0.5)`;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = `0 8px 32px ${color.border}20, inset 0 1px 1px rgba(255, 255, 255, 0.5)`;
                }}
              >
                {/* Top Section - Patient + Priority */}
                <div className="flex items-start justify-between mb-6">
                  <div className="flex items-start gap-4 flex-1">
                    <span style={{ fontSize: '2.5rem', lineHeight: '1' }}>{color.icon}</span>
                    <div className="flex-1">
                      <h3 style={{ color: color.text, fontWeight: '700', fontSize: '1.35rem', letterSpacing: '-0.01em', lineHeight: '1.2' }}>
                        {alert.patient_name}
                      </h3>
                      <p style={{ color: color.text, opacity: 0.6, marginTop: '0.35rem', fontSize: '0.9rem' }}>
                        Patient ID: {alert.patient}
                      </p>
                    </div>
                  </div>
                  <span
                    style={{
                      background: color.bg,
                      color: color.text,
                      padding: '0.5rem 1rem',
                      borderRadius: '8px',
                      fontWeight: '700',
                      fontSize: '0.8rem',
                      textTransform: 'uppercase',
                      letterSpacing: '0.08em',
                      border: `1px solid ${color.border}40`
                    }}
                  >
                    {alert.priority}
                  </span>
                </div>

                {/* Divider */}
                <div style={{ height: '1px', background: `${color.border}33`, marginBottom: '1.5rem' }} />

                {/* Details Grid */}
                <div className="grid grid-cols-2 gap-6 mb-6">
                  <div>
                    <p style={{ color: color.text, opacity: 0.5, fontSize: '0.7rem', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.6rem' }}>Alert Type</p>
                    <p style={{ color: color.text, fontWeight: '600', fontSize: '0.95rem' }}>{alert.alert_type.replace('_', ' ').toUpperCase()}</p>
                  </div>
                  <div>
                    <p style={{ color: color.text, opacity: 0.5, fontSize: '0.7rem', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.6rem' }}>Triggered</p>
                    <p style={{ color: color.text, fontWeight: '600', fontSize: '0.95rem' }}>{alertTime.toLocaleTimeString()}</p>
                  </div>
                </div>

                {/* Trigger Reason Box */}
                <div style={{
                  background: `${color.bg}80`,
                  borderRadius: '12px',
                  padding: '12px 16px',
                  marginBottom: '1.5rem',
                  borderLeft: `3px solid ${color.border}`,
                  borderTop: `1px solid ${color.border}33`,
                  borderRight: `1px solid ${color.border}33`,
                  borderBottom: `1px solid ${color.border}33`
                }}>
                  <p style={{ color: color.text, opacity: 0.5, fontSize: '0.7rem', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>Trigger Reason</p>
                  <p style={{ color: color.text, fontWeight: '600', fontSize: '0.95rem', lineHeight: '1.4' }}>{alert.trigger_reason}</p>
                </div>

                {/* Status & Time Grid */}
                <div className="grid grid-cols-2 gap-4 mb-6">
                  <div>
                    <p style={{ color: color.text, opacity: 0.5, fontSize: '0.7rem', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.6rem' }}>Status</p>
                    <span style={{
                      background: `${color.bg}`,
                      color: color.text,
                      padding: '0.4rem 0.8rem',
                      borderRadius: '6px',
                      fontSize: '0.8rem',
                      fontWeight: '600',
                      display: 'inline-block',
                      border: `0.5px solid ${color.border}80`
                    }}>
                      {alert.status.toUpperCase()}
                    </span>
                  </div>
                  <div>
                    <p style={{ color: color.text, opacity: 0.5, fontSize: '0.7rem', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.6rem' }}>Time Since</p>
                    <p style={{ color: color.text, fontWeight: '600', fontSize: '0.95rem' }}>{timeAgo}m ago</p>
                  </div>
                </div>

                {/* Action Button */}
                <button
                  onClick={() => acknowledgeAlert(alert.id)}
                  style={{
                    background: `linear-gradient(135deg, ${color.border} 0%, ${color.border}dd 100%)`,
                    boxShadow: `0 4px 12px ${color.border}40`,
                    width: '100%',
                    color: 'white',
                    padding: '12px 16px',
                    borderRadius: '10px',
                    fontWeight: '700',
                    fontSize: '0.95rem',
                    border: 'none',
                    cursor: 'pointer',
                    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                    letterSpacing: '0.02em'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.transform = 'translateY(-2px)';
                    e.currentTarget.style.boxShadow = `0 6px 20px ${color.border}60`;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = 'translateY(0)';
                    e.currentTarget.style.boxShadow = `0 4px 12px ${color.border}40`;
                  }}
                >
                  ✓ Acknowledge Alert
                </button>
              </div>
            );
          })}
        </div>

        {/* Stats Footer */}
        {!loading && alerts.length > 0 && (
          <div style={{
            background: 'rgba(255, 255, 255, 0.08)',
            border: '1px solid rgba(255, 255, 255, 0.12)',
            borderRadius: '12px',
            marginTop: '2rem',
            padding: '1.5rem',
            textAlign: 'center',
            backdropFilter: 'blur(10px)'
          }}>
            <p style={{ color: '#e2e8f0', fontWeight: '700', fontSize: '1rem', letterSpacing: '0.02em' }}>
              {alerts.length} active alert{alerts.length !== 1 ? 's' : ''} • Immediate attention required
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
