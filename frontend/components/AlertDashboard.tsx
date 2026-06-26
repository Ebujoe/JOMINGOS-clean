'use client';

import { useEffect, useState } from 'react';

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

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

  // Fetch alerts from backend
  const fetchAlerts = async () => {
    try {
      setLoading(true);
      setError(null);

      const token = localStorage.getItem('access_token');

      if (!token) {
        setError('Not authenticated. Please login first to view alerts.');
        setLoading(false);
        return;
      }

      const headers: HeadersInit = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      };

      const response = await fetch(`${API_URL}/alerts/active_alerts/`, {
        headers,
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch alerts: ${response.statusText}`);
      }

      const data = await response.json();
      setAlerts(data);
      setLastRefresh(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      console.error('Error fetching alerts:', err);
    } finally {
      setLoading(false);
    }
  };

  // Acknowledge an alert
  const acknowledgeAlert = async (alertId: number) => {
    try {
      const token = localStorage.getItem('access_token');
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };

      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_URL}/alerts/${alertId}/acknowledge/`, {
        method: 'POST',
        headers,
      });

      if (!response.ok) {
        throw new Error('Failed to acknowledge alert');
      }

      // Remove acknowledged alert from list
      setAlerts(alerts.filter(a => a.id !== alertId));
    } catch (err) {
      console.error('Error acknowledging alert:', err);
      alert('Failed to acknowledge alert');
    }
  };

  // Fetch alerts on mount and set up auto-refresh (every 30 seconds)
  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 30000);
    return () => clearInterval(interval);
  }, []);

  const getPriorityColor = (priority: string): string => {
    switch (priority) {
      case 'critical':
        return '#dc3545'; // Red
      case 'high':
        return '#fd7e14'; // Orange
      case 'medium':
        return '#ffc107'; // Yellow
      case 'low':
        return '#28a745'; // Green
      default:
        return '#6c757d'; // Gray
    }
  };

  const getPriorityLabel = (priority: string): string => {
    return priority.toUpperCase();
  };

  return (
    <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      {/* Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '30px',
          borderBottom: '2px solid #e0e0e0',
          paddingBottom: '15px',
        }}
      >
        <h1 style={{ margin: 0, fontSize: '28px', fontWeight: 'bold', color: '#333' }}>
          🚨 Active Alerts
        </h1>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <button
            onClick={fetchAlerts}
            style={{
              padding: '8px 16px',
              backgroundColor: '#007bff',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '14px',
            }}
          >
            🔄 Refresh
          </button>
          <span style={{ fontSize: '12px', color: '#666' }}>
            Last updated: {lastRefresh.toLocaleTimeString()}
          </span>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div
          style={{
            padding: '20px',
            backgroundColor: error.includes('authenticated') ? '#e7f3ff' : '#f8d7da',
            color: error.includes('authenticated') ? '#004085' : '#721c24',
            border: `1px solid ${error.includes('authenticated') ? '#b8daff' : '#f5c6cb'}`,
            borderRadius: '4px',
            marginBottom: '20px',
          }}
        >
          <strong>{error.includes('authenticated') ? 'Authentication Required' : 'Error'}</strong>
          <p style={{ margin: '10px 0 0 0' }}>
            {error}
            {error.includes('authenticated') && (
              <>
                <br />
                <small>Please login first, then alerts will appear here automatically.</small>
              </>
            )}
          </p>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
          <p>Loading alerts...</p>
        </div>
      )}

      {/* No Alerts */}
      {!loading && alerts.length === 0 && !error && (
        <div
          style={{
            padding: '40px',
            backgroundColor: '#d4edda',
            color: '#155724',
            borderRadius: '4px',
            textAlign: 'center',
          }}
        >
          <h3>✅ All Clear!</h3>
          <p>No active alerts at the moment.</p>
        </div>
      )}

      {/* Alerts Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))',
          gap: '20px',
        }}
      >
        {alerts.map(alert => (
          <div
            key={alert.id}
            style={{
              border: `3px solid ${getPriorityColor(alert.priority)}`,
              borderRadius: '8px',
              padding: '20px',
              backgroundColor: '#f9f9f9',
              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
              transition: 'transform 0.2s',
            }}
            onMouseEnter={e => {
              (e.currentTarget as HTMLElement).style.transform = 'translateY(-4px)';
            }}
            onMouseLeave={e => {
              (e.currentTarget as HTMLElement).style.transform = 'translateY(0)';
            }}
          >
            {/* Alert Priority Badge */}
            <div
              style={{
                display: 'inline-block',
                backgroundColor: getPriorityColor(alert.priority),
                color: 'white',
                padding: '6px 12px',
                borderRadius: '4px',
                fontSize: '12px',
                fontWeight: 'bold',
                marginBottom: '12px',
              }}
            >
              {getPriorityLabel(alert.priority)}
            </div>

            {/* Patient Info */}
            <h3 style={{ margin: '10px 0', fontSize: '18px', color: '#333' }}>
              {alert.patient_name || `Patient #${alert.patient}`}
            </h3>

            {/* Alert Details */}
            <div style={{ margin: '15px 0', fontSize: '14px', color: '#666' }}>
              <p>
                <strong>Type:</strong> {alert.alert_type.replace('_', ' ').toUpperCase()}
              </p>
              <p>
                <strong>Reason:</strong> {alert.trigger_reason}
              </p>
              <p>
                <strong>Time:</strong>{' '}
                {new Date(alert.triggered_at).toLocaleString()}
              </p>
            </div>

            {/* Acknowledge Button */}
            <button
              onClick={() => acknowledgeAlert(alert.id)}
              style={{
                width: '100%',
                padding: '10px',
                marginTop: '10px',
                backgroundColor: '#28a745',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: 'bold',
                transition: 'background-color 0.2s',
              }}
              onMouseEnter={e => {
                (e.target as HTMLElement).style.backgroundColor = '#218838';
              }}
              onMouseLeave={e => {
                (e.target as HTMLElement).style.backgroundColor = '#28a745';
              }}
            >
              ✓ Acknowledge Alert
            </button>
          </div>
        ))}
      </div>

      {/* Alert Count */}
      {!loading && alerts.length > 0 && (
        <div style={{ marginTop: '30px', textAlign: 'center', color: '#666', fontSize: '14px' }}>
          Showing {alerts.length} active alert{alerts.length !== 1 ? 's' : ''}
        </div>
      )}
    </div>
  );
}
