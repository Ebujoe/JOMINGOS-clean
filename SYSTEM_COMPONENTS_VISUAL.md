# System Components - Visual Reference

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    CARE STAFF WORKFLOW                          │
└─────────────────────────────────────────────────────────────────┘

    Staff Records Vital Signs in JOMINGOS
                    ↓
            ┌───────────────┐
            │  VitalSigns   │
            │   Model       │
            │ (Existing)    │
            └───────┬───────┘
                    │
                    ↓ Django Signal (post_save)
    ┌───────────────────────────────────────────────┐
    │  trigger_deterioration_check()                │
    │  Auto-called when vital recorded              │
    └───────────────────────────────────────────────┘
                    │
                    ↓
    ┌───────────────────────────────────────────────┐
    │  AlertGenerationService.check_and_create_     │
    │  alerts(patient)                              │
    │  • Check NEWS2 ≥ 7                            │
    │  • Check sustained elevation                  │
    │  • Check rapid trend (if 8+ vitals exist)     │
    └───────────────────────────────────────────────┘
                    │
                    ├─→ Call TrendAnalysisService
                    │   └─→ Calculate slopes
                    │   └─→ Determine severity
                    │   └─→ Save TrendAnalysis
                    │
                    └─→ Create DeteriorationAlert
                        if thresholds met
                    │
                    ├─→ Check AlertSuppressionRule
                    │   └─→ Suppress if within 15 min?
                    │   └─→ Suppress if >3 alerts/30 min?
                    │
                    └─→ Log to DeteriorationEventLog
                        (for research analysis)
                        
                    ↓
    ┌───────────────────────────────────────────────┐
    │  ALERT CREATED & SAVED TO DATABASE            │
    │  Status: "active" (unacknowledged)            │
    └───────────────────────────────────────────────┘
                    ↓
    ┌───────────────────────────────────────────────┐
    │  DeteriorationDashboard (Frontend)            │
    │  Auto-fetches every 2 minutes via API         │
    │  Displays alerts sorted by priority           │
    └───────────────────────────────────────────────┘
                    ↓
    Staff sees red card: "HIGH PRIORITY: Rapid NEWS2 rise"
    Staff clicks "ACKNOWLEDGE" button
                    ↓
    ┌───────────────────────────────────────────────┐
    │  API: POST /deterioration-alerts/{id}/ack... │
    │  Alert.acknowledge(user) called               │
    │  Status changes to: "acknowledged"            │
    └───────────────────────────────────────────────┘
                    ↓
    Staff intervenes (hydration, oxygen, labs)
    ↓
    Patient improves, staff clicks "RESOLVE"
    ↓
    Alert.resolve() called, status → "resolved"
    ↓
    Alert disappears from dashboard
    ✓ Crisis averted, documented for research
```

---

## Component Interaction Map

```
                    ┌─────────────────────────────────┐
                    │      JOMINGOS DATABASE          │
                    └────────┬────────────────────┬────┘
                             │                    │
                    ┌────────▼────────┐   ┌───────▼──────────┐
                    │  patients       │   │  vitals          │
                    │  ─────────────  │   │  ──────────────  │
                    │ • id (PK)       │   │ • id (PK)        │
                    │ • name          │   │ • patient_id (FK)│
                    │ • age           │   │ • heart_rate     │
                    │ • care_level    │   │ • respiratory_ra │
                    │ • ...           │   │ • temperature    │
                    └────────┬────────┘   │ • bp_systolic    │
                             │           │ • oxygen_satur   │
                             │           │ • recorded_at    │
                             │           └─────┬────────────┘
                             │                 │
                             │ News2 scoring   │ 
                             │ (existing)      │
                             │                 │
          ┌──────────────────▼─────────────────▼──────────────────┐
          │    NEW: deterioration_alerts APP TABLES               │
          └──────────────────────────────────────────────────────┘
          
          ├─ TrendAnalysis
          │  ├ id (PK)
          │  ├ patient_id (FK)
          │  ├ window_size
          │  ├ news2_trend_slope ← KEY: Rate of change
          │  ├ news2_avg_current
          │  ├ news2_avg_previous
          │  ├ temp_trend
          │  ├ hr_trend
          │  ├ rr_trend
          │  ├ spo2_trend
          │  ├ bp_systolic_trend
          │  ├ severity (stable/improving/declining/critical)
          │  ├ risk_score (0-100)
          │  └ analysed_at
          │
          ├─ DeteriorationAlert ← MAIN: Staff interacts with these
          │  ├ id (PK)
          │  ├ patient_id (FK)
          │  ├ alert_type
          │  │  ├ threshold_breach (NEWS2 ≥ 7)
          │  │  ├ trend_rise (slope > 0.5)
          │  │  ├ sustained_elevation
          │  │  └ combined_risk
          │  ├ priority (low/medium/high/CRITICAL)
          │  ├ status (active/acknowledged/resolved/suppressed)
          │  ├ trigger_value
          │  ├ trigger_reason
          │  ├ triggered_at
          │  ├ acknowledged_by (FK to users)
          │  ├ acknowledged_at
          │  ├ resolved_at
          │  ├ related_vital_id (FK)
          │  ├ related_trend_id (FK)
          │  ├ is_suppressed
          │  └ suppression_reason
          │
          ├─ AlertSuppressionRule ← CONFIG: Prevents alert spam
          │  ├ id (PK)
          │  ├ patient_id (FK, nullable = system-wide)
          │  ├ rule_type
          │  │  ├ time_based (suppress for 15 min)
          │  │  └ count_based (suppress if >3 in 30 min)
          │  ├ suppress_minutes
          │  ├ alert_threshold
          │  ├ time_window_minutes
          │  ├ is_active
          │  └ created_at
          │
          └─ DeteriorationEventLog ← AUDIT: For research analysis
             ├ id (PK)
             ├ patient_id (FK)
             ├ event_type
             │  ├ NEWS2_SCORE_RECORDED
             │  ├ TREND_CALCULATED
             │  ├ ALERT_TRIGGERED
             │  └ ALERT_ACKNOWLEDGED
             ├ severity_at_event
             ├ data_snapshot (JSON)
             ├ notes
             └ logged_at
```

---

## Service Layer Architecture

```
                        SIGNAL LAYER
                        ┌──────────────────────────────┐
                        │ @receiver(post_save,         │
                        │          sender=VitalSigns)  │
                        │                              │
                        │ trigger_deterioration_check()│
                        └──────────┬───────────────────┘
                                   │
                 ┌─────────────────▼──────────────────┐
                 │                                    │
        ┌────────▼────────────┐        ┌─────────────▼──────┐
        │ TrendAnalysisService│        │AlertGenerationServi│
        ├────────────────────┤        ├────────────────────┤
        │                    │        │                    │
        │ Main methods:      │        │ Main methods:      │
        │ • analyze_trends() │        │ • check_and_create │
        │   ├ Get vitals     │        │   _alerts()        │
        │   ├ Extract series │        │   ├ Threshold chck │
        │   ├ Calculate      │        │   ├ Sustained ckck │
        │   │ slopes (numpy) │        │   ├ Trend check    │
        │   └ Classify       │        │   ├ Suppression    │
        │     severity       │        │   │ check          │
        │                    │        │   └ Create alert   │
        │ Helper methods:    │        │                    │
        │ • get_recent_     │        │ Private methods:   │
        │   vitals()        │        │ • _create_alert()  │
        │ • extract_vital_  │        │ • _should_suppress │
        │   series()        │        │   _alert()         │
        │ • calculate_      │        │                    │
        │   trend_slope()   │        │ Used by:           │
        │ • _classify_      │        │ • Signals          │
        │   severity()      │        │ • API endpoints    │
        │                   │        │ • Management       │
        │ Used by:          │        │   commands         │
        │ • AlertGen...     │        │                    │
        │ • API endpoints   │        │                    │
        │ • Management      │        │                    │
        │   commands        │        │                    │
        └────────────────────┘       └────────────────────┘
```

---

## API Endpoints (REST)

```
┌─────────────────────────────────────────────────────────────┐
│         DETERIORATION ALERTS API                            │
├─────────────────────────────────────────────────────────────┤

GET /api/deterioration-alerts/
    → List all alerts (paginated)
    Response: {count: N, results: [Alert, ...]}

GET /api/deterioration-alerts/?status=active
    → Filter by status (active/acknowledged/resolved)

GET /api/deterioration-alerts/active_alerts/
    → Only unacknowledged alerts (Staff Dashboard uses this)
    Response: [Alert with priority: HIGH, ...]

GET /api/deterioration-alerts/critical_alerts/
    → Only CRITICAL priority (Emergency view)

GET /api/deterioration-alerts/by_patient/?patient_id=123
    → All alerts for one patient
    
GET /api/deterioration-alerts/{id}/
    → Single alert detail
    Response: {
        id: 5,
        patient: 123,
        patient_name: "John Doe",
        alert_type: "threshold_breach",
        priority: "critical",
        status: "active",
        trigger_reason: "NEWS2 score 8 exceeds threshold of 7",
        triggered_at: "2026-06-07T14:30:00Z",
        ...
    }

POST /api/deterioration-alerts/{id}/acknowledge/
    → Mark alert as acknowledged
    Request: {}
    Response: {status: "acknowledged", acknowledged_at: "..."}
    
POST /api/deterioration-alerts/{id}/resolve/
    → Mark alert as resolved
    Request: {}
    Response: {status: "resolved", resolved_at: "..."}

└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│         TREND ANALYSIS API                                  │
├─────────────────────────────────────────────────────────────┤

GET /api/trend-analysis/patient_latest/?patient_id=123
    → Latest trend analysis for patient
    Response: {
        patient: 123,
        severity: "declining",
        risk_score: 65,
        news2_trend_slope: 0.45,
        news2_avg_current: 5.2,
        analysed_at: "2026-06-07T14:30:00Z"
    }

GET /api/trend-analysis/patient_history/?patient_id=123
    → Trend history for last 7 days
    Response: [TrendAnalysis, TrendAnalysis, ...]

POST /api/trend-analysis/trigger_analysis/
    → Manually trigger analysis for patient
    Request: {patient_id: 123, window_size: 8}
    Response: TrendAnalysis object

└─────────────────────────────────────────────────────────────┘
```

---

## Frontend Component Hierarchy

```
PatientDetail Page
├── Patient Info (existing)
├── Vitals Entry Form (existing)
├── Vitals History (existing)
│
└── NEW: DeteriorationDashboard
    ├── Header
    │   ├── Title: "🚨 Deterioration Detection Dashboard"
    │   └── Toggle: "Active Alerts Only"
    │
    ├── Alert Count Badge
    │   └── "3 Active Alerts"
    │
    └── Alerts Grid (Responsive)
        ├── AlertCard (Priority: HIGH)
        │   ├── Patient: "John Doe"
        │   ├── Alert Type: "Rapid Trend Rise"
        │   ├── Reason: "+0.5 NEWS2 slope detected"
        │   ├── Triggered: "10 min ago"
        │   └── Buttons:
        │       ├── [Acknowledge] → POST /api/.../acknowledge/
        │       └── [Resolve] → POST /api/.../resolve/
        │
        ├── AlertCard (Priority: MEDIUM)
        │   └── ... similar structure
        │
        └── AlertCard (Priority: LOW)
            └── ... similar structure
```

---

## Database Query Patterns (Django ORM)

```python
# 1. Get latest trend for patient
latest_trend = TrendAnalysis.objects.filter(
    patient_id=123
).order_by('-analysed_at').first()

print(f"Severity: {latest_trend.severity}")
print(f"Risk: {latest_trend.risk_score}%")
print(f"Slope: {latest_trend.news2_trend_slope}")

# 2. Get active alerts for staff dashboard
active_alerts = DeteriorationAlert.objects.filter(
    status='active'
).select_related('patient').order_by('-priority', '-triggered_at')

# 3. Get alerts for specific patient
patient_alerts = DeteriorationAlert.objects.filter(
    patient_id=123
).order_by('-triggered_at')

# 4. Check if patient is suppressed (prevent alert spam)
suppressed = DeteriorationAlert.objects.filter(
    patient_id=123,
    is_suppressed=True,
    triggered_at__gte=timezone.now() - timedelta(minutes=15)
).exists()

# 5. Calculate false positive rate (weekly)
from datetime import timedelta
one_week_ago = timezone.now() - timedelta(days=7)
suppressed = DeteriorationAlert.objects.filter(
    triggered_at__gte=one_week_ago,
    is_suppressed=True
).count()
total = DeteriorationAlert.objects.filter(
    triggered_at__gte=one_week_ago
).count()
fpr = (suppressed / total * 100) if total > 0 else 0

# 6. Get event audit trail for research
from django.utils import timezone
from datetime import timedelta
last_7_days = timezone.now() - timedelta(days=7)
events = DeteriorationEventLog.objects.filter(
    patient_id=123,
    logged_at__gte=last_7_days
).order_by('logged_at')

for event in events:
    print(f"{event.logged_at}: {event.event_type} - {event.severity_at_event}")
    print(f"Data: {event.data_snapshot}")
```

---

## Signal Flow (Django Signals)

```
1. Care staff enters vital signs via form
2. Form submitted → POST /api/vitals/ (or Django ORM)
3. VitalSigns model saved to database
                    ↓
4. Django fires: post_save signal for VitalSigns
                    ↓
5. Signal handler: trigger_deterioration_check(sender, instance, created)
   ├─ Check: if created (not just updated)
   └─ Call: AlertGenerationService.check_and_create_alerts(patient)
                    ↓
6. Service runs analysis
   ├─ Try TrendAnalysisService.analyze_trends()
   │  ├─ Get 16 recent vitals
   │  ├─ Split into windows
   │  ├─ Calculate slopes
   │  ├─ Save TrendAnalysis to DB
   │  └─ Return severity/risk_score
   │
   ├─ Check NEWS2 threshold (≥7)
   │  └─ Create alert if breached
   │
   ├─ Check trend rise (slope > 0.5)
   │  └─ Create alert if rising rapidly
   │
   ├─ Check sustained elevation
   │  └─ Create alert if 2+ readings high
   │
   ├─ Check suppression rules
   │  ├─ Time-based: Was alert within last 15 min?
   │  └─ Count-based: >3 alerts in last 30 min?
   │
   └─ Log to DeteriorationEventLog
      └─ All events recorded for research
                    ↓
7. Alerts saved to database with status='active'
                    ↓
8. Frontend polls API every 2 minutes
   GET /api/deterioration-alerts/active_alerts/
                    ↓
9. Dashboard updates with new alerts
   Shows red cards, sounds chime
                    ↓
10. Care staff sees alert on dashboard
    Clicks [Acknowledge] button
                    ↓
11. POST /api/deterioration-alerts/{id}/acknowledge/
    Alert.acknowledge(user) → status='acknowledged'
                    ↓
12. Staff intervenes (oxygen, IV, labs, etc.)
    ↓
13. Staff clicks [Resolve]
    Alert.resolve() → status='resolved'
                    ↓
14. Alert removed from active dashboard
    ✓ Case closed
```

---

## Time Complexity Analysis

```
Operation                    Time      Notes
─────────────────────────────────────────────────────────
Get recent vitals (DB)       O(log n)  Index on (patient, recorded_at)
Extract vital series         O(w)      w = window_size (typically 8-12)
Calculate trend slope        O(w)      NumPy linear fit
Classify severity            O(1)      Just comparing numbers
Check suppression rules      O(s)      s = # suppression rules (usually 2-3)
Create alert                 O(1)      One DB insert
Total per vital record       O(w)      Negligible for web app
─────────────────────────────────────────────────────────

Per 1000 vitals/day with 100 patients:
• 1000 signal triggers
• 1000 × TrendAnalysisService calls (if 8+ vitals exist)
• ~500 alerts generated (assuming 50% detection rate)
• All logged to DeteriorationEventLog

Performance: Sub-100ms per vital on modern hardware
```

---

## Example Alert Lifecycle

```
TIMELINE: Patient Records Vitals 12 Times Over 8 Hours

08:00 | Vital 1: HR 72, RR 16, NEWS2=0 → Signal fires → Not enough data (need 8)
09:00 | Vital 2: HR 78, RR 18, NEWS2=1 → Signal fires → Still 7 vitals total
10:00 | Vital 3: HR 85, RR 20, NEWS2=2 → Signal fires → Still 7 vitals
11:00 | Vital 4: HR 92, RR 22, NEWS2=3 → Signal fires → Still 7 vitals
12:00 | Vital 5: HR 102, RR 24, NEWS2=5 → Signal fires → Still 7 vitals
13:00 | Vital 6: HR 110, RR 26, NEWS2=6 → Signal fires → Still 7 vitals
14:00 | Vital 7: HR 118, RR 28, NEWS2=7 → Signal fires
       │ THRESHOLD BREACH!
       │ Alert created: threshold_breach, priority=HIGH
       │ Alert ID: 42
       │ Status: active (unacknowledged)
       │
       └─→ Dashboard notifies staff
           [RED CARD] HIGH: "Threshold breach - NEWS2=7"
           Staff clicks [Acknowledge] at 14:05
           Alert.status → "acknowledged"
       
15:00 | Vital 8: HR 120, RR 30, NEWS2=8 → Signal fires
       │ NOW 8 VITALS EXIST - TREND ANALYSIS STARTS!
       │
       │ TrendAnalysisService.analyze_trends():
       │ • Window = [Vital 1-8] (oldest → newest)
       │ • NEWS2 series = [0, 1, 2, 3, 5, 6, 7, 8]
       │ • Slope = +0.9 per vital ← RAPID RISE!
       │ • Severity = "critical"
       │ • Risk = 85%
       │ • TrendAnalysis saved
       │
       │ AlertGenerationService.check_and_create_alerts():
       │ ✓ Threshold check: 8 ≥ 7 → Already alerted
       │ ✓ Sustained check: Last 3 scores [7,8] → Only 2 readings
       │ ✗ Trend check: slope=0.9 > 0.5 → YES!
       │   → Create new alert: trend_rise, priority=CRITICAL
       │   → Alert ID: 43
       │
       │ Check suppression rules:
       │ ✓ Time-based: Alert 42 triggered at 14:00
       │   Current time: 15:00 (60 min ago)
       │   Suppress after 15 min? NO → allow alert 43
       │
       └─→ Dashboard shows 2 active alerts
           [RED CARD] CRITICAL: "Rapid trend rise (+0.9 per reading)"
           Staff clicks [Acknowledge]
       
16:00 | Vital 9: HR 125, RR 32, NEWS2=9 → Signal fires
       │ TrendAnalysisService with window 2-9:
       │ • NEWS2 series = [1, 2, 3, 5, 6, 7, 8, 9]
       │ • Slope = +0.85 (still critical)
       │ • Severity = "critical"
       │ • Risk = 90%
       │
       │ AlertGenerationService:
       │ ✓ Check news2 ≥ 7: YES → already alerted
       │ ✓ Check trend: slope=0.85 → YES → create alert
       │ BUT check suppression:
       │   • Last CRITICAL alert: 43 at 15:00
       │   • Current time: 16:00 (60 min ago)
       │   • Wait, check SUPPRESSION RULE count_based:
       │     → Alerts in last 30 min? Only 1 (from 15:30)
       │     → Under threshold of 3
       │   → Allow alert creation: Alert ID: 44
       │
       │ Actually... 60 min gap → alert will be created
       │ BUT if we had more vitals...
       │
       └─→ Dashboard adds Alert 44

16:30 | Vital 10: HR 128, RR 34, NEWS2=10 → Signal fires
       │ Count-based suppression kicks in:
       │ Last 30 min alerts:
       │ • Alert 42 (14:00) - outside window
       │ • Alert 43 (15:00) - outside window
       │ • Alert 44 (16:00) - 30 min ago, border case
       │
       │ Actually depends on exact times
       │ If within window and count ≥ 3: SUPPRESS
       │ Otherwise: create new alert
       │
       └─→ Either Alert 45 created or suppressed

17:00 | STAFF INTERVENTION OCCURS
       │ IV fluids, oxygen, monitoring
       │ Patient improves
       │
       └─→ Vital trend changes: HR dropping, RR normal

18:00 | Patient stable: HR 95, RR 18, NEWS2=2
       │ Staff reviews dashboard
       │ Sees all historical alerts
       │ Clicks [Resolve] on all alerts
       │ All alerts → status='resolved'
       │
       └─→ Crisis averted, 4 hours after detection
           Would have been crisis at 20:00 if untreated
           → 4-hour early detection ✓
```

---

## Key Formulas Used

### 1. Linear Regression (Trend Slope)

```python
# Simple linear fit for vital sign trends
import numpy as np

vitals = [HR_1, HR_2, ..., HR_8]  # 8 readings
x = np.arange(len(vitals))  # [0, 1, 2, 3, 4, 5, 6, 7]
coefficients = np.polyfit(x, vitals, 1)  # Fit line
slope = coefficients[0]  # Change per reading

Example:
vitals = [72, 78, 85, 92, 102, 110, 118, 120]
x = [0, 1, 2, 3, 4, 5, 6, 7]
slope ≈ +6 bpm per reading = critical trend
```

### 2. Risk Score Calculation

```python
risk_score = 0

# 1. Absolute NEWS2 risk
if news2_curr >= 7:
    risk_score += 40  # Threshold breach
elif news2_curr >= 5:
    risk_score += 25  # Elevated
elif news2_curr >= 3:
    risk_score += 15  # Borderline

# 2. Trend risk (upward = dangerous)
if news2_slope > 0.5:
    risk_score += 30  # Rapid rise
elif news2_slope > 0.2:
    risk_score += 15  # Gradual rise

# 3. Multiple vitals trends
if hr_slope > 0.3 or rr_slope > 0.3 or bp_slope > 0.3:
    risk_score += 10 per vital  # Multi-parameter deterioration

# 4. Falling SpO2 (very dangerous)
if spo2_slope < -0.5:
    risk_score += 20

# 5. Rising temperature
if temp_slope > 0.2:
    risk_score += 10

risk_score = min(risk_score, 100)  # Cap at 100%

Example:
news2=7 (+40) + slope=0.6 (+30) + HR rising (+10) + SpO2 falling (+20)
= 100% risk = CRITICAL
```

### 3. Severity Classification

```python
if news2_slope > 0.5 or (news2_slope > 0.2 and news2_curr >= 5):
    severity = "critical"
elif news2_slope > 0.1 and news2_curr >= 3:
    severity = "declining"
elif news2_slope < -0.1:
    severity = "improving"
else:
    severity = "stable"
```

---

This visual guide should help you understand how everything connects! 🎯
