# Phase 1: Ready-to-Use Code (Models & Database)

This file contains all the code you need for Week 1-2. Copy and paste directly into your project.

---

## Step 1: Create the App

```bash
cd backend
python manage.py startapp deterioration_alerts
```

---

## Step 2: Add to INSTALLED_APPS

**File:** `backend/Jomingos/settings.py`

Find the `INSTALLED_APPS` list and add:

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    
    # Your existing apps
    'accounts',
    'patients',
    'vitals',
    'care_notes',
    'medications',
    'tasks',
    'family',
    'dashboard',
    
    # NEW APP - Add this line
    'deterioration_alerts',  # ← ADD THIS
]
```

Also add settings at the bottom of `settings.py`:

```python
# Deterioration Detection Configuration
DETERIORATION_ALERTS = {
    'NEWS2_CRITICAL_THRESHOLD': 7,           # Alert if NEWS2 ≥ 7
    'NEWS2_RISING_SLOPE_THRESHOLD': 0.5,    # Alert if rising >0.5 per reading
    'ALERT_FATIGUE_SUPPRESSION_MINUTES': 15, # Suppress alerts within 15 min of previous
    'MIN_VITALS_FOR_TREND_ANALYSIS': 8,     # Need 8 readings to start trend analysis
    'ENABLE_AUTO_ALERTS': True,              # Auto-generate alerts when vital recorded
}
```

---

## Step 3: Copy Models Code

**File:** `backend/deterioration_alerts/models.py`

Copy this entire file:

```python
from django.db import models
from django.utils import timezone
from patients.models import Patient
from vitals.models import VitalSigns
from accounts.models import User


class TrendAnalysis(models.Model):
    """
    Stores trend analysis results for each patient.
    Calculated after every X vital signs recorded.
    """
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
    """
    Alerts triggered by deterioration detection.
    One alert per trigger event (threshold breach, rapid trend, etc.)
    """
    ALERT_TYPE_CHOICES = [
        ('threshold_breach', 'NEWS2 Threshold Breach (≥7)'),
        ('trend_rise', 'Rapid Trend Rise (slope > 0.5)'),
        ('sustained_elevation', 'Sustained Elevation (2+ readings high)'),
        ('combined_risk', 'Combined Risk Factors'),
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
    """
    Rules to suppress repetitive alerts (combat alert fatigue).
    Prevents staff from being overwhelmed with duplicate alerts.
    """
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
    """
    Audit log of all deterioration events for research/analysis.
    Tracks every meaningful event for later investigation.
    """
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
```

---

## Step 4: Create Migrations

```bash
cd backend
python manage.py makemigrations deterioration_alerts
```

You should see output like:
```
Migrations for 'deterioration_alerts':
  deterioration_alerts/migrations/0001_initial.py
    - Create model TrendAnalysis
    - Create model DeteriorationAlert
    - Create model AlertSuppressionRule
    - Create model DeteriorationEventLog
```

Then apply migrations:

```bash
python manage.py migrate deterioration_alerts
```

Output:
```
Running migrations:
  Applying deterioration_alerts.0001_initial... OK
```

---

## Step 5: Test in Django Shell

```bash
python manage.py shell
```

Run these commands:

```python
# Import models
from deterioration_alerts.models import TrendAnalysis, DeteriorationAlert, AlertSuppressionRule
from patients.models import Patient

# Check models are created
print("Models imported successfully!")
print(f"TrendAnalysis: {TrendAnalysis._meta.db_table}")
print(f"DeteriorationAlert: {DeteriorationAlert._meta.db_table}")
print(f"AlertSuppressionRule: {AlertSuppressionRule._meta.db_table}")

# Get a patient (assuming one exists)
patient = Patient.objects.first()
if patient:
    print(f"\nTest patient: {patient}")
    print(f"Alert count: {patient.deterioration_alerts.count()}")
    print(f"Trend analyses: {patient.trend_analyses.count()}")
else:
    print("No patients found - create one first")

exit()
```

---

## Step 6: Register in Django Admin

**File:** `backend/deterioration_alerts/admin.py`

Copy this entire file:

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
    readonly_fields = ('analysed_at', 'news2_trend_slope', 'news2_avg_current', 'news2_avg_previous', 'severity', 'risk_score')
    
    fieldsets = (
        ('Patient', {'fields': ('patient',)}),
        ('Configuration', {'fields': ('window_size',)}),
        ('NEWS2 Metrics', {'fields': ('news2_trend_slope', 'news2_avg_current', 'news2_avg_previous')}),
        ('Vital Trends', {'fields': ('temp_trend', 'hr_trend', 'rr_trend', 'spo2_trend', 'bp_systolic_trend')}),
        ('Assessment', {'fields': ('severity', 'risk_score', 'analysed_at')}),
    )


@admin.register(DeteriorationAlert)
class DeteriorationAlertAdmin(admin.ModelAdmin):
    list_display = ('patient', 'alert_type', 'priority', 'status', 'triggered_at')
    list_filter = ('alert_type', 'priority', 'status', 'triggered_at', 'is_suppressed')
    search_fields = ('patient__first_name', 'patient__last_name')
    readonly_fields = ('triggered_at', 'acknowledged_at', 'resolved_at')
    actions = ['mark_acknowledged', 'mark_resolved', 'mark_suppressed']
    
    fieldsets = (
        ('Patient & Details', {'fields': ('patient', 'alert_type', 'priority', 'status')}),
        ('Trigger Info', {'fields': ('trigger_value', 'trigger_reason')}),
        ('Timeline', {'fields': ('triggered_at', 'acknowledged_at', 'resolved_at', 'acknowledged_by')}),
        ('Related Data', {'fields': ('related_vital', 'related_trend')}),
        ('Suppression', {'fields': ('is_suppressed', 'suppression_reason')}),
    )
    
    def mark_acknowledged(self, request, queryset):
        count = 0
        for alert in queryset.filter(status='active'):
            alert.acknowledge(request.user)
            count += 1
        self.message_user(request, f'{count} alerts marked as acknowledged')
    mark_acknowledged.short_description = "Mark selected as acknowledged"
    
    def mark_resolved(self, request, queryset):
        count = 0
        for alert in queryset.filter(status__in=['active', 'acknowledged']):
            alert.resolve()
            count += 1
        self.message_user(request, f'{count} alerts resolved')
    mark_resolved.short_description = "Mark selected as resolved"
    
    def mark_suppressed(self, request, queryset):
        updated = queryset.update(is_suppressed=True, suppression_reason='Manually suppressed via admin')
        self.message_user(request, f'{updated} alerts suppressed')
    mark_suppressed.short_description = "Suppress selected alerts"


@admin.register(AlertSuppressionRule)
class AlertSuppressionRuleAdmin(admin.ModelAdmin):
    list_display = ('rule_type', 'patient', 'is_active', 'suppress_minutes', 'created_at')
    list_filter = ('rule_type', 'is_active', 'created_at')
    search_fields = ('patient__first_name', 'patient__last_name')


@admin.register(DeteriorationEventLog)
class DeteriorationEventLogAdmin(admin.ModelAdmin):
    list_display = ('patient', 'event_type', 'severity_at_event', 'logged_at')
    list_filter = ('event_type', 'severity_at_event', 'logged_at')
    search_fields = ('patient__first_name', 'patient__last_name')
    readonly_fields = ('data_snapshot', 'logged_at')
    
    def has_add_permission(self, request):
        return False  # Logs are created automatically, not manually
    
    def has_delete_permission(self, request, obj=None):
        return False  # Don't allow deleting audit logs
```

---

## Step 7: Verify Everything Works

```bash
# Run the development server
python manage.py runserver

# In browser, go to:
# http://localhost:8000/admin/

# Login with your admin account
# You should see new "Deterioration Alerts" section
# with options for:
# - Trend Analyses
# - Deterioration Alerts
# - Alert Suppression Rules
# - Deterioration Event Logs
```

---

## Step 8: Create Initialization Script (Optional)

Create a management command to set up default suppression rules.

**File:** `backend/deterioration_alerts/management/__init__.py`

```python
# Empty file
```

**File:** `backend/deterioration_alerts/management/commands/__init__.py`

```python
# Empty file
```

**File:** `backend/deterioration_alerts/management/commands/init_suppression_rules.py`

```python
from django.core.management.base import BaseCommand
from deterioration_alerts.models import AlertSuppressionRule


class Command(BaseCommand):
    help = 'Initialize default alert suppression rules'

    def handle(self, *args, **options):
        # Rule 1: Time-based suppression (prevent alert spam)
        rule1, created = AlertSuppressionRule.objects.get_or_create(
            rule_type='time_based',
            patient=None,
            defaults={
                'suppress_minutes': 15,
                'is_active': True,
                'notes': 'System-wide: suppress duplicate alerts within 15 minutes',
            }
        )
        
        # Rule 2: Count-based suppression (if >3 alerts in 30 min, suppress)
        rule2, created = AlertSuppressionRule.objects.get_or_create(
            rule_type='count_based',
            patient=None,
            defaults={
                'alert_threshold': 3,
                'time_window_minutes': 30,
                'is_active': True,
                'notes': 'System-wide: suppress alerts if >3 in 30 minutes',
            }
        )
        
        self.stdout.write(self.style.SUCCESS('✓ Suppression rules initialized'))
        self.stdout.write(f'  Rule 1 (time-based): {rule1.id}')
        self.stdout.write(f'  Rule 2 (count-based): {rule2.id}')
```

Run with:
```bash
python manage.py init_suppression_rules
```

---

## Checklist for Phase 1 Completion

- [ ] Created `deterioration_alerts` app
- [ ] Added app to `INSTALLED_APPS` in settings.py
- [ ] Added `DETERIORATION_ALERTS` config to settings.py
- [ ] Copied models code to `backend/deterioration_alerts/models.py`
- [ ] Copied admin code to `backend/deterioration_alerts/admin.py`
- [ ] Ran `makemigrations` successfully
- [ ] Ran `migrate` successfully
- [ ] Verified models in Django shell
- [ ] Verified admin interface works
- [ ] Created management command for initialization (optional)
- [ ] Database is ready for Phase 2 (Trend Analysis Engine)

---

## Next: Phase 2 Preparation

You're now ready for Phase 2. In the next guide, we'll add:

1. **TrendAnalysisService** - Calculate slopes and trends
2. **AlertGenerationService** - Auto-generate alerts
3. **Django signals** - Trigger checks when vitals recorded
4. **API endpoints** - Serve data to frontend

Keep this code safe! 🎯

---

## Troubleshooting

**Q: "ModuleNotFoundError: No module named 'deterioration_alerts'"**
- A: Did you add it to INSTALLED_APPS? Check settings.py

**Q: "Table doesn't exist" error**
- A: Did you run `python manage.py migrate`?

**Q: Admin page shows no models**
- A: Did you create admin.py file? Make sure it's in the right place

**Q: Migrations won't create**
- A: Check models.py syntax - use Python syntax checker

Problems? Keep the full implementation guide handy!
