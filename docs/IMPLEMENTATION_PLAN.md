# JOMINGOS Deterioration Detection Implementation Plan
**Status**: Draft  
**Version**: 1.0.0  
**Last Updated**: 10 August 2026

---

## Executive Summary

The JOMINGOS platform already implements core vital sign monitoring with NEWS2 scoring. This plan describes the integration of **research-grade deterioration detection** based on time-series trend analysis, designed to:

1. ✅ Detect early deterioration patterns (gradual vs. sudden)
2. ✅ Provide transparent decision explanations
3. ✅ Support 60/40 experimental evaluation against Kaggle dataset
4. ✅ Maintain audit trail for clinical validation

**Current Status**: Basic NEWS2 + alert system working. Next phase: add research-grade trend analysis + evaluation pipeline.

---

## 1. Current Jomingo Architecture Review

### Existing Components (Working)

#### Database Models
- **Patient**: Demographics, clinical info (in `patients.models`)
- **VitalSigns**: Individual vital sign records (in `vitals.models`)
  - Fields: HR, RR, SpO2, BP (sys/dias), Temp, timestamp, etc.
  - Relations: ForeignKey to Patient
  - Signals: auto_detect_deterioration on save
- **DeteriorationAlert**: Alert records (in `deterioration_alerts.models`)
  - Fields: patient, alert_type, priority, status, trigger_reason
  - Relations: ForeignKey to Patient, ForeignKey to VitalSigns

#### Business Logic
- **NEWS2 Scoring**: Implemented in VitalSigns model as @property methods
  - `news2_hr_score`, `news2_respiratory_score`, `news2_spo2_score`, `news2_bp_score`, `news2_temp_score`
  - `news2_total`: Sum of component scores
  - `news2_level`: Risk classification (low/medium/high)
- **Deterioration Signal Handler**: `auto_detect_deterioration` signal
  - Triggered on VitalSigns save
  - Creates DeteriorationAlert if NEWS2 ≥ 7
- **Alert Generation**: Basic rule: NEWS2 ≥ 7 → CRITICAL alert

#### Frontend
- **Dashboard**: HTML template showing vital signs summary
- **Patient Detail**: Individual patient view with vitals tab
- **Patient History**: Time-series view of vitals with NEWS2 display
- **Admin Interface**: Django admin for managing records

#### APIs
- **REST API**: `/vitals/api/` endpoint returning JSON data

### Existing Test Data
- 12 patients in system
- 15 vital sign recordings
- 4 deterioration alerts generated
- Complete audit trail preserved

---

## 2. Research Requirements Mapping

### Requirement 1: TIME-SERIES TREND ANALYSIS
**Current State**: NEWS2 only (snapshot scoring)
**Required State**: NEWS2 + trend analysis over sliding windows

**Implementation**:
- Add trend calculation engine to VitalSigns model
- Calculate rate of change for each vital over 4, 8, 12 reading windows
- Store historical observations efficiently (query optimization)
- Implement deterioration signal detection (multiple vitals worsening simultaneously)

**Files to Modify**:
- `backend/vitals/models.py` — Add trend analysis methods
- `backend/vitals/utils/trend_engine.py` — NEW trend calculation logic

### Requirement 2: MULTI-PARAMETER ANALYSIS
**Current State**: Individual vital scores only
**Required State**: Combined risk from NEWS2 + trend + multi-parameter worsening

**Implementation**:
- Detect when multiple vitals are trending in same direction
- Weight combined deterioration higher than single-vital changes
- Distinguish between noise and significant trends

**Files to Modify**:
- `backend/vitals/models.py` — Add multi-parameter scoring
- `backend/vitals/utils/risk_engine.py` — NEW risk calculation

### Requirement 3: EXPLAINABILITY & TRACEABILITY
**Current State**: Alert generated, but limited explanation
**Required State**: Step-by-step decision logic visible to user

**Implementation**:
- Store decision trace (NEWS2 components, trend scores, reasoning) per assessment
- Create "why this result?" panel showing contributing factors
- Historical reconstruction (what was known at timestamp T?)

**Files to Modify**:
- `backend/vitals/models.py` — Add decision trace fields
- `backend/templates/vitals/patient_vital_history.html` — Add explanation panel
- `backend/vitals/utils/explainability.py` — NEW explanation generation

### Requirement 4: 60/40 EXPERIMENTAL EVALUATION
**Current State**: Real data in system, but no evaluation pipeline
**Required State**: Train/test split on Kaggle dataset, evaluation metrics

**Implementation**:
- Load Kaggle vital_signs_cleaned.csv dataset
- Patient-level 60/40 split (no leakage)
- Apply algorithms to both sets
- Calculate performance metrics

**Files to Create**:
- `backend/experiments/dataset_loader.py` — Load Kaggle CSV
- `backend/experiments/experimental_split.py` — 60/40 split logic
- `backend/experiments/evaluation_pipeline.py` — Run experiments
- `backend/experiments/metrics.py` — Calculate sensitivity/specificity/etc.

### Requirement 5: DASHBOARD & VISUALIZATION
**Current State**: Basic HTML tables
**Required State**: Professional timeline, charts, risk progression

**Implementation**:
- Create patient risk timeline (NEWS2, Trend, Combined Risk over time)
- Add historical charts (temperature, HR, RR, SpO2, BP)
- Clickable historical assessments (temporal integrity)
- Professional risk visualization (color-coded badges)

**Files to Modify**:
- `backend/templates/vitals/patient_vital_history.html` — Add timeline & charts
- `frontend/components/VitalChart.tsx` — NEW React component (if using frontend)

---

## 3. Proposed Integration Points

### Integration 1: NEWS2 Scoring (ALREADY DONE ✅)
**Location**: `backend/vitals/models.py` (VitalSigns model)
**Status**: Working. No changes needed.

### Integration 2: Trend Analysis (NEW)
**Location**: `backend/vitals/models.py` (add methods) + `backend/vitals/utils/trend_engine.py` (new)
**Method**: 
```
def calculate_trend(patient, vital_type, window_size=4):
    """
    Get last N observations for vital_type.
    Calculate rate of change (RoC).
    Return trend score.
    """
```
**Trigger**: On VitalSigns save, calculate trend for all parameters

### Integration 3: Risk Assessment (NEW)
**Location**: `backend/vitals/utils/risk_engine.py` (new)
**Method**:
```
def assess_combined_risk(patient):
    """
    Get latest NEWS2 score.
    Get trend scores.
    Combine: combined_risk = NEWS2 + trend_score.
    Return risk level.
    """
```
**Trigger**: On VitalSigns save, recalculate combined risk

### Integration 4: Alert Decision (MODIFY)
**Location**: `backend/vitals/models.py` (auto_detect_deterioration signal)
**Current Logic**: IF NEWS2 ≥ 7 THEN alert
**New Logic**: 
```
IF NEWS2 ≥ 7 OR (NEWS2 ≥ 5 AND trend_worsening) OR (combined_risk ≥ threshold):
    Create alert
    Store decision trace
```

### Integration 5: Decision Trace Storage (NEW)
**Location**: New model `RiskAssessment` in `backend/vitals/models.py`
**Fields**:
```python
patient = ForeignKey(Patient)
timestamp = DateTimeField()
observation_ids = JSONField()  # IDs of vitals used
news2_total = IntegerField()
news2_components = JSONField()  # dict of HR, RR, SpO2, BP, Temp scores
trend_scores = JSONField()  # dict of trend calculations
multi_param_analysis = JSONField()  # dict of parameter interactions
combined_risk = IntegerField()
risk_level = CharField(choices=[low, medium, high, critical])
explanation = TextField()  # Human-readable explanation
algorithm_version = CharField()
configuration_version = CharField()
```

### Integration 6: Explainability Panel (NEW)
**Location**: `backend/templates/vitals/patient_vital_history.html`
**Components**:
- Show current assessment
- Show recent observations used
- Show changes detected (for each vital)
- Show contributing factors
- Show decision logic
- Show clinical wording

---

## 4. Database Schema Changes

### New Model: RiskAssessment
```python
class RiskAssessment(models.Model):
    """
    Stores complete risk assessment record for traceability
    """
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    assessed_at = models.DateTimeField()  # When assessment was made
    
    # Vital sign observations used
    vital_signs = models.ManyToManyField(VitalSigns)
    observation_count = models.IntegerField()  # How many vitals used
    
    # NEWS2 Analysis
    news2_total = models.IntegerField()
    news2_hr_score = models.IntegerField()
    news2_rr_score = models.IntegerField()
    news2_spo2_score = models.IntegerField()
    news2_bp_score = models.IntegerField()
    news2_temp_score = models.IntegerField()
    
    # Trend Analysis
    trend_window_4 = models.JSONField(default=dict)  # Last 4 readings
    trend_window_8 = models.JSONField(default=dict)  # Last 8 readings
    trend_window_12 = models.JSONField(default=dict)  # Last 12 readings
    trend_score = models.IntegerField(default=0)
    
    # Multi-Parameter Analysis
    multi_param_score = models.IntegerField(default=0)
    multi_param_details = models.JSONField(default=dict)
    
    # Combined Risk
    combined_risk = models.IntegerField()  # NEWS2 + trend + multi
    risk_level = models.CharField(max_length=20, choices=[
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk'),
        ('critical', 'Critical'),
    ])
    
    # Explanation
    explanation_text = models.TextField()  # Human-readable explanation
    decision_logic = models.JSONField()  # Step-by-step reasoning
    
    # System Info
    algorithm_version = models.CharField(max_length=10)
    configuration_version = models.CharField(max_length=10)
    
    class Meta:
        ordering = ['-assessed_at']
        index_together = [['patient', 'assessed_at']]
```

### Migration Required
```bash
python manage.py makemigrations vitals
python manage.py migrate vitals
```

---

## 5. API Changes

### Current Endpoint
**GET `/vitals/api/`** → Returns vital signs list

### New Endpoints

#### GET `/api/v1/patient/{patient_id}/risk-timeline/`
Returns risk progression timeline with:
- Timestamp
- NEWS2
- Trend score
- Combined risk
- Risk level

#### GET `/api/v1/patient/{patient_id}/risk-assessment/{assessment_id}/`
Returns complete assessment including:
- All vital signs used
- NEWS2 breakdown
- Trend analysis
- Decision logic
- Explanation

#### GET `/api/v1/vital/{vital_id}/explanation/`
Returns why this specific vital contributed to risk assessment

---

## 6. Frontend Changes

### Patient Vital History Template Enhancements
**File**: `backend/templates/vitals/patient_vital_history.html`

**Changes**:
1. Add "Risk Timeline" section showing NEWS2 + Trend + Combined Risk over time
2. Add clickable historical assessments (show what was known at that timestamp)
3. Add "Why this result?" expandable panel with decision logic
4. Add visual trend indicators (arrows showing direction)
5. Add contributing factors list

**Example Output**:
```
RECORDING #5 (15:33)
Heart Rate: 108 bpm ↑ (was 88)
Respiratory Rate: 26 br/min ↑ (was 20)
SpO2: 92.1% ↓ (was 95.8%)
NEWS2: 7 (CRITICAL)
Trend: Worsening
Risk: HIGH

Why this result?
- Multiple vitals moving in concerning directions
- Respiratory rate critically elevated (26 = +3 points)
- SpO2 concerning (92.1 = +2 points)
- Worsening trend detected over last 4 readings
- Alert automatically triggered per protocol
```

---

## 7. Experimental Methodology (60/40 Split)

### Step 1: Load Kaggle Dataset
```python
import pandas as pd

df = pd.read_csv('human_vital_signs_dataset_2024.csv')
# 200,020 observations
# 17 columns: Patient ID, HR, RR, Timestamp, Temp, SpO2, BP, Age, etc.
# Ground truth: Risk Category (High Risk / Low Risk)
```

### Step 2: Patient-Level Stratified Split
```python
unique_patients = df['Patient ID'].unique()
n_patients = len(unique_patients)
train_count = int(0.6 * n_patients)

np.random.seed(42)  # Reproducibility
train_patients = np.random.choice(unique_patients, train_count, replace=False)

train_df = df[df['Patient ID'].isin(train_patients)]
test_df = df[~df['Patient ID'].isin(train_patients)]

print(f"Train: {len(train_df)} obs from {len(train_patients)} patients")
print(f"Test: {len(test_df)} obs from {n_patients - len(train_patients)} patients")
```

**Outcome**:
- Training: 60% of patients (all their observations)
- Test: 40% of patients (all their observations)
- No patient leakage between sets

### Step 3: Algorithm Development (on Training Set)
- Calculate NEWS2 for each observation
- Calculate trends over 4/8/12 reading windows
- Test different trend thresholds
- Calibrate multi-parameter weighting
- Finalize configuration

### Step 4: Evaluation (on Test Set Only)
- Apply frozen algorithm to test set
- Compare predictions to ground truth risk labels
- Calculate: TP, FP, TN, FN
- Compute:
  - Sensitivity = TP / (TP + FN)
  - Specificity = TN / (TN + FP)
  - Precision = TP / (TP + FP)
  - F1 = 2 × (Precision × Recall) / (Precision + Recall)
  - Accuracy = (TP + TN) / (TP + TN + FP + FN)
  - ROC-AUC (if probabilities available)

### Step 5: Comparison
- **NEWS2 Only**: Calculate using NEWS2 threshold (e.g., ≥7 = High Risk)
- **NEWS2 + Trends**: Using combined algorithm
- Compare metrics to show added value of trends

---

## 8. Leakage Prevention Strategy

### Temporal Leakage
**Risk**: Future observations influence historical decisions
**Prevention**: 
- Store assessment timestamp separately from calculation timestamp
- When reconstructing historical assessment, use ONLY observations before that timestamp
- Block access to future observations in historical view

### Patient Leakage
**Risk**: Same patient in both train and test sets
**Prevention**: ✅ Implemented via patient-level split (see section 7)

### Label Leakage
**Risk**: Ground truth labels influence algorithm parameters
**Prevention**:
- Freeze algorithm configuration before evaluating test set
- Do NOT tune parameters based on test set results
- Document configuration version

### Temporal Structure Leakage
**Risk**: Training on future data to predict past
**Prevention**: Single-date dataset prevents this, but document limitation

---

## 9. Implementation Sequence

### Phase 1: Foundation (Week 1)
- ✅ Dataset audit (COMPLETE)
- ⏳ Create RiskAssessment model
- ⏳ Implement NEWS2 validation tests
- ⏳ Create database migration

### Phase 2: Trend Analysis Engine (Week 2)
- ⏳ Implement trend_engine.py
- ⏳ Calculate rate of change for each vital
- ⏳ Implement 4/8/12 reading windows
- ⏳ Create trend calculation tests

### Phase 3: Risk Assessment Engine (Week 3)
- ⏳ Implement risk_engine.py
- ⏳ Combine NEWS2 + trend scores
- ⏳ Implement multi-parameter analysis
- ⏳ Create risk assessment tests

### Phase 4: Integration & Alerts (Week 3)
- ⏳ Modify auto_detect_deterioration signal
- ⏳ Update alert creation logic
- ⏳ Store RiskAssessment records
- ⏳ Integration testing

### Phase 5: Explainability (Week 4)
- ⏳ Implement explainability.py
- ⏳ Update patient_vital_history template
- ⏳ Add decision logic rendering
- ⏳ Add clickable historical assessments

### Phase 6: Dashboard Enhancement (Week 4)
- ⏳ Create risk timeline visualization
- ⏳ Add historical charts
- ⏳ Add "Why this result?" panel
- ⏳ UI testing

### Phase 7: Experimental Pipeline (Week 5)
- ⏳ Create dataset_loader.py
- ⏳ Create experimental_split.py
- ⏳ Create evaluation_pipeline.py
- ⏳ Create metrics.py

### Phase 8: Evaluation & Testing (Week 5-6)
- ⏳ Run 60/40 experiment on Kaggle dataset
- ⏳ Calculate performance metrics
- ⏳ Compare NEWS2 vs. NEWS2+Trends
- ⏳ Generate evaluation report

### Phase 9: Documentation (Week 6)
- ⏳ Create ALGORITHM_SPECIFICATION.md
- ⏳ Create NEWS2_IMPLEMENTATION.md
- ⏳ Create TREND_DETECTION.md
- ⏳ Create EXPERIMENT_PROTOCOL.md
- ⏳ Create EVALUATION_RESULTS.md

### Phase 10: Git & Deployment (Week 6)
- ⏳ Create meaningful commits
- ⏳ Create git tags for milestones
- ⏳ Final testing
- ⏳ Deployment checklist

---

## 10. Files to Create

### New Python Modules
- `backend/vitals/utils/__init__.py` — Package marker
- `backend/vitals/utils/trend_engine.py` — Trend analysis logic
- `backend/vitals/utils/risk_engine.py` — Risk scoring logic
- `backend/vitals/utils/explainability.py` — Explanation generation
- `backend/experiments/__init__.py` — Experiments package
- `backend/experiments/dataset_loader.py` — Load Kaggle CSV
- `backend/experiments/experimental_split.py` — 60/40 split logic
- `backend/experiments/evaluation_pipeline.py` — Run experiments
- `backend/experiments/metrics.py` — Calculate performance metrics

### New Django Models
- Add to `backend/vitals/models.py`:
  - `RiskAssessment` model
  - Database migration file

### New Templates
- Potentially enhance `backend/templates/vitals/patient_vital_history.html`

### New Documentation
- `docs/DATASET_AUDIT.md` (DONE ✅)
- `docs/IMPLEMENTATION_PLAN.md` (THIS FILE)
- `docs/DATA_SPLIT_METHODOLOGY.md` — TBD
- `docs/ALGORITHM_SPECIFICATION.md` — TBD
- `docs/NEWS2_IMPLEMENTATION.md` — TBD
- `docs/TREND_DETECTION.md` — TBD
- `docs/RISK_CLASSIFICATION.md` — TBD
- `docs/ALERT_LOGIC.md` — TBD
- `docs/EXPLAINABILITY.md` — TBD
- `docs/EXPERIMENT_PROTOCOL.md` — TBD
- `docs/EVALUATION_RESULTS.md` — TBD
- `docs/RESEARCH_TRACEABILITY.md` — TBD

### New Tests
- `backend/tests/test_trend_engine.py`
- `backend/tests/test_risk_engine.py`
- `backend/tests/test_explainability.py`
- `backend/experiments/test_dataset_loader.py`
- `backend/experiments/test_split.py`

---

## 11. Files to Modify

### Core Model Files
- `backend/vitals/models.py`
  - Add RiskAssessment model
  - Modify auto_detect_deterioration signal
  - Add trend calculation methods
  
- `backend/vitals/admin.py`
  - Update admin interface for RiskAssessment

### Django Configuration
- `backend/settings.py`
  - Add new app references if needed

### Templates
- `backend/templates/vitals/patient_vital_history.html`
  - Add risk timeline section
  - Add explainability panel
  - Add clickable historical assessments
  - Add charts/visualizations

### URLs & APIs
- `backend/vitals/urls.py`
  - Add new API endpoints

### Views
- `backend/vitals/views.py`
  - Add RiskAssessment serialization
  - Add explainability views

---

## 12. Key Risks & Mitigation

### Risk 1: Dataset Size
**Issue**: 200K observations × 17 columns large for real-time calculation
**Mitigation**: 
- Cache trend calculations
- Use database indexing
- Limit historical reconstruction to last 48 hours

### Risk 2: Single-Date Data
**Issue**: All Kaggle data from one date; cannot generalize to real practice
**Mitigation**: 
- Clearly document limitation
- Test on real Jomingo data once available
- Use synthetic multi-day splits for development

### Risk 3: Missing ACVPU
**Issue**: NEWS2 incomplete without consciousness assessment
**Mitigation**: 
- Default ACVPU to "Alert" (0 points) for dataset
- Document this assumption
- Note that real implementation requires ACVPU measurement

### Risk 4: Ground Truth Ambiguity
**Issue**: Kaggle labels ("High Risk") may not match real deterioration
**Mitigation**: 
- Evaluate against provided labels (what we have)
- Test against real outcome data when available
- Document that evaluation is against synthetic labels

### Risk 5: Over-fitting to Kaggle Dataset
**Issue**: Algorithm calibrated on specific date's patterns
**Mitigation**: 
- Use strict 60/40 split
- Never tune against test set
- Plan for re-calibration on real data

---

## 13. Success Criteria

### For Each Phase
- ✅ Unit tests pass
- ✅ Integration tests pass
- ✅ No unexplained errors
- ✅ Code review completed
- ✅ Documentation updated

### For Final System
- ✅ NEWS2 engine accurate
- ✅ Trend detection identifies gradual deterioration
- ✅ Multi-parameter analysis detects simultaneous worsening
- ✅ Risk timeline renders correctly
- ✅ Explainability panel shows decision logic
- ✅ 60/40 evaluation completed
- ✅ Metrics calculated and documented
- ✅ Research artifacts created
- ✅ All tests passing
- ✅ Git history clean and meaningful

---

## 14. Next Steps

**IMMEDIATELY**:
1. Review this plan
2. Confirm phases and timeline are acceptable
3. Identify any blockers

**THEN**:
1. Create RiskAssessment database model
2. Create migration
3. Begin Phase 1: Foundation

**BEFORE CODING EACH PHASE**:
1. Create detailed specification document
2. Outline test cases
3. Get approval to proceed

---

**Plan Created**: 10 August 2026  
**Status**: Ready for review and approval  
**Expected Completion**: 6-8 weeks (depending on refinements)

