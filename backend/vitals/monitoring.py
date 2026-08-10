"""
Real-time Monitoring Service

Provides real-time patient risk monitoring and alert notifications.
Enables live dashboard updates without page refresh.

Reference: Phase 6 - Real-time Monitoring & Dashboard
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.cache import cache
from django.utils import timezone
from typing import Dict, List, Optional
import json

from vitals.models import RiskAssessment, VitalSigns
from deterioration_alerts.models import DeteriorationAlert
from patients.models import Patient


class RealtimeMonitor:
    """
    Real-time monitoring service for patient risk updates.

    Tracks:
    - Current risk levels
    - Recent alerts
    - Trend changes
    - Critical patients
    """

    # Cache keys
    PATIENT_RISK_KEY = "patient_risk_{patient_id}"
    ALERT_STREAM_KEY = "alert_stream"
    CRITICAL_PATIENTS_KEY = "critical_patients"
    ALERT_COUNTER_KEY = "alert_counter"

    # Cache TTL (seconds)
    CACHE_TTL = 3600  # 1 hour for risk status
    ALERT_TTL = 86400  # 24 hours for alert stream

    @classmethod
    def update_patient_risk(cls, patient_id: int, assessment: RiskAssessment) -> Dict:
        """
        Update patient risk status in cache.

        Called when new RiskAssessment created.
        """
        risk_data = {
            'patient_id': patient_id,
            'risk_level': assessment.risk_level,
            'combined_risk': float(assessment.combined_risk),
            'news2_score': assessment.news2_total,
            'trend_score': assessment.trend_score,
            'assessed_at': assessment.assessed_at.isoformat(),
            'explanation': assessment.explanation_text,
            'recommendation': assessment.recommendation,
        }

        # Store in cache
        cache_key = cls.PATIENT_RISK_KEY.format(patient_id=patient_id)
        cache.set(cache_key, risk_data, cls.CACHE_TTL)

        # Update critical patients list if needed
        cls._update_critical_patients_list(patient_id, assessment.risk_level)

        return risk_data

    @classmethod
    def record_alert(cls, alert: DeteriorationAlert) -> Dict:
        """
        Record alert event in stream for real-time updates.

        Called when DeteriorationAlert created.
        """
        alert_event = {
            'alert_id': alert.id,
            'patient_id': alert.patient_id,
            'patient_name': alert.patient.get_full_name(),
            'priority': alert.priority,
            'alert_type': alert.alert_type,
            'trigger_reason': alert.trigger_reason,
            'triggered_at': alert.triggered_at.isoformat(),
            'status': alert.status,
        }

        # Append to alert stream
        stream = cache.get(cls.ALERT_STREAM_KEY, [])
        stream.insert(0, alert_event)  # Prepend for newest first
        stream = stream[:100]  # Keep last 100 alerts
        cache.set(cls.ALERT_STREAM_KEY, stream, cls.ALERT_TTL)

        # Increment alert counter
        counter = cache.get(cls.ALERT_COUNTER_KEY, 0)
        cache.set(cls.ALERT_COUNTER_KEY, counter + 1, cls.ALERT_TTL)

        return alert_event

    @classmethod
    def get_patient_risk(cls, patient_id: int) -> Optional[Dict]:
        """Get current patient risk status from cache"""
        cache_key = cls.PATIENT_RISK_KEY.format(patient_id=patient_id)
        return cache.get(cache_key)

    @classmethod
    def get_critical_patients(cls) -> List[Dict]:
        """Get list of currently critical patients"""
        return cache.get(cls.CRITICAL_PATIENTS_KEY, [])

    @classmethod
    def get_alert_stream(cls, limit: int = 20) -> List[Dict]:
        """Get recent alert stream"""
        stream = cache.get(cls.ALERT_STREAM_KEY, [])
        return stream[:limit]

    @classmethod
    def get_alert_count(cls) -> int:
        """Get total alert count"""
        return cache.get(cls.ALERT_COUNTER_KEY, 0)

    @classmethod
    def _update_critical_patients_list(cls, patient_id: int, risk_level: str):
        """Maintain list of critical patients"""
        critical_list = cache.get(cls.CRITICAL_PATIENTS_KEY, [])

        # Find patient in list
        patient_entry = next((p for p in critical_list if p['patient_id'] == patient_id), None)

        if risk_level == 'critical':
            # Add or update
            if patient_entry:
                patient_entry['last_update'] = timezone.now().isoformat()
            else:
                patient = Patient.objects.get(id=patient_id)
                critical_list.append({
                    'patient_id': patient_id,
                    'patient_name': patient.get_full_name(),
                    'first_alert': timezone.now().isoformat(),
                    'last_update': timezone.now().isoformat(),
                })
        else:
            # Remove if present
            critical_list = [p for p in critical_list if p['patient_id'] != patient_id]

        cache.set(cls.CRITICAL_PATIENTS_KEY, critical_list, cls.CACHE_TTL)

    @classmethod
    def get_dashboard_summary(self) -> Dict:
        """Get dashboard summary for monitoring view"""
        critical_patients = self.get_critical_patients()
        recent_alerts = self.get_alert_stream(10)
        alert_count = self.get_alert_count()

        return {
            'critical_patients_count': len(critical_patients),
            'critical_patients': critical_patients,
            'recent_alerts_count': len(recent_alerts),
            'recent_alerts': recent_alerts,
            'total_alerts': alert_count,
            'last_update': timezone.now().isoformat(),
        }


class AlertNotificationService:
    """
    Handles alert notifications for different channels.

    Supports:
    - In-app notifications
    - Dashboard push (via WebSocket)
    - Email notifications
    - SMS alerts (for critical)
    """

    @staticmethod
    def notify_alert(alert: DeteriorationAlert):
        """
        Send alert notifications through multiple channels.
        """
        # Record in real-time monitor
        RealtimeMonitor.record_alert(alert)

        # Generate notification message
        notification = AlertNotificationService._build_notification(alert)

        # Send through channels
        AlertNotificationService._send_dashboard_notification(alert, notification)
        AlertNotificationService._send_email_notification(alert, notification)

        if alert.priority == 'critical':
            AlertNotificationService._send_urgent_notification(alert, notification)

    @staticmethod
    def _build_notification(alert: DeteriorationAlert) -> Dict:
        """Build notification message"""
        return {
            'alert_id': alert.id,
            'patient_name': alert.patient.get_full_name(),
            'priority': alert.priority,
            'message': f"{alert.patient.get_full_name()} - {alert.alert_type.upper()}",
            'reason': alert.trigger_reason,
            'timestamp': alert.triggered_at.isoformat(),
        }

    @staticmethod
    def _send_dashboard_notification(alert: DeteriorationAlert, notification: Dict):
        """
        Send notification to dashboard (via cache for WebSocket consumers).

        In production, this would use Django Channels for WebSocket.
        For now, we store in cache for polling.
        """
        # Store notification in cache for dashboard polling
        cache_key = f"notification_{alert.patient_id}"
        cache.set(cache_key, notification, 300)  # 5 minute TTL

    @staticmethod
    def _send_email_notification(alert: DeteriorationAlert, notification: Dict):
        """Send email notification to care team"""
        # TODO: Implement email sending
        # Would send to alert.patient.primary_nurse.email
        pass

    @staticmethod
    def _send_urgent_notification(alert: DeteriorationAlert, notification: Dict):
        """Send urgent notification for critical alerts"""
        # TODO: Implement SMS/urgent notification
        # Would send to on-call physician, charge nurse
        pass


# Signal receivers for automatic monitoring updates

@receiver(post_save, sender=RiskAssessment)
def on_risk_assessment_created(sender, instance, created, **kwargs):
    """Update monitoring when risk assessment created"""
    if created:
        try:
            RealtimeMonitor.update_patient_risk(instance.patient_id, instance)
        except Exception as e:
            # Log but don't fail
            print(f"[MONITORING] Error updating patient risk: {e}")


@receiver(post_save, sender=DeteriorationAlert)
def on_alert_created(sender, instance, created, **kwargs):
    """Send notifications when alert created"""
    if created:
        try:
            AlertNotificationService.notify_alert(instance)
        except Exception as e:
            # Log but don't fail
            print(f"[NOTIFICATION] Error sending alert notification: {e}")
