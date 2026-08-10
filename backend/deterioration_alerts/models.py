from django.db import models
from django.utils import timezone
from patients.models import Patient
from vitals.models import VitalSigns
from accounts.models import User


class TrendAnalysis(models.Model):
    """Store trend analysis results for each patient"""
    WINDOW_CHOICES = [(4, '4 readings'), (8, '8 readings'), (12, '12 readings')]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='trend_analyses')
    window_size = models.IntegerField(choices=WINDOW_CHOICES, default=8, help_text='Number of readings in trend window')

    # Trend metrics
    news2_trend_slope = models.FloatField(help_text='Rate of change in NEWS2 score (per reading)')
    news2_avg_current = models.FloatField(help_text='Average NEWS2 over current window')
    news2_avg_previous = models.FloatField(help_text='Average NEWS2 over previous window')

    # Individual vital trends (slope per reading)
    temp_trend = models.FloatField(null=True, blank=True)
    hr_trend = models.FloatField(null=True, blank=True)
    rr_trend = models.FloatField(null=True, blank=True)
    spo2_trend = models.FloatField(null=True, blank=True)
    bp_systolic_trend = models.FloatField(null=True, blank=True)

    # Severity classification
    SEVERITY_CHOICES = [
        ('stable', 'Stable - No trend'),
        ('improving', 'Improving - Downward trend'),
        ('declining', 'Declining - Upward trend'),
        ('critical', 'Critical - Rapid decline detected'),
    ]
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='stable')

    # Risk score (0-100) based on trend + absolute values
    risk_score = models.IntegerField(default=0, help_text='Combined risk from trends and current values')

    # Timestamps
    analysed_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-analysed_at']
        verbose_name_plural = 'Trend Analyses'
        indexes = [
            models.Index(fields=['patient', '-analysed_at']),
            models.Index(fields=['severity']),
        ]

    def __str__(self):
        return f'{self.patient} - {self.severity} (Risk: {self.risk_score}%)'


class DeteriorationAlert(models.Model):
    """Alerts triggered by deterioration detection"""
    ALERT_TYPE_CHOICES = [
        ('threshold_breach', 'NEWS2 Threshold Breach (>=7)'),
        ('trend_rise', 'Rapid Trend Rise (slope > 0.5)'),
        ('sustained_elevation', 'Sustained Elevation (2+ readings high)'),
        ('combined_risk', 'Combined Risk Factors'),
        ('ml_prediction', 'ML Model Prediction'),
        ('research_deterioration_detection', 'Research Deterioration Detection (Phase 4)'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'CRITICAL'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active - Not reviewed'),
        ('acknowledged', 'Acknowledged'),
        ('resolved', 'Resolved'),
        ('suppressed', 'Suppressed'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='deterioration_alerts')
    alert_type = models.CharField(max_length=50, choices=ALERT_TYPE_CHOICES)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    # Alert details
    trigger_value = models.FloatField(help_text='NEWS2 score or trend slope that triggered alert')
    trigger_reason = models.CharField(max_length=255, help_text='Why this alert was triggered')

    # Timeline
    triggered_at = models.DateTimeField(auto_now_add=True)
    acknowledged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='acknowledged_alerts')
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    # Related analysis
    related_vital = models.ForeignKey(VitalSigns, on_delete=models.SET_NULL, null=True, blank=True, related_name='deterioration_alerts')
    related_trend = models.ForeignKey(TrendAnalysis, on_delete=models.SET_NULL, null=True, blank=True)
    risk_assessment = models.ForeignKey('vitals.RiskAssessment', on_delete=models.SET_NULL, null=True, blank=True, related_name='alerts')

    # Alert fatigue suppression
    is_suppressed = models.BooleanField(default=False)
    suppression_reason = models.CharField(max_length=255, blank=True, help_text='Why this alert was suppressed')

    class Meta:
        ordering = ['-triggered_at']
        verbose_name_plural = 'Deterioration Alerts'
        indexes = [
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['priority', 'status']),
            models.Index(fields=['triggered_at']),
        ]

    def __str__(self):
        return f'{self.patient} - {self.alert_type} ({self.priority})'

    def acknowledge(self, user):
        """Mark alert as acknowledged by care staff"""
        self.status = 'acknowledged'
        self.acknowledged_by = user
        self.acknowledged_at = timezone.now()
        self.save()
        return self

    def resolve(self):
        """Mark alert as resolved"""
        self.status = 'resolved'
        self.resolved_at = timezone.now()
        self.save()
        return self


class AlertSuppressionRule(models.Model):
    """Rules to suppress repetitive alerts (combat alert fatigue)"""
    RULE_TYPE_CHOICES = [
        ('time_based', 'Suppress for X minutes'),
        ('count_based', 'Suppress if >X alerts in Y minutes'),
    ]

    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name='suppression_rules',
        null=True, blank=True, help_text='Leave blank for system-wide rule'
    )
    rule_type = models.CharField(max_length=20, choices=RULE_TYPE_CHOICES)

    # Time-based: suppress next alert for N minutes
    suppress_minutes = models.IntegerField(default=15, help_text='Minutes to suppress after first alert')

    # Count-based: if >X alerts in Y minutes, suppress remainder
    alert_threshold = models.IntegerField(default=3, help_text='Number of alerts before suppression kicks in')
    time_window_minutes = models.IntegerField(default=30, help_text='Time window for counting alerts')

    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, help_text='Notes on why this rule was created')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Suppression Rule: {self.rule_type}'


class DeteriorationEventLog(models.Model):
    """Audit log of all deterioration events for research/analysis"""
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='event_logs')

    # Event metadata
    event_type = models.CharField(
        max_length=100,
        help_text='e.g., NEWS2_SCORE_RECORDED, TREND_CALCULATED, ALERT_TRIGGERED'
    )
    severity_at_event = models.CharField(max_length=20, help_text='Patient severity at time of event')

    # Details
    data_snapshot = models.JSONField(help_text='Snapshot of vitals/scores at time of event')
    notes = models.TextField(blank=True)

    # Timeline
    logged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-logged_at']
        verbose_name_plural = 'Deterioration Event Logs'
        indexes = [
            models.Index(fields=['patient', '-logged_at']),
            models.Index(fields=['event_type']),
        ]

    def __str__(self):
        return f'{self.patient} - {self.event_type} at {self.logged_at}'
