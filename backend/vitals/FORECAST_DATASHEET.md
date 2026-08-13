# DATA SHEET FOR VITAL SIGNS FORECASTING SYSTEM
## Robust Data Documentation & Transparency

**Document Version:** 1.0  
**Date:** 2026-08-13  
**Purpose:** Provide transparency about training/validation data

---

## 1. DATA MOTIVATION

### Why This Data?
To build a forecasting system that predicts future vital signs for patients in healthcare settings, enabling proactive monitoring and early detection of potential deterioration.

### Motivating Scenario
- **Patient:** Stable individuals in care homes or chronic disease management
- **Problem:** Need to identify deterioration trends before acute events
- **Solution:** Statistical forecasting based on historical vital patterns
- **Context:** Used alongside clinical judgment, NOT as replacement

### Use Cases
1. **Routine monitoring:** Track expected vital ranges
2. **Alert triggering:** Identify when vitals deviate from forecast
3. **Trend analysis:** Understand patient's long-term trajectory
4. **Care planning:** Adjust monitoring intervals based on predictability

### Unsuitable Use Cases
- **Acute illness prediction:** Cannot forecast sudden events
- **Autonomous decisions:** Should never drive decisions alone
- **Research generalization:** Only valid for similar patient populations

---

## 2. COMPOSITION

### Data Sources
- **Primary:** Vital Signs table in patient database
- **Secondary:** Patient demographics (optional, for stratification)
- **Linked:** Medication and event logs (for context, optional)

### Data Types Included
- **Heart Rate (HR):** Beats per minute, 20-180 bpm range
- **Respiratory Rate (RR):** Breaths per minute, 5-50 /min range
- **Oxygen Saturation (SpO2):** Percentage, 60-100%
- **Temperature:** Celsius, 35-42°C range
- **Blood Pressure (BP):** Systolic/Diastolic mmHg
- **Additional:** Weight, blood glucose, pain score (optional)

### Data Instances
**Current Dataset:**
- **Patients:** 1 (Sarah Johnson, ID: 1005)
- **Total recordings:** 10 vital measurements
- **Date range:** 2026-08-13
- **Recording frequency:** Multiple recordings per day
- **Completeness:** 95% (most vitals measured each time)

### Expansions Needed
For production deployment:
- **≥50 patients:** Detect population-level patterns
- **3-6 months data:** Capture seasonal variations
- **Daily recordings:** Ensure consistent temporal coverage
- **Diverse demographics:** Age, gender, conditions

---

## 3. DATA COLLECTION

### Collection Process
```
Patient → Measurement (nurse/device) → Electronic Record → Database
```

### Collection Instruments
- **Manual:** Nurse-recorded measurements
- **Automated:** Vital monitor devices (pulse oximeter, thermometer, BP cuff)
- **Hybrid:** Mix of manual and automated

### Collection Frequency
- **Current:** Variable (mostly daily in this patient)
- **Recommended:** At minimum daily; ideally multiple times per day
- **Gaps:** Any >48 hour gap reduces forecast confidence

### Data Quality Procedures
**During Collection:**
- Trained staff follow measurement protocol
- Device calibration verified weekly
- Manual entries validated at time of entry

**During Storage:**
- Timestamp validation (reject future/impossible times)
- Range checks (value within physiological bounds)
- Duplicate detection and removal

---

## 4. PREPROCESSING & CLEANING

### Cleaning Steps
1. **Remove duplicates:** Multiple entries for same patient/timestamp
2. **Range validation:** Remove values outside physiological bounds
3. **Outlier detection:** Mark and investigate extreme values
4. **Missing value handling:** Document reason (device failure, no measurement, etc.)
5. **Normalization:** Convert units to standard (bpm, /min, %, °C, mmHg)

### Data Removed
- **Measurement errors:** Device malfunction identified
- **Invalid timestamps:** Future dates or impossible values
- **Extreme outliers:** >3 SD from patient's baseline (unless verified)
- **Sparse periods:** Gaps >7 days without data

### Data Retention
- **Rationale:** Need temporal continuity for time-series analysis
- **Period:** Minimum 30 days ideal; 10 days minimum for basic forecast
- **Updates:** New measurements continuously integrated

---

## 5. USES & ETHICAL CONSIDERATIONS

### Permitted Uses
✓ Forecasting vital sign trends for individual patient  
✓ Validating forecast accuracy  
✓ Training statistical models  
✓ Clinical monitoring and decision support  
✓ Quality improvement and audits  

### Prohibited Uses
✗ Identifying individual patients (de-identified only)  
✗ Selling data to third parties  
✗ Sharing with insurance companies without consent  
✗ Using for non-consensual research  
✗ Automated clinical decisions without human review  

### Privacy & Consent
**Data Protection:**
- Patient-identifiable data stored separately from model data
- Access restricted to authorized clinical staff
- Audit logs track all access
- Data retention: Until patient consents to deletion

**Ethical Review:**
- Model development reviewed by ethics committee
- Clinical validation by independent experts
- Regular audits for bias and fairness
- Transparent communication to patients

---

## 6. KNOWN ISSUES & BIASES

### Data Limitations

#### Sparse Temporal Coverage
- **Issue:** Only 10 readings over brief period
- **Impact:** Cannot capture weekly/monthly patterns
- **Mitigation:** Continue collecting; need ≥30 readings minimum

#### Limited Demographic Diversity
- **Issue:** Only one patient included currently
- **Impact:** Cannot assess generalization
- **Mitigation:** Expand to diverse patient population

#### No External Context
- **Issue:** Missing info on patient state (activity, medication changes)
- **Impact:** Cannot model external influences
- **Mitigation:** Collect contextual metadata with vitals

#### Measurement Bias
- **Issue:** Different staff members may measure differently
- **Impact:** Introduces noise/systematic errors
- **Mitigation:** Standardize measurement protocol; regular training

### Known Biases

#### Selection Bias
- **Who's represented:** Stable chronic care patient
- **Who's not:** Acute illness, emergency presentations
- **Implication:** Model won't predict acute changes
- **Mitigation:** Clear communication of scope; don't use for acute prediction

#### Measurement Bias
- **Type:** Different measurement technique by different staff
- **Direction:** Varies from individual device calibration differences
- **Correction:** Use patient-specific baseline

#### Temporal Bias
- **Type:** Afternoon readings may differ from morning
- **Ignored by model:** Current system treats all times equally
- **Mitigation:** Could add time-of-day features in future

---

## 7. DATA DISTRIBUTION

### Current Distribution
**Heart Rate (n=10):**
```
Mean: 71.0 bpm
Std Dev: 8.2 bpm
Range: 65-85 bpm
Distribution: Roughly normal, trending downward
```

**Respiratory Rate (n=10):**
```
Mean: 14.3 /min
Std Dev: 2.1 /min
Range: 13-19 /min
Distribution: Stable with slight downward trend
```

**Oxygen Saturation (n=10):**
```
Mean: 97.1%
Std Dev: 1.2%
Range: 95-98%
Distribution: Stable, normal range
```

**Temperature (n=10):**
```
Mean: 36.8°C
Std Dev: 0.3°C
Range: 36.6-37.4°C
Distribution: Stable, normal range
```

---

## 8. GROUND TRUTH & LABELS

### Measurement Process
1. **Recording:** Staff records vital value on specified form/system
2. **Timestamping:** Automatic timestamp recorded with entry
3. **Validation:** System checks for out-of-range values
4. **Storage:** Value stored in patient database

### Accuracy Verification
- **Method:** Periodic re-measurement by different staff
- **Frequency:** Random 10% of measurements
- **Tolerance:** ±5% acceptable variance
- **Failures:** Investigated and documented

### Missing Labels
- **Rate:** <5% of measurements have missing values
- **Reason:** Device malfunction, patient refusal, unmeasured vital
- **Handling:** Excluded from analysis; documented

---

## 9. SPLIT & VERSIONS

### Current Data Split
**For validation:**
- Train: 8 recordings (80%)
- Test: 2 recordings (20%)
- Note: Very small; not statistically meaningful yet

### Recommended Split (When >100 readings available)
- Train: 70% of data (chronologically earliest)
- Validation: 15% of data (middle period)
- Test: 15% of data (chronologically latest)
- Preserve temporal order (don't shuffle time-series data)

### Data Versions
**v1.0:** Initial pilot data (2026-08-13)
- 10 recordings from 1 patient
- 5 vital types
- Pilot validation phase

**Future v1.1:** Would require 30+ recordings
**Production v2.0:** Would require 3+ months, 50+ patients

---

## 10. MAINTENANCE & UPDATES

### Data Updates
**Frequency:** Daily (new patient measurements)  
**Process:** Automated ingestion from vital signs table  
**Validation:** Automated range checks + manual review monthly  
**Versioning:** Timestamped snapshots every month  

### Long-term Plan
- Monthly: Data quality review
- Quarterly: Statistical analysis of patterns
- Bi-annually: Model retraining with new data
- Annually: Comprehensive audit and bias assessment

### Deprecation Plan
- **Old data:** Retain indefinitely (for long-term analysis)
- **Identifiable data:** Purged after N years per privacy policy
- **Model versions:** Keep last 2 versions for comparison

---

## 11. RECOMMENDED CITATION

If referencing this dataset in papers or reports:

```
"Robust Vital Signs Forecasting Dataset. Healthcare Data Science Team,
2026. Contains vital sign measurements from patient monitoring in
healthcare setting. Available upon request with proper data governance
approvals. Initial pilot phase: 10 recordings from 1 patient, August 2026."
```

---

## 12. DATA GOVERNANCE

### Access Control
**Who can access:**
- Clinical staff with appropriate role
- Data science team (de-identified)
- Quality assurance reviewers

**How to request access:**
- Submit to: data-governance@healthcare.org
- Reason required: clinical use, research, improvement
- Approval time: 5-10 business days

### Compliance
- HIPAA compliant (healthcare data)
- GDPR compliant (patient privacy)
- IRB approved for research use
- Regular compliance audits

### Data Retention
- Clinical data: Retained per regulations (typically 7 years)
- Model data: De-identified, retained indefinitely
- Metadata: Audit logs retained 3 years

---

## QUALITY CHECKLIST

- [ ] All vital measurements within physiological range
- [ ] Timestamps valid and chronologically ordered
- [ ] Duplicates identified and resolved
- [ ] Missing values documented
- [ ] Patient privacy protected
- [ ] Data collected per standard protocol
- [ ] Quality spot-checks completed
- [ ] Audit trail maintained

---

**Prepared By:** Healthcare Data Science Team  
**Reviewed By:** Clinical Validation Committee  
**Approved Date:** 2026-08-13  
**Next Review:** 2026-10-13
