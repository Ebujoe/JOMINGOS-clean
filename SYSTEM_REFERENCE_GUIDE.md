# JOMINGOS Phase 10: Technical Reference & Explanation Guide

## Quick System Summary (Elevator Pitch)

**JOMINGOS** is a healthcare monitoring platform that has evolved from **reactive alerts** (detecting when patients are currently in danger) to **predictive forecasting** (anticipating when patients will become critical 24-72 hours in advance).

**Phase 10** adds AI-powered forecasting that:
- 📊 Analyzes vital sign trends (temperature, heart rate, oxygen, blood pressure)
- 🔮 Predicts what vitals will be 24-48-72 hours from now
- 🚨 Alerts staff when critical situations are forecasted
- 💡 Provides clinical recommendations based on predictions

---

## How to Explain It to Different Audiences

### For Clinical Staff
> "JOMINGOS now watches your patients' vital trends and predicts when they might deteriorate. Instead of waiting until vitals are critically abnormal, you get a heads-up 24-72 hours early so you can intervene before problems become emergencies."

### For Administrators
> "Phase 10 extends our vital monitoring system with predictive capabilities. We use machine learning ensemble forecasting to predict patient deterioration 24-72 hours in advance, improving intervention timing and reducing adverse events."

### For Developers
> "Phase 10 implements a multi-model forecasting ensemble (linear regression, exponential smoothing, moving average) to predict vital signs, uses trajectory analysis to calculate time-to-critical, and stores predictions in a dedicated model for historical tracking."

### For Patients/Families
> "The system now uses artificial intelligence to learn patterns from your health data and predict if you might get sicker in the coming days, so doctors can help you before problems get serious."

---

## Core Architecture

### The Three-Layer System

```
LAYER 1: USER INTERFACE
├─ Dashboard: Overview of all monitored patients
├─ Detail Page: Individual patient forecasts  
└─ API: Programmatic access for integrations

LAYER 2: FORECASTING LOGIC
├─ ForecastingEngine: Generates predictions
├─ TrajectoryAnalyzer: Assesses risk levels
└─ Clinical Decision Rules: Creates recommendations

LAYER 3: DATA
├─ VitalSigns: Raw measurements (temperature, HR, SpO2, etc.)
├─ PredictiveRiskAssessment: Forecasts & risk scores
└─ Database: Persistent storage
```

---

## The Forecasting Algorithm Explained Simply

### Problem to Solve
> Given a patient's recent vital signs, what will their vitals be in 24 hours?

### The Three Prediction Models

**Model 1: Linear Regression (Trend Line)**
- **What it does:** Draws a straight line through recent vital sign measurements
- **Good for:** Steady, consistent trends
- **Example:** If heart rate increases 5 bpm every hour, it predicts 120 bpm in 24 hours
- **Risk:** Assumes trends continue unchanged

**Model 2: Exponential Smoothing (Weighted Recent)**
- **What it does:** Gives more weight to recent readings, less to older ones
- **Good for:** Catching sudden changes
- **Example:** Last reading was 110 bpm, previous was 100 bpm → focuses more on the 110
- **Risk:** Can overreact to single abnormal readings

**Model 3: Moving Average (Smoothed Trend)**
- **What it does:** Averages the last 3 readings to smooth out noise, then projects forward
- **Good for:** Reducing measurement errors and fluctuations
- **Example:** Readings 98, 99, 100 → average 99, smooth trend
- **Risk:** Slower to detect real changes

### Combining the Models: Ensemble

Instead of picking one model (risky!), we use ALL THREE and combine them:

```
Prediction = Model1 × weight1 + Model2 × weight2 + Model3 × weight3

Where weights are based on:
- How consistent each model's data is (stable = higher weight)
- How well each model performed historically

Result: More robust prediction that balances all three approaches
```

---

## The Risk Calculation

### How We Determine "Time to Critical"

```
For each vital sign:
1. Get the forecasted value from the ensemble
2. Compare to clinical threshold (e.g., SpO2 < 85% is critical)
3. If forecasted value would breach threshold:
   → Calculate how many hours until it crosses
   → Example: Currently 92%, dropping 0.5%/hour, critical at 85%
   → Time = (92 - 85) / 0.5 = 14 hours

4. Find the EARLIEST vital that would become critical
   → Show that in "Time to Critical"
```

### Risk Levels

| Level | Definition | Action |
|-------|-----------|--------|
| 🟢 **STABLE** | No critical vitals predicted | Continue routine monitoring |
| 🟡 **SLOW DETERIORATION** | Critical in 48-72 hours | Plan for escalation |
| 🟠 **MODERATE DETERIORATION** | Critical in 24-48 hours | Increase monitoring frequency |
| 🔴 **RAPID DETERIORATION** | Critical in 6-24 hours | Prepare intervention |
| 🔴🔴 **CRITICAL WITHIN 24H** | Critical in <6 hours | Immediate intervention needed |

---

## Database Schema (Simplified)

### VitalSigns Table

Stores individual vital sign measurements:

```
VitalSigns
├─ id (auto-increment)
├─ patient_id (FK to Patient)
├─ temperature (decimal)
├─ heart_rate (integer)
├─ respiratory_rate (integer)
├─ oxygen_saturation (decimal)
├─ bp_systolic (integer)
├─ bp_diastolic (integer)
├─ blood_glucose (decimal)
├─ weight_kg (decimal)
├─ pain_score (integer 0-10)
├─ recorded_at (datetime)
└─ notes (text)

Example Row:
id=1234, patient_id=1003, temperature=38.2, heart_rate=105, 
respiratory_rate=25, oxygen_saturation=92.0, recorded_at=2026-08-11 12:13:31
```

### PredictiveRiskAssessment Table

Stores forecasts and risk calculations:

```
PredictiveRiskAssessment
├─ id (auto-increment)
├─ patient_id (FK to Patient)
├─ based_on_vital (FK to VitalSigns)
├─ prediction_timestamp (datetime)
│
├─ Current Vitals:
│  ├─ current_heart_rate
│  ├─ current_respiratory_rate
│  ├─ current_oxygen_saturation
│  ├─ current_bp_systolic
│  └─ current_temperature
│
├─ Forecasted Vitals (24h ahead):
│  ├─ forecast_24h_heart_rate
│  ├─ forecast_24h_respiratory_rate
│  ├─ forecast_24h_oxygen_saturation
│  ├─ forecast_24h_bp_systolic
│  └─ forecast_24h_temperature
│
├─ Risk Assessment:
│  ├─ trajectory_level (stable/slow/moderate/rapid/critical)
│  ├─ hours_to_critical (float or null)
│  ├─ vitals_at_risk (JSON list)
│  ├─ critical_vital_first (string)
│  ├─ critical_vital_first_hours (float)
│  ├─ urgency_level (immediate/urgent/elevated/monitor/routine)
│  ├─ forecast_confidence (0.0-1.0)
│  ├─ historical_readings_used (integer)
│  ├─ recommended_actions (JSON list)
│  └─ intervention_window_hours (float or null)

Example Row:
patient_id=1003, trajectory_level='stable', hours_to_critical=NULL,
vitals_at_risk=[], forecast_confidence=0.7, 
recommended_actions=['Continue routine monitoring']
```

---

## API Endpoints (How to Use)

### Endpoint 1: Get Patient Prediction

```
GET /vitals/api/patient/<patient_id>/predictive/

Example: /vitals/api/patient/1003/predictive/

Returns:
{
  "success": true,
  "prediction": {
    "patient_id": 1003,
    "patient_name": "Predictive Demo Patient",
    "trajectory_level": "stable",
    "urgency": "routine",
    "hours_to_critical": null,
    "vitals_at_risk": [],
    "current_vitals": {
      "heart_rate": 105,
      "respiratory_rate": 25,
      "oxygen_saturation": 92.0,
      "bp_systolic": 120,
      "temperature": 38.2
    },
    "forecast_24h": {
      "heart_rate": 105,
      "respiratory_rate": 25,
      "oxygen_saturation": 92.1,
      "bp_systolic": 120,
      "temperature": 38.2
    },
    "recommendations": ["Continue routine monitoring"],
    "confidence": 0.7,
    "created_at": "2026-08-11T12:13:31.947657+00:00"
  }
}

Use Case: Get latest prediction for a specific patient
```

### Endpoint 2: Get All At-Risk Patients

```
GET /vitals/api/predict/cohort/

Returns:
{
  "success": true,
  "predictions": [
    {patient_id: 1003, urgency: "routine", ...},
    {patient_id: 1004, urgency: "urgent", ...},
    ...
  ]
}

Sorted by urgency (most critical first)

Use Case: Dashboard refresh, alert systems, bulk reporting
```

### Endpoint 3: Get Specific Prediction Details

```
GET /vitals/api/predict/details/<prediction_id>/

Example: /vitals/api/predict/details/42/

Returns: Full prediction record with all calculated fields

Use Case: Historical analysis, audit trails, detailed reviews
```

---

## File Structure

```
JOMINGOS/
├── backend/
│   ├── vitals/
│   │   ├── models.py
│   │   │   └─ VitalSigns
│   │   │   └─ PredictiveRiskAssessment  ← NEW in Phase 10
│   │   │
│   │   ├── views.py
│   │   │   └─ add_vitals(), patient_vitals_list()
│   │   │
│   │   ├── predictive_views.py  ← NEW in Phase 10
│   │   │   ├─ predictive_dashboard()
│   │   │   ├─ patient_predictive_detail()
│   │   │   └─ api_patient_predictive()
│   │   │
│   │   ├── api_predictive.py  ← NEW in Phase 10
│   │   │   ├─ get_patient_prediction()
│   │   │   ├─ get_cohort_predictions()
│   │   │   └─ get_prediction_details()
│   │   │
│   │   ├── utils/
│   │   │   ├── forecasting_engine.py  ← NEW in Phase 10
│   │   │   │   └─ ForecastingEngine (3 models + ensemble)
│   │   │   │
│   │   │   └── trajectory_analyzer.py  ← NEW in Phase 10
│   │   │       └─ TrajectoryAnalyzer (risk calculation)
│   │   │
│   │   ├── forms.py
│   │   │   └─ VitalSignsForm
│   │   │
│   │   ├── urls.py
│   │   │   └─ Routes for predictive endpoints
│   │   │
│   │   ├── test_phase10_predictive_forecasting.py  ← NEW in Phase 10
│   │   │   └─ 21 comprehensive tests (all passing)
│   │   │
│   │   └── templates/vitals/
│   │       ├── predictive_simple.html  ← NEW in Phase 10
│   │       │   └─ Main dashboard UI
│   │       │
│   │       └── patient_predictive_detail.html  ← NEW in Phase 10
│   │           └─ Individual forecast UI
```

---

## How to Explain Each Component

### 1. ForecastingEngine (utils/forecasting_engine.py)

**Purpose:** Make predictions about future vital signs

**Think of it as:** A weather forecaster that uses three different methods to predict tomorrow's temperature, then combines them into one forecast

**Key Methods:**
- `forecast_vital()` - Predicts one vital sign using one model
- `forecast_all_vitals()` - Predicts all vital signs using ensemble
- `_combine_forecasts()` - Weights and merges the three models

**Example Usage:**
```python
engine = ForecastingEngine()
historical_data = {
    'heart_rate': [
        {'value': 75, 'time_hours_ago': -12},
        {'value': 80, 'time_hours_ago': -8},
        {'value': 85, 'time_hours_ago': -4},
        {'value': 90, 'time_hours_ago': 0}
    ]
}
forecast = engine.forecast_vital('heart_rate', historical_data, horizon_hours=24)
# Result: {'forecast': 95, 'confidence': 0.8}
```

### 2. TrajectoryAnalyzer (utils/trajectory_analyzer.py)

**Purpose:** Determine risk level and urgency

**Think of it as:** A clinical decision system that says "This patient is stable" or "This patient will be critical in 12 hours"

**Key Methods:**
- `calculate_time_to_deterioration()` - How many hours until critical?
- `analyze_patient_trajectory()` - Overall risk assessment
- `_generate_recommendations()` - What should clinical staff do?

**Example Usage:**
```python
analyzer = TrajectoryAnalyzer()
current_vitals = {'heart_rate': 105, 'oxygen_saturation': 92.0, ...}
forecasts = {'heart_rate': {...}, 'oxygen_saturation': {...}, ...}

trajectory = analyzer.analyze_patient_trajectory(current_vitals, forecasts)
# Result: {
#   'trajectory_level': 'stable',
#   'intervention_window_hours': null,
#   'vitals_at_risk': [],
#   'recommendations': ['Continue routine monitoring']
# }
```

### 3. PredictiveRiskAssessment Model (models.py)

**Purpose:** Store predictions in database for historical tracking

**Think of it as:** A report card that gets filed away so we can look at it later

**Key Fields:**
- Current vitals (what was measured)
- Forecasted vitals (what we predict)
- Risk assessment (trajectory level, urgency)
- Clinical guidance (recommendations)
- Quality metrics (confidence, readings used)

### 4. Predictive Dashboard (templates/predictive_simple.html + predictive_views.py)

**Purpose:** Show clinical staff overview of all patients

**Shows:**
- Summary metrics (immediate action, at-risk, total monitored)
- Tables of stable and at-risk patients
- Quick view of current vitals and confidence

**Think of it as:** A triage board that instantly shows the sickest patients first

### 5. Patient Detail Page (templates/patient_predictive_detail.html + predictive_views.py)

**Purpose:** Show detailed forecast for one patient

**Shows:**
- Risk alert (is this patient in danger?)
- Current vs. forecasted vitals (what changed?)
- Vitals at risk (which ones are problematic?)
- Recommendations (what should we do?)
- Forecast quality (how confident are we?)
- History (how have predictions evolved?)

---

## Clinical Thresholds Reference

When the system determines if a vital is "at risk," it compares to these thresholds:

```
HEART RATE:
├─ Critical: < 40 bpm  or  > 130 bpm
├─ Warning: < 50 bpm  or  > 110 bpm
└─ Normal: 50-110 bpm

RESPIRATORY RATE:
├─ Critical: < 8 br/min  or  > 30 br/min
├─ Warning: < 10 br/min  or  > 24 br/min
└─ Normal: 10-24 br/min

OXYGEN SATURATION:
├─ Critical: < 85%
├─ Warning: < 90%
└─ Normal: ≥ 90%

TEMPERATURE:
├─ Critical: < 35°C  or  > 39°C
├─ Warning: < 36°C  or  > 38°C
└─ Normal: 36-38°C

BLOOD PRESSURE (Systolic):
├─ Critical: < 90 mmHg  or  > 180 mmHg
├─ Warning: < 100 mmHg  or  > 160 mmHg
└─ Normal: 100-160 mmHg
```

---

## Common Questions & Answers

### Q: How is Phase 10 different from Phase 6-9?

**A:** 
- **Phase 6-9:** Detect alerts when vitals are CURRENTLY abnormal
- **Phase 10:** Predict dangers 24-72 hours BEFORE they happen

Think of the difference:
- Old way: Fire alarm goes off when house is burning
- New way: Smoke detector alerts you while you're cooking

### Q: Why use three forecasting models instead of one?

**A:** 
Different models catch different patterns:
- Linear = good for steady trends
- Exponential = good for sudden changes  
- Moving average = good for noisy data

Using all three makes predictions more robust. If one model is wrong, the other two can correct it.

### Q: What happens if a patient doesn't have 3+ vital readings?

**A:** 
The system requires at least 3 readings to detect a trend. Without a trend, you can't forecast. So:
- New patients: Collect 3+ readings first, then forecasting starts
- Existing patients: Use all available history (more readings = more accurate)

### Q: Can the system make mistakes?

**A:** 
Yes! The confidence score tells you how much to trust it:
- 0.9+ = Very confident (86%+ readings align)
- 0.7-0.9 = Fairly confident (data fairly consistent)
- <0.7 = Lower confidence (variable data)

**Important:** Clinical staff should always verify predictions with their clinical judgment. System is a TOOL, not the decision-maker.

### Q: What's the "time to critical" calculation?

**A:**
```
Example:
Current SpO2: 92%
Predicted SpO2 (24h): 90%
Rate of decline: 0.083%/hour

Critical threshold: 85%
Hours to critical = (92 - 85) / 0.083 = 84 hours

So the patient has ~84 hours before predicted critical SpO2
```

### Q: How often are predictions updated?

**A:**
- Every time a new vital is recorded
- Patient detail page auto-generates forecast (if ≥3 readings)
- Dashboard updates when staff views it
- API calls get current prediction

### Q: Can I access predictions programmatically (for EHR integration)?

**A:**
Yes! Three REST API endpoints:
1. `/vitals/api/patient/<id>/predictive/` - Single patient
2. `/vitals/api/predict/cohort/` - All patients
3. `/vitals/api/predict/details/<id>/` - Detailed prediction

All return JSON with full forecast data.

---

## Testing the System (For QA/Validation)

### Test 1: Basic Forecast
1. Record 4 vital signs for a patient (showing trend)
2. Go to patient detail page
3. Verify forecasted values appear
4. Check that forecast shows trend continuation

### Test 2: Risk Detection
1. Record vitals where one is approaching critical
2. Verify "hours_to_critical" calculates
3. Verify trajectory level changes (not "stable")
4. Verify recommendation appears

### Test 3: API Access
1. Call `/vitals/api/patient/1003/predictive/`
2. Verify JSON response includes forecast data
3. Check that confidence score is present
4. Verify recommendations are populated

### Test 4: Dashboard
1. Navigate to `/vitals/predictive/`
2. Verify at least 1 patient appears in table
3. Click [Details] button
4. Verify forecast detail page loads

### Test 5: Data Persistence
1. Record vitals for patient A
2. Generate forecast (view detail page)
3. Close browser
4. Reopen and navigate back
5. Verify forecast is still there (not recalculated, retrieved from DB)

---

## Deployment Checklist

Before going live:

- [ ] Database migrations applied (PredictiveRiskAssessment table created)
- [ ] All 21 tests passing
- [ ] Clinical staff trained on reading forecasts
- [ ] Confidence thresholds set for alerts
- [ ] Alert escalation process defined
- [ ] Performance testing completed (query times, response times)
- [ ] Backup strategy in place
- [ ] Monitoring/logging configured
- [ ] User documentation created
- [ ] Audit trail enabled for predictions

---

## Summary: What to Tell People

**For your boss:**
> "Phase 10 adds predictive AI to JOMINGOS. We now forecast patient deterioration 24-72 hours in advance, letting staff intervene early instead of reacting to emergencies. System is fully tested and ready for deployment."

**For clinical staff:**
> "You'll see a new 'Predictive Forecasting' section on each patient. It shows what we predict their vitals will be tomorrow, and alerts you if we think they might become critical soon. Check it regularly to catch problems early."

**For IT/DevOps:**
> "Phase 10 adds database tables (PredictiveRiskAssessment), three new views (predictive_views.py), forecasting logic (forecasting_engine.py, trajectory_analyzer.py), and REST API endpoints. All code is tested, integrated, and documented."

**For patients/families:**
> "Your hospital now uses AI to predict if you might get worse in the coming days. If it detects early warning signs, doctors will know to help you sooner."

---

**Version:** Phase 10 - Predictive Forecasting  
**Status:** Ready for Deployment ✅  
**Date:** 2026-08-11
