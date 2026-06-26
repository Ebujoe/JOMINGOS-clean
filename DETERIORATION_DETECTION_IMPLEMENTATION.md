# JOMINGOS: Early Deterioration Detection System Implementation Guide

## Overview
Your JOMINGOS app already has **NEWS2 scoring implemented** in `VitalSigns` model. This guide adds **trend analysis** on top to detect gradual deterioration 24-48 hours before crisis.

---

## PHASE 1: DATABASE & MODELS (Week 1-2)

### 1.1 Create New Django App for Deterioration Detection

```bash
cd backend
python manage.py startapp deterioration_alerts
```

Add to `backend/Jomingos/settings.py`:
```python
INSTALLED_APPS = [
    # ... existing apps ...
    'deterioration_alerts',
]
```

### 1.2 Create Models for Trend Tracking & Alerts

**File:** `backend/deterioration_alerts/models.py`

```python
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
    
    def __str__(self):
        return f'{self.patient} - {self.severity} (Risk: {self.risk_score}%)'


class DeteriorationAlert(models.Model):
    """Alerts triggered by deterioration detection"""
    ALERT_TYPE_CHOICES = [
        ('threshold_breach', 'NEWS2 Threshold Breach'),
        ('trend_rise', 'Rapid Trend Rise'),
        ('sustained_elevation', 'Sustained Elevation (2+ readings high)'),
        ('combined_risk', 'Combined Risk Factors'),
    ]
    
    PRIORITY_CHOICES = [('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'CRITICAL')]
    STATUS_CHOICES = [('active', 'Active - Not reviewed'), ('acknowledged', 'Acknowledged'), ('resolved', 'Resolved'), ('suppressed', 'Suppressed')]
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='deterioration_alerts')
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPE_CHOICES)
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
    related_vital = models.ForeignKey(VitalSigns, on_delete=models.SET_NULL, null=True, blank=True)
    related_trend = models.ForeignKey(TrendAnalysis, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Alert fatigue suppression
    is_suppressed = models.BooleanField(default=False)
    suppression_reason = models.CharField(max_length=255, blank=True, help_text='Why this alert was suppressed')
    
    class Meta:
        ordering = ['-triggered_at']
        indexes = [
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['priority', 'status']),
        ]
    
    def __str__(self):
        return f'{self.patient} - {self.alert_type} ({self.priority})'
    
    def acknowledge(self, user):
        """Mark alert as acknowledged by staff"""
        self.status = 'acknowledged'
        self.acknowledged_by = user
        self.acknowledged_at = timezone.now()
        self.save()
    
    def resolve(self):
        """Mark alert as resolved"""
        self.status = 'resolved'
        self.resolved_at = timezone.now()
        self.save()


class AlertSuppressionRule(models.Model):
    """Rules to suppress repetitive alerts (combat alert fatigue)"""
    RULE_TYPE_CHOICES = [
        ('time_based', 'Suppress for X minutes'),
        ('count_based', 'Suppress if >X alerts in Y minutes'),
        ('condition_based', 'Suppress if specific condition met'),
    ]
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='suppression_rules', null=True, blank=True)
    rule_type = models.CharField(max_length=20, choices=RULE_TYPE_CHOICES)
    
    # Time-based: suppress next alert for N minutes
    suppress_minutes = models.IntegerField(default=15, help_text='Minutes to suppress after first alert')
    
    # Count-based: if >X alerts in Y minutes, suppress remainder
    alert_threshold = models.IntegerField(default=3, help_text='Number of alerts before suppression')
    time_window_minutes = models.IntegerField(default=30, help_text='Time window for counting alerts')
    
    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f'Suppression Rule: {self.rule_type}'


class DeteriorationEventLog(models.Model):
    """Audit log of all deterioration events for research/analysis"""
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='event_logs')
    
    # Event metadata
    event_type = models.CharField(max_length=100, help_text='e.g., NEWS2_SCORE_RECORDED, TREND_CALCULATED, ALERT_TRIGGERED')
    severity_at_event = models.CharField(max_length=20, help_text='Patient severity at time of event')
    
    # Details
    data_snapshot = models.JSONField(help_text='Snapshot of vitals/scores at time of event')
    notes = models.TextField(blank=True)
    
    # Timeline
    logged_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-logged_at']
        verbose_name_plural = 'Deterioration Event Logs'
    
    def __str__(self):
        return f'{self.patient} - {self.event_type} at {self.logged_at}'
```

### 1.3 Create Migrations

```bash
python manage.py makemigrations deterioration_alerts
python manage.py migrate deterioration_alerts
```

---

## PHASE 2: TREND ANALYSIS ENGINE (Week 2-3)

### 2.1 Trend Analysis Service

**File:** `backend/deterioration_alerts/services.py`

```python
import numpy as np
from datetime import timedelta
from django.utils import timezone
from vitals.models import VitalSigns
from patients.models import Patient
from .models import TrendAnalysis, DeteriorationAlert, DeteriorationEventLog


class TrendAnalysisService:
    """Core trend detection engine"""
    
    def __init__(self, patient, window_size=8):
        self.patient = patient
        self.window_size = window_size
    
    def get_recent_vitals(self, limit=None):
        """Get recent vitals for patient, ordered chronologically (oldest first)"""
        if limit is None:
            limit = self.window_size * 3  # Get extra for comparison windows
        
        vitals = VitalSigns.objects.filter(patient=self.patient).order_by('recorded_at')[:limit]
        return list(vitals)
    
    def extract_vital_series(self, vitals, vital_name):
        """Extract time series for a specific vital (e.g., 'heart_rate', 'news2_total')"""
        series = []
        for v in vitals:
            if vital_name == 'news2_total':
                value = v.news2_total
            elif vital_name == 'temperature':
                value = float(v.temperature) if v.temperature else None
            elif vital_name == 'heart_rate':
                value = v.heart_rate
            elif vital_name == 'respiratory_rate':
                value = v.respiratory_rate
            elif vital_name == 'oxygen_saturation':
                value = float(v.oxygen_saturation) if v.oxygen_saturation else None
            elif vital_name == 'bp_systolic':
                value = v.bp_systolic
            else:
                value = None
            
            if value is not None:
                series.append(value)
        
        return series
    
    def calculate_trend_slope(self, values):
        """Calculate linear regression slope for trend"""
        if len(values) < 2:
            return 0.0
        
        try:
            x = np.arange(len(values))
            coefficients = np.polyfit(x, values, 1)  # Linear fit
            return float(coefficients[0])  # Return slope
        except Exception:
            return 0.0
    
    def analyze_trends(self):
        """
        Main trend analysis - calculates slopes and severity
        Returns TrendAnalysis object (not saved yet)
        """
        vitals = self.get_recent_vitals(limit=self.window_size * 2)
        
        if len(vitals) < self.window_size:
            return None  # Not enough data
        
        # Split into current and previous windows
        current_window = vitals[-self.window_size:]
        previous_window = vitals[-self.window_size*2:-self.window_size]
        
        # Extract NEWS2 series
        current_news2 = self.extract_vital_series(current_window, 'news2_total')
        previous_news2 = self.extract_vital_series(previous_window, 'news2_total')
        
        # Calculate NEWS2 trend
        news2_trend_slope = self.calculate_trend_slope(current_news2)
        news2_avg_current = np.mean(current_news2) if current_news2 else 0
        news2_avg_previous = np.mean(previous_news2) if previous_news2 else 0
        
        # Calculate individual vital trends
        temp_series = self.extract_vital_series(current_window, 'temperature')
        hr_series = self.extract_vital_series(current_window, 'heart_rate')
        rr_series = self.extract_vital_series(current_window, 'respiratory_rate')
        spo2_series = self.extract_vital_series(current_window, 'oxygen_saturation')
        bp_series = self.extract_vital_series(current_window, 'bp_systolic')
        
        temp_trend = self.calculate_trend_slope(temp_series)
        hr_trend = self.calculate_trend_slope(hr_series)
        rr_trend = self.calculate_trend_slope(rr_series)
        spo2_trend = self.calculate_trend_slope(spo2_series)
        bp_trend = self.calculate_trend_slope(bp_series)
        
        # Determine severity
        severity, risk_score = self._classify_severity(
            news2_trend_slope, news2_avg_current, news2_avg_previous,
            hr_trend, rr_trend, spo2_trend, temp_trend, bp_trend
        )
        
        # Create and return analysis
        analysis = TrendAnalysis(
            patient=self.patient,
            window_size=self.window_size,
            news2_trend_slope=news2_trend_slope,
            news2_avg_current=news2_avg_current,
            news2_avg_previous=news2_avg_previous,
            temp_trend=temp_trend,
            hr_trend=hr_trend,
            rr_trend=rr_trend,
            spo2_trend=spo2_trend,
            bp_systolic_trend=bp_trend,
            severity=severity,
            risk_score=risk_score,
        )
        
        return analysis
    
    def _classify_severity(self, news2_slope, news2_curr, news2_prev, hr_slope, rr_slope, spo2_slope, temp_slope, bp_slope):
        """Classify patient severity based on trends"""
        risk_score = 0
        
        # NEWS2 absolute risk
        if news2_curr >= 7:
            risk_score += 40
        elif news2_curr >= 5:
            risk_score += 25
        elif news2_curr >= 3:
            risk_score += 15
        
        # NEWS2 trend risk (upward = dangerous)
        if news2_slope > 0.5:  # Rising >0.5 per reading
            risk_score += 30
        elif news2_slope > 0.2:
            risk_score += 15
        
        # Multiple vital trends rising
        rising_vitals = sum([
            1 for trend in [hr_slope, rr_slope, bp_slope]
            if trend and trend > 0.3
        ])
        risk_score += rising_vitals * 10
        
        # Falling SpO2 is very dangerous
        if spo2_slope and spo2_slope < -0.5:
            risk_score += 20
        
        # Rising temperature (fever)
        if temp_slope and temp_slope > 0.2:
            risk_score += 10
        
        risk_score = min(risk_score, 100)
        
        # Severity classification
        if news2_slope > 0.5 or (news2_slope > 0.2 and news2_curr >= 5):
            severity = 'critical'
        elif news2_slope > 0.1 and news2_curr >= 3:
            severity = 'declining'
        elif news2_slope < -0.1:
            severity = 'improving'
        else:
            severity = 'stable'
        
        return severity, risk_score


class AlertGenerationService:
    """Generates alerts based on trends and thresholds"""
    
    ALERT_THRESHOLDS = {
        'threshold_breach': 7,  # NEWS2 score
        'trend_rise_slope': 0.5,  # Per reading
        'sustained_high': (5, 2),  # (score, readings_count)
    }
    
    @staticmethod
    def check_and_create_alerts(patient):
        """
        Main alert generation method
        Called after each vital is recorded
        """
        alerts_created = []
        
        # Get latest vital
        latest_vital = VitalSigns.objects.filter(patient=patient).order_by('-recorded_at').first()
        if not latest_vital:
            return alerts_created
        
        # Check for NEWS2 threshold breach
        if latest_vital.news2_total >= AlertGenerationService.ALERT_THRESHOLDS['threshold_breach']:
            alert = AlertGenerationService._create_alert(
                patient=patient,
                alert_type='threshold_breach',
                priority='high' if latest_vital.news2_total >= 9 else 'medium',
                trigger_value=latest_vital.news2_total,
                trigger_reason=f'NEWS2 score {latest_vital.news2_total} exceeds threshold of 7',
                related_vital=latest_vital,
            )
            alerts_created.append(alert)
        
        # Check for sustained elevation
        recent_vitals = VitalSigns.objects.filter(patient=patient).order_by('-recorded_at')[:3]
        if len(recent_vitals) >= 2:
            recent_scores = [v.news2_total for v in recent_vitals]
            if all(score >= AlertGenerationService.ALERT_THRESHOLDS['sustained_high'][0] for score in recent_scores):
                alert = AlertGenerationService._create_alert(
                    patient=patient,
                    alert_type='sustained_elevation',
                    priority='medium',
                    trigger_value=sum(recent_scores) / len(recent_scores),
                    trigger_reason=f'NEWS2 sustained ≥5 over {len(recent_scores)} readings',
                    related_vital=latest_vital,
                )
                alerts_created.append(alert)
        
        # Check for rapid trend
        service = TrendAnalysisService(patient, window_size=8)
        trend_analysis = service.analyze_trends()
        if trend_analysis:
            trend_analysis.save()
            if trend_analysis.news2_trend_slope > AlertGenerationService.ALERT_THRESHOLDS['trend_rise_slope']:
                alert = AlertGenerationService._create_alert(
                    patient=patient,
                    alert_type='trend_rise',
                    priority='critical',
                    trigger_value=trend_analysis.news2_trend_slope,
                    trigger_reason=f'Rapid NEWS2 rise detected: +{trend_analysis.news2_trend_slope:.2f} per reading',
                    related_vital=latest_vital,
                    related_trend=trend_analysis,
                )
                alerts_created.append(alert)
        
        # Check suppression rules before finalizing
        for alert in alerts_created:
            if AlertGenerationService._should_suppress_alert(patient, alert):
                alert.is_suppressed = True
                alert.suppression_reason = 'Alert fatigue suppression rule applied'
        
        # Log all alerts
        for alert in alerts_created:
            alert.save()
            DeteriorationEventLog.objects.create(
                patient=patient,
                event_type='ALERT_TRIGGERED',
                severity_at_event=trend_analysis.severity if trend_analysis else 'unknown',
                data_snapshot={
                    'alert_type': alert.alert_type,
                    'priority': alert.priority,
                    'trigger_value': str(alert.trigger_value),
                    'news2_score': latest_vital.news2_total,
                }
            )
        
        return alerts_created
    
    @staticmethod
    def _create_alert(patient, alert_type, priority, trigger_value, trigger_reason, related_vital, related_trend=None):
        """Create alert object (not saved yet)"""
        return DeteriorationAlert(
            patient=patient,
            alert_type=alert_type,
            priority=priority,
            status='active',
            trigger_value=trigger_value,
            trigger_reason=trigger_reason,
            related_vital=related_vital,
            related_trend=related_trend,
        )
    
    @staticmethod
    def _should_suppress_alert(patient, new_alert):
        """Check if alert should be suppressed based on rules"""
        from .models import AlertSuppressionRule
        
        rules = AlertSuppressionRule.objects.filter(is_active=True, patient__isnull=True)
        
        for rule in rules:
            if rule.rule_type == 'time_based':
                # Check if alert was recently triggered
                recent_alerts = DeteriorationAlert.objects.filter(
                    patient=patient,
                    triggered_at__gte=timezone.now() - timedelta(minutes=rule.suppress_minutes)
                ).exclude(status='suppressed').count()
                
                if recent_alerts > 0:
                    return True
            
            elif rule.rule_type == 'count_based':
                # Suppress if too many alerts in time window
                alert_count = DeteriorationAlert.objects.filter(
                    patient=patient,
                    triggered_at__gte=timezone.now() - timedelta(minutes=rule.time_window_minutes)
                ).exclude(status='suppressed').count()
                
                if alert_count >= rule.alert_threshold:
                    return True
        
        return False
```

---

## PHASE 3: API ENDPOINTS & SIGNALS (Week 3-4)

### 3.1 Update VitalSigns to Trigger Analysis

**File:** `backend/vitals/models.py` (Add to existing file)

Add to imports:
```python
from django.db.models.signals import post_save
from django.dispatch import receiver
```

Add at bottom:
```python
@receiver(post_save, sender=VitalSigns)
def trigger_deterioration_check(sender, instance, created, **kwargs):
    """Automatically check for deterioration when vital is recorded"""
    if created:  # Only on new vital sign records
        from deterioration_alerts.services import AlertGenerationService
        AlertGenerationService.check_and_create_alerts(instance.patient)
```

### 3.2 Create API Views

**File:** `backend/deterioration_alerts/views_api.py`

```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from patients.models import Patient
from vitals.models import VitalSigns
from .models import DeteriorationAlert, TrendAnalysis
from .serializers import (
    DeteriorationAlertSerializer, TrendAnalysisSerializer,
    AlertDetailSerializer
)
from .services import TrendAnalysisService, AlertGenerationService


class DeteriorationAlertViewSet(viewsets.ModelViewSet):
    """
    Endpoints for deterioration alerts
    - List active alerts
    - Acknowledge/resolve alerts
    - Get alerts by patient
    """
    permission_classes = [IsAuthenticated]
    serializer_class = DeteriorationAlertSerializer
    queryset = DeteriorationAlert.objects.all()
    
    def get_queryset(self):
        """Filter by patient and role"""
        if self.request.user.role == 'care_staff':
            # Care staff see only alerts for their patients
            from accounts.role_access import get_accessible_patients
            accessible = get_accessible_patients(self.request.user)
            return DeteriorationAlert.objects.filter(patient__in=accessible)
        else:
            return DeteriorationAlert.objects.all()
    
    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """Mark alert as acknowledged"""
        alert = self.get_object()
        alert.acknowledge(request.user)
        serializer = self.get_serializer(alert)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Mark alert as resolved"""
        alert = self.get_object()
        alert.resolve()
        serializer = self.get_serializer(alert)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def active_alerts(self, request):
        """Get all active, unacknowledged alerts"""
        alerts = self.get_queryset().filter(status='active')
        serializer = self.get_serializer(alerts, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def critical_alerts(self, request):
        """Get only CRITICAL priority alerts"""
        alerts = self.get_queryset().filter(priority='critical', status__in=['active', 'acknowledged'])
        serializer = self.get_serializer(alerts, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_patient(self, request):
        """Get alerts for specific patient"""
        patient_id = request.query_params.get('patient_id')
        if not patient_id:
            return Response({'error': 'patient_id required'}, status=status.HTTP_400_BAD_REQUEST)
        
        alerts = self.get_queryset().filter(patient_id=patient_id)
        serializer = self.get_serializer(alerts, many=True)
        return Response(serializer.data)


class TrendAnalysisViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only endpoint for trend analysis results
    - Get latest trend for patient
    - Get trend history
    """
    permission_classes = [IsAuthenticated]
    serializer_class = TrendAnalysisSerializer
    queryset = TrendAnalysis.objects.all()
    
    @action(detail=False, methods=['get'])
    def patient_latest(self, request):
        """Get latest trend analysis for patient"""
        patient_id = request.query_params.get('patient_id')
        if not patient_id:
            return Response({'error': 'patient_id required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            patient = Patient.objects.get(pk=patient_id)
        except Patient.DoesNotExist:
            return Response({'error': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)
        
        latest = TrendAnalysis.objects.filter(patient=patient).order_by('-analysed_at').first()
        if not latest:
            return Response({'message': 'No trend analysis yet'}, status=status.HTTP_204_NO_CONTENT)
        
        serializer = self.get_serializer(latest)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def patient_history(self, request):
        """Get trend analysis history for patient (last 7 days)"""
        patient_id = request.query_params.get('patient_id')
        if not patient_id:
            return Response({'error': 'patient_id required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            patient = Patient.objects.get(pk=patient_id)
        except Patient.DoesNotExist:
            return Response({'error': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)
        
        seven_days_ago = timezone.now() - timezone.timedelta(days=7)
        trends = TrendAnalysis.objects.filter(
            patient=patient,
            analysed_at__gte=seven_days_ago
        ).order_by('-analysed_at')
        
        serializer = self.get_serializer(trends, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def trigger_analysis(self, request):
        """Manually trigger trend analysis for a patient"""
        patient_id = request.data.get('patient_id')
        window_size = request.data.get('window_size', 8)
        
        try:
            patient = Patient.objects.get(pk=patient_id)
        except Patient.DoesNotExist:
            return Response({'error': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)
        
        service = TrendAnalysisService(patient, window_size=window_size)
        analysis = service.analyze_trends()
        
        if analysis:
            analysis.save()
            serializer = self.get_serializer(analysis)
            return Response(serializer.data)
        
        return Response({'error': 'Not enough data for analysis'}, status=status.HTTP_400_BAD_REQUEST)
```

### 3.3 Create Serializers

**File:** `backend/deterioration_alerts/serializers.py`

```python
from rest_framework import serializers
from .models import DeteriorationAlert, TrendAnalysis
from patients.models import Patient
from vitals.models import VitalSigns


class DeteriorationAlertSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    acknowledged_by_name = serializers.CharField(source='acknowledged_by.get_full_name', read_only=True, allow_null=True)
    
    class Meta:
        model = DeteriorationAlert
        fields = [
            'id', 'patient', 'patient_name', 'alert_type', 'priority', 'status',
            'trigger_value', 'trigger_reason', 'triggered_at', 'acknowledged_at',
            'acknowledged_by', 'acknowledged_by_name', 'is_suppressed'
        ]
        read_only_fields = ['triggered_at', 'acknowledged_at']


class TrendAnalysisSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    
    class Meta:
        model = TrendAnalysis
        fields = [
            'id', 'patient', 'patient_name', 'window_size', 'news2_trend_slope',
            'news2_avg_current', 'news2_avg_previous', 'temp_trend', 'hr_trend',
            'rr_trend', 'spo2_trend', 'bp_systolic_trend', 'severity', 'risk_score',
            'analysed_at'
        ]
        read_only_fields = ['analysed_at']


class AlertDetailSerializer(serializers.ModelSerializer):
    """Detailed alert view with related vital signs data"""
    patient_details = serializers.SerializerMethodField()
    related_vital_data = serializers.SerializerMethodField()
    related_trend_data = serializers.SerializerMethodField()
    
    class Meta:
        model = DeteriorationAlert
        fields = '__all__'
    
    def get_patient_details(self, obj):
        return {
            'id': obj.patient.id,
            'name': obj.patient.get_full_name(),
            'age': obj.patient.get_age(),
            'care_level': obj.patient.care_level,
        }
    
    def get_related_vital_data(self, obj):
        if not obj.related_vital:
            return None
        return {
            'news2_score': obj.related_vital.news2_total,
            'news2_level': obj.related_vital.news2_level,
            'heart_rate': obj.related_vital.heart_rate,
            'respiratory_rate': obj.related_vital.respiratory_rate,
            'temperature': obj.related_vital.temperature,
            'oxygen_saturation': obj.related_vital.oxygen_saturation,
            'recorded_at': obj.related_vital.recorded_at,
        }
    
    def get_related_trend_data(self, obj):
        if not obj.related_trend:
            return None
        return {
            'severity': obj.related_trend.severity,
            'risk_score': obj.related_trend.risk_score,
            'news2_trend_slope': obj.related_trend.news2_trend_slope,
        }
```

### 3.4 Register API URLs

**File:** `backend/api/urls.py`

Add to imports:
```python
from deterioration_alerts.views_api import DeteriorationAlertViewSet, TrendAnalysisViewSet
```

Add to router:
```python
router.register(r'deterioration-alerts', DeteriorationAlertViewSet, basename='deterioration-alert')
router.register(r'trend-analysis', TrendAnalysisViewSet, basename='trend-analysis')
```

---

## PHASE 4: FRONTEND DASHBOARD (Week 4-5)

### 4.1 Create Alert Dashboard Component

**File:** `frontend/src/components/DeteriorationDashboard.tsx`

```typescript
import React, { useState, useEffect } from 'react';
import axios from 'axios';

interface Alert {
  id: number;
  patient_name: string;
  alert_type: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
  status: string;
  trigger_reason: string;
  triggered_at: string;
}

interface TrendAnalysis {
  patient_name: string;
  severity: string;
  risk_score: number;
  news2_trend_slope: number;
}

export const DeteriorationDashboard: React.FC = () => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [activeOnly, setActiveOnly] = useState(true);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchAlerts();
    // Refresh every 2 minutes
    const interval = setInterval(fetchAlerts, 120000);
    return () => clearInterval(interval);
  }, [activeOnly]);

  const fetchAlerts = async () => {
    setLoading(true);
    try {
      const endpoint = activeOnly
        ? '/api/deterioration-alerts/active_alerts/'
        : '/api/deterioration-alerts/';
      const response = await axios.get(endpoint);
      setAlerts(response.data);
    } catch (error) {
      console.error('Failed to fetch alerts:', error);
    } finally {
      setLoading(false);
    }
  };

  const acknowledgeAlert = async (alertId: number) => {
    try {
      await axios.post(`/api/deterioration-alerts/${alertId}/acknowledge/`);
      fetchAlerts();
    } catch (error) {
      console.error('Failed to acknowledge alert:', error);
    }
  };

  const resolveAlert = async (alertId: number) => {
    try {
      await axios.post(`/api/deterioration-alerts/${alertId}/resolve/`);
      fetchAlerts();
    } catch (error) {
      console.error('Failed to resolve alert:', error);
    }
  };

  const getPriorityColor = (priority: string) => {
    const colors = {
      low: 'info',
      medium: 'warning',
      high: 'danger',
      critical: 'danger',
    };
    return colors[priority as keyof typeof colors] || 'secondary';
  };

  return (
    <div className="container-fluid mt-4">
      <div className="row mb-4">
        <div className="col-md-8">
          <h2>🚨 Deterioration Detection Dashboard</h2>
        </div>
        <div className="col-md-4 text-end">
          <div className="form-check form-switch">
            <input
              className="form-check-input"
              type="checkbox"
              id="activeOnly"
              checked={activeOnly}
              onChange={(e) => setActiveOnly(e.target.checked)}
            />
            <label className="form-check-label" htmlFor="activeOnly">
              Active Alerts Only
            </label>
          </div>
        </div>
      </div>

      {loading && <div className="alert alert-info">Loading alerts...</div>}

      {alerts.length === 0 && !loading && (
        <div className="alert alert-success">✓ No active alerts</div>
      )}

      <div className="row">
        {alerts.map((alert) => (
          <div key={alert.id} className="col-md-6 mb-3">
            <div className={`card border-${getPriorityColor(alert.priority)}`}>
              <div className={`card-header bg-${getPriorityColor(alert.priority)} text-white`}>
                <strong>{alert.patient_name}</strong>
                <span className="badge ms-2">{alert.priority.toUpperCase()}</span>
              </div>
              <div className="card-body">
                <p className="card-text">
                  <strong>Type:</strong> {alert.alert_type.replace('_', ' ')}
                </p>
                <p className="card-text">
                  <strong>Reason:</strong> {alert.trigger_reason}
                </p>
                <p className="card-text text-muted small">
                  <strong>Triggered:</strong> {new Date(alert.triggered_at).toLocaleString()}
                </p>
                <div className="btn-group" role="group">
                  {alert.status === 'active' && (
                    <button
                      className="btn btn-sm btn-warning"
                      onClick={() => acknowledgeAlert(alert.id)}
                    >
                      Acknowledge
                    </button>
                  )}
                  <button
                    className="btn btn-sm btn-success"
                    onClick={() => resolveAlert(alert.id)}
                  >
                    Resolve
                  </button>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
```

### 4.2 Add to Patient Details Page

**File:** `frontend/src/pages/PatientDetail.tsx`

Add import:
```typescript
import { DeteriorationDashboard } from '../components/DeteriorationDashboard';
```

Add to render (near vitals section):
```typescript
<div className="mt-5">
  <DeteriorationDashboard />
</div>
```

---

## PHASE 5: TESTING & VALIDATION (Week 5-6)

### 5.1 Unit Tests for Trend Analysis

**File:** `backend/deterioration_alerts/tests.py`

```python
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from patients.models import Patient
from vitals.models import VitalSigns
from deterioration_alerts.services import TrendAnalysisService, AlertGenerationService
from deterioration_alerts.models import DeteriorationAlert
from accounts.models import User


class TrendAnalysisServiceTests(TestCase):
    def setUp(self):
        self.patient = Patient.objects.create(
            first_name='Test',
            last_name='Patient',
            date_of_birth='1950-01-01',
            care_level='nursing',
        )
        self.staff = User.objects.create_user(
            username='staff',
            email='staff@test.com',
            password='test123',
            role='care_staff'
        )
    
    def test_trend_slope_calculation(self):
        """Test that trend slope is calculated correctly"""
        # Create 12 vitals with rising NEWS2 scores
        for i in range(12):
            news2_base = 3 + (i * 0.5)  # Rising trend
            VitalSigns.objects.create(
                patient=self.patient,
                recorded_by=self.staff,
                heart_rate=60 + i,
                respiratory_rate=14 + (i * 0.2),
                temperature=37 + (i * 0.1),
                bp_systolic=120 + i,
                oxygen_saturation=97 - (i * 0.2),
                recorded_at=timezone.now() - timedelta(hours=12-i)
            )
        
        service = TrendAnalysisService(self.patient, window_size=8)
        analysis = service.analyze_trends()
        
        self.assertIsNotNone(analysis)
        self.assertGreater(analysis.news2_trend_slope, 0)  # Should be upward
        self.assertEqual(analysis.severity, 'declining')  # Rising slope
    
    def test_alert_generation_on_threshold_breach(self):
        """Test that alerts are generated when NEWS2 ≥ 7"""
        # Create vital with NEWS2 = 8
        VitalSigns.objects.create(
            patient=self.patient,
            recorded_by=self.staff,
            heart_rate=120,
            respiratory_rate=25,
            temperature=38,
            bp_systolic=95,
            oxygen_saturation=92,
        )
        
        alerts = DeteriorationAlert.objects.filter(
            patient=self.patient,
            alert_type='threshold_breach'
        )
        
        self.assertGreater(alerts.count(), 0)
    
    def test_insufficient_data_returns_none(self):
        """Test that analysis returns None if not enough vitals"""
        # Create only 2 vitals
        VitalSigns.objects.create(
            patient=self.patient,
            recorded_by=self.staff,
            heart_rate=70,
            respiratory_rate=16,
        )
        
        service = TrendAnalysisService(self.patient, window_size=8)
        analysis = service.analyze_trends()
        
        self.assertIsNone(analysis)
```

### 5.2 Manual Testing Checklist

- [ ] Create test patient
- [ ] Record 12 vitals with rising NEWS2 scores
- [ ] Verify TrendAnalysis is created and saved
- [ ] Verify DeteriorationAlert is created
- [ ] Check dashboard displays alert
- [ ] Acknowledge alert and verify status changes
- [ ] Resolve alert and verify status changes
- [ ] Test alert suppression with rapid alerts
- [ ] Verify API endpoints return correct data

---

## PHASE 6: DEPLOYMENT & MONITORING (Week 6-8)

### 6.1 Admin Interface

**File:** `backend/deterioration_alerts/admin.py`

```python
from django.contrib import admin
from .models import (
    TrendAnalysis, DeteriorationAlert, AlertSuppressionRule,
    DeteriorationEventLog
)


@admin.register(TrendAnalysis)
class TrendAnalysisAdmin(admin.ModelAdmin):
    list_display = ('patient', 'window_size', 'severity', 'risk_score', 'analysed_at')
    list_filter = ('severity', 'window_size', 'analysed_at')
    search_fields = ('patient__first_name', 'patient__last_name')
    readonly_fields = ('analysed_at',)


@admin.register(DeteriorationAlert)
class DeteriorationAlertAdmin(admin.ModelAdmin):
    list_display = ('patient', 'alert_type', 'priority', 'status', 'triggered_at')
    list_filter = ('alert_type', 'priority', 'status', 'triggered_at')
    search_fields = ('patient__first_name', 'patient__last_name')
    actions = ['mark_acknowledged', 'mark_resolved']
    
    def mark_acknowledged(self, request, queryset):
        updated = 0
        for alert in queryset:
            if alert.status == 'active':
                alert.acknowledge(request.user)
                updated += 1
        self.message_user(request, f'{updated} alerts acknowledged')
    
    def mark_resolved(self, request, queryset):
        updated = 0
        for alert in queryset:
            if alert.status in ['active', 'acknowledged']:
                alert.resolve()
                updated += 1
        self.message_user(request, f'{updated} alerts resolved')


@admin.register(AlertSuppressionRule)
class AlertSuppressionRuleAdmin(admin.ModelAdmin):
    list_display = ('rule_type', 'is_active', 'created_at')
    list_filter = ('rule_type', 'is_active')


@admin.register(DeteriorationEventLog)
class DeteriorationEventLogAdmin(admin.ModelAdmin):
    list_display = ('patient', 'event_type', 'severity_at_event', 'logged_at')
    list_filter = ('event_type', 'severity_at_event', 'logged_at')
    search_fields = ('patient__first_name', 'patient__last_name')
    readonly_fields = ('data_snapshot', 'logged_at')
```

### 6.2 Settings Configuration

**File:** `backend/Jomingos/settings.py`

Add configuration:
```python
# Deterioration Detection Settings
DETERIORATION_ALERTS = {
    'NEWS2_CRITICAL_THRESHOLD': 7,
    'NEWS2_RISING_SLOPE_THRESHOLD': 0.5,  # per reading
    'ALERT_FATIGUE_SUPPRESSION_MINUTES': 15,
    'MIN_VITALS_FOR_TREND_ANALYSIS': 8,
    'ENABLE_AUTO_ALERTS': True,  # Auto-generate alerts on vital record
}
```

### 6.3 Management Command for Batch Analysis

**File:** `backend/deterioration_alerts/management/commands/analyze_all_patients.py`

```python
from django.core.management.base import BaseCommand
from patients.models import Patient
from deterioration_alerts.services import TrendAnalysisService


class Command(BaseCommand):
    help = 'Run trend analysis for all active patients'

    def add_arguments(self, parser):
        parser.add_argument(
            '--window-size',
            type=int,
            default=8,
            help='Trend window size'
        )

    def handle(self, *args, **options):
        window_size = options['window_size']
        patients = Patient.objects.filter(is_active=True)
        
        completed = 0
        for patient in patients:
            service = TrendAnalysisService(patient, window_size=window_size)
            analysis = service.analyze_trends()
            if analysis:
                analysis.save()
                completed += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Completed analysis for {completed} patients')
        )
```

Run with:
```bash
python manage.py analyze_all_patients --window-size=8
```

---

## IMPLEMENTATION CHECKLIST

### Week 1: Models & Database
- [ ] Create `deterioration_alerts` Django app
- [ ] Define `TrendAnalysis`, `DeteriorationAlert`, `AlertSuppressionRule` models
- [ ] Create and run migrations
- [ ] Verify models in Django admin

### Week 2: Trend Engine
- [ ] Implement `TrendAnalysisService` class
- [ ] Test slope calculations with sample data
- [ ] Implement severity classification
- [ ] Test with real patient vitals

### Week 3: Alerts & API
- [ ] Implement `AlertGenerationService`
- [ ] Create signal to auto-trigger alerts on vital record
- [ ] Create API viewsets and serializers
- [ ] Test API endpoints with Postman/Swagger
- [ ] Verify alert generation works

### Week 4: Frontend
- [ ] Create `DeteriorationDashboard` component
- [ ] Add to patient detail page
- [ ] Test alert display and acknowledge/resolve
- [ ] Add real-time refresh (polling/WebSocket)

### Week 5: Testing
- [ ] Write unit tests for `TrendAnalysisService`
- [ ] Write unit tests for `AlertGenerationService`
- [ ] Manual testing with test patient data
- [ ] Test alert suppression rules
- [ ] Verify no false positives/negatives

### Week 6: Admin & Config
- [ ] Register models in Django admin
- [ ] Add admin actions for bulk operations
- [ ] Create suppression rule management UI
- [ ] Configure thresholds in settings

### Week 7: Documentation & Polish
- [ ] Document all models and services
- [ ] Create user guide for care staff
- [ ] Write API documentation
- [ ] Optimize database queries
- [ ] Add logging and monitoring

### Week 8: Deployment
- [ ] Deploy to staging environment
- [ ] Run full integration tests
- [ ] Monitor performance and false positive rate
- [ ] Collect staff feedback
- [ ] Deploy to production

---

## Key Integration Points with Existing JOMINGOS

✅ **Already Implemented:**
- NEWS2 scoring in `VitalSigns` model
- Patient age and care level data
- Fall risk calculation
- Care staff role-based access

**This Plan Adds:**
- Trend analysis on top of NEWS2
- Automated alert generation
- Alert management dashboard
- Alert fatigue suppression
- Event audit logging

---

## Performance Optimization

For large patient bases (100+ patients with frequent vitals):

1. **Database indexing** - Already specified in models
2. **Async processing** - Use Celery for background analysis
3. **Caching** - Cache latest trend analysis (5-minute TTL)
4. **Pagination** - Implement on alert list endpoints

---

## Success Metrics

Measure against your research proposal:

| Metric | Target | How to Measure |
|--------|--------|-----------------|
| **Sensitivity** | >0.80 | Compare detected vs. actual deteriorations |
| **Specificity** | >0.85 | False positive rate analysis |
| **Alert Fatigue** | <15% FPR | Monitor suppression rule effectiveness |
| **Time Savings** | 24-48hr earlier | Compare alert time vs. clinical intervention |
| **Staff Feedback** | Positive | Collect UI/UX feedback from care staff |

---

## Questions for Implementation?

Ask your codebase-specific questions:
- Want me to show exact line-by-line integration with your existing code?
- Need help with specific Django patterns?
- Want to see full working example with test data?

Let me know which phase to deep-dive into first!
