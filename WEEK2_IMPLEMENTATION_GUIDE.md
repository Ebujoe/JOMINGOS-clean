# WEEK 2: DATA FOUNDATION COMPLETION GUIDE

**Status:** Implementation Ready  
**Phase:** Phase 1 - Data Foundation (Weeks 1-2)  
**Goal:** Reach 30+ readings per patient and calculate stable baselines  

---

## What's New This Week

Week 2 provides tools to:
1. **Generate realistic test data** - Reach 30+ readings quickly
2. **Assess quality comprehensively** - Detailed quality metrics
3. **Analyze baseline stability** - Determine readiness for forecasting
4. **Generate readiness reports** - Week 2 completion checklist

---

## Week 2 Implementation (30 minutes to completion)

### Step 1: Migrate Database (if not done)

```bash
python manage.py migrate
```

### Step 2: Generate Test Data (5 minutes)

Generate 30 realistic vitals per patient:

```bash
# Generate test data for all patients
python manage.py generate_test_vitals --count=30

# With automatic validation
python manage.py generate_test_vitals --count=30 --validate

# Deteriorating pattern (for testing)
python manage.py generate_test_vitals --count=30 --deteriorating

# Specific patient
python manage.py generate_test_vitals --patient=1 --count=30
```

**Output:** Shows progress for each patient
```
Patient: Sarah Johnson (ID: 1)
  [MODE] Normal variation
  Recording 30 vitals...
  ✓ Created 30 vitals (30 validated)
  Calculating baselines...
  ✓ Calculated 6 baselines
    - heart_rate: 72.0±8.5 (n=30)
    - respiratory_rate: 16.0±2.1 (n=30)
    ...
```

### Step 3: Run Validation Pipeline (2 minutes)

Validate all vitals and calculate baselines:

```bash
python manage.py validate_and_calculate_baselines

# With quality reports
python manage.py validate_and_calculate_baselines --report

# Specific patient
python manage.py validate_and_calculate_baselines --patient=1 --report
```

### Step 4: Generate Week 2 Report (1 minute)

Check readiness for Phase 2:

```bash
# Full cohort report
python manage.py week2_report

# Single patient with stability analysis
python manage.py week2_report --patient=1 --stability

# Export to JSON
python manage.py week2_report --export
```

**Sample Output:**
```
======================================================================
WEEK 2 READINESS REPORT
======================================================================

COHORT SUMMARY
  Patients with data: 1
  Ready for Phase 2: 1
  Progress: 100.0%
  Phase 2 readiness: READY

AGGREGATE METRICS
  Total measurements: 30
  Approved: 29
  Approval rate: 96.7%
  Avg quality score: 92.5
  Avg approval rate: 96.7%

PER-PATIENT DETAILS
Patient                        Approved     Ready
----------------------------------------------------
Sarah Johnson                  29/30        ✓

WEEK 2 READINESS ASSESSMENT
  Status: ✓ READY FOR PHASE 2
  Score: 92/100

  Details:
    ✓ Sufficient data (30+ readings)
    ✓ Excellent quality (<5% rejection)
    ✓ Excellent measurement quality (90+)
    ✓ Baselines calculated (6 vitals)
    ✓ Multiple vital types (6)

  Recommendations:
    Ready to proceed with baseline validation
```

---

## Understanding the Tools

### Data Generator (generate_test_vitals)

Generates realistic vital data with:
- **Circadian rhythms** - HR higher during day, lower at night
- **Activity effects** - HR increases with activity
- **Measurement noise** - Realistic variation
- **Temporal spacing** - ~6 hours between measurements

**Vital Patterns:**
```
Heart Rate:    72±8 bpm (higher 8am-8pm, lower at night)
Respiratory:   16±2 breaths/min
SpO2:          97.5±1% (stable)
Temperature:   37.0±0.3°C (peaks 2-4pm)
BP Systolic:   120±8 mmHg (peaks morning)
```

### Quality Report (week2_report)

Generates readiness score based on:

| Factor | Points | Criteria |
|--------|--------|----------|
| Data Volume | 30 | 30+ approved readings |
| Quality | 30 | <5% rejection rate |
| Quality Score | 20 | 90+ average |
| Baselines | 10 | All vitals calculated |
| Coverage | 10 | 4+ vital types |
| **Total** | **100** | **Score** |

**Readiness Levels:**
- **80-100:** READY_FOR_PHASE2 - Proceed to Phase 2
- **60-80:** IN_PROGRESS - Continue data collection
- **<60:** NEEDS_ATTENTION - Address data quality issues

### Stability Analyzer (week2_report --stability)

Analyzes whether baselines are stable:
- Splits data into early/late periods
- Calculates mean shift percentage
- Recommends readiness
- Detects unstable patterns

**Status:**
- **STABLE:** <5% mean shift → Ready for forecasting
- **SOMEWHAT_STABLE:** 5-10% shift → Monitor closely
- **UNSTABLE:** >10% shift → Collect more data

---

## Step-by-Step Workflow

### For Development/Testing

```bash
# 1. Generate test data (creates 30 realistic vitals)
python manage.py generate_test_vitals --count=30 --validate

# 2. Validate and calculate baselines
python manage.py validate_and_calculate_baselines --report

# 3. Check Week 2 readiness
python manage.py week2_report --stability

# 4. Examine detailed metrics
python manage.py week2_report --patient=1 --stability
```

### For Production (Real Data)

```bash
# 1. Record vitals via normal channels (web app)
# (Already validated on recording)

# 2. Daily: Run validation pipeline
python manage.py validate_and_calculate_baselines --report

# 3. Weekly: Check Week 2 readiness
python manage.py week2_report

# 4. When ready: Proceed to Phase 2
```

---

## Week 2 Success Criteria

### ✓ Data Collection
- [ ] 30+ readings per patient
- [ ] Multiple vital types (4+)
- [ ] Spread over at least 7 days
- [ ] Consistent measurement times

### ✓ Quality Validation
- [ ] >95% approval rate
- [ ] <5% rejection rate
- [ ] Average quality score >90
- [ ] Issues identified and resolved

### ✓ Baseline Calculation
- [ ] All vitals have baselines
- [ ] Baselines stable (mean shift <5%)
- [ ] Sufficient sample size (30+)
- [ ] Clinically reasonable values

### ✓ Readiness Assessment
- [ ] Week 2 score >80/100
- [ ] Status: READY_FOR_PHASE2
- [ ] All recommendations addressed
- [ ] Stability analysis passed

### ✓ Documentation
- [ ] Quality reports generated
- [ ] Readiness report completed
- [ ] Issues documented
- [ ] Improvements planned

---

## Data Quality Thresholds

### Approval Rates
- **95-100%:** Excellent ✓
- **90-95%:** Good ✓
- **80-90%:** Fair ⚠
- **<80%:** Poor ✗

### Quality Scores
- **90-100:** Excellent ✓
- **80-90:** Good ✓
- **70-80:** Fair ⚠
- **<70:** Poor ✗

### Baseline Stability
- **<5% shift:** Stable ✓
- **5-10% shift:** Moderate ⚠
- **>10% shift:** Unstable ✗

---

## Common Issues & Solutions

### Issue: Low Approval Rate (<90%)

**Diagnosis:**
```bash
python manage.py week2_report --patient=1
# Check "rejection_reasons" in output
```

**Solutions:**
1. **Out of range:** Check vital recording procedures
2. **Duplicate:** Ensure proper time spacing
3. **Temporal issues:** Verify timestamp order
4. **Outliers:** Review data collection context

**Action:**
```bash
# Retrain staff on recording procedures
# Review rejected vitals for patterns
# Adjust validation thresholds if needed
```

### Issue: Unstable Baseline (>10% mean shift)

**Diagnosis:**
```bash
python manage.py week2_report --patient=1 --stability
# Look for "Mean shift: >10%"
```

**Possible Causes:**
- Patient condition changing
- Different time of day measurements
- Measurement technique issues
- Artifact/noise in data

**Solution:**
- Collect more data over longer period
- Ensure consistent measurement times
- Monitor patient health status
- Review measurement procedures

### Issue: Low Quality Scores (<80)

**Diagnosis:**
```bash
python manage.py validate_and_calculate_baselines --report
# Check "average_quality_score"
```

**Common Causes:**
- Out of normal range warnings
- Occasional outliers
- Measurement errors

**Solution:**
- Review measurement techniques
- Check equipment calibration
- Verify vital recording procedures
- Retrain staff as needed

---

## Database Verification

### Check Data Collection Progress

```python
from vitals.models import VitalSigns
from patients.models import Patient

for patient in Patient.objects.all():
    count = VitalSigns.objects.filter(patient=patient, is_approved=True).count()
    print(f"{patient.name}: {count} approved vitals")
```

### Check Baseline Calculations

```python
from vitals.models import PatientBaselineData

for baseline in PatientBaselineData.objects.all():
    print(f"{baseline.patient.name} - {baseline.vital_name}: "
          f"{baseline.mean_value}±{baseline.std_dev} (n={baseline.n_samples})")
```

### Check Quality Metrics

```python
from vitals.models import VitalSigns
from django.db.models import Avg

vitals = VitalSigns.objects.all()
print(f"Total vitals: {vitals.count()}")
print(f"Approved: {vitals.filter(is_approved=True).count()}")
print(f"Avg quality: {vitals.filter(quality_score__isnull=False).aggregate(Avg('quality_score'))['quality_score__avg']:.1f}")
```

---

## Transitioning to Phase 2

When Week 2 readiness score > 80:

1. **Verify completeness:**
   ```bash
   python manage.py week2_report
   # All metrics should show GREEN (✓)
   ```

2. **Document baseline stability:**
   ```bash
   python manage.py week2_report --patient=1 --stability
   # All baselines should show STABLE
   ```

3. **Export final reports:**
   ```bash
   python manage.py week2_report --export
   # Creates week2_report_YYYY-MM-DD.json
   ```

4. **Proceed with Phase 2:**
   - Week 3-4: Deploy forecasting models
   - Integrate RobustForecastingEngine
   - Begin backtesting

---

## Week 2 Timeline

| When | Task | Command |
|------|------|---------|
| Day 1 | Generate 30 readings | `generate_test_vitals --count=30` |
| Day 1 | Validate all vitals | `validate_and_calculate_baselines` |
| Day 1 | Calculate baselines | (Automatic in validation) |
| Day 1 | Check readiness | `week2_report` |
| Days 2-7 | Collect real data | (Continue normal recording) |
| Day 7 | Final validation | `validate_and_calculate_baselines` |
| Day 7 | Final readiness check | `week2_report --stability` |
| Day 8 | Proceed to Phase 2 | (Start forecasting) |

---

## Success Indicators

✓ **Week 2 Complete When:**
1. 30+ readings per patient ✓
2. >95% approval rate ✓
3. >90 quality score ✓
4. All baselines calculated ✓
5. Baselines stable ✓
6. Readiness score >80 ✓
7. Ready for Phase 2 ✓

---

## Next Steps (Phase 2: Model Improvement)

**Weeks 3-4:**
- Deploy RobustForecastingEngine
- Implement uncertainty quantification
- Add clinical plausibility assessment
- Begin forecasting on validation set

**Expected Confidence:**
- 24h forecast: 25-35% confidence
- 7d forecast: 5-15% confidence
- Path to 70-85% by Week 6

---

## Support & Questions

**Data Generation Questions:**
- `backend/vitals/utils/data_generator.py`
- Run: `python manage.py generate_test_vitals --help`

**Quality Reporting Questions:**
- `backend/vitals/utils/data_quality_report.py`
- Run: `python manage.py week2_report --help`

**Management Commands:**
- `python manage.py generate_test_vitals --help`
- `python manage.py week2_report --help`
- `python manage.py validate_and_calculate_baselines --help`

---

## Summary

**Week 2 Tools Delivered:**
1. ✓ PatientVitalSimulator - Generate realistic vitals
2. ✓ BulkDataGenerator - Batch data creation
3. ✓ DataQualityReport - Comprehensive metrics
4. ✓ BaselineStabilityAnalyzer - Stability assessment
5. ✓ Management commands - Operational automation

**Ready to proceed to Phase 2 (Weeks 3-4): Model Improvement**

---

**Week 2 Status:** Implementation Ready  
**Commit:** Complete  
**Next Phase:** Week 3 - Model Deployment

