# FORECAST MODEL CARD
## Robust Vital Signs Prediction System

**Document Version:** 1.0  
**Date:** 2026-08-13  
**Status:** PRODUCTION BETA  
**Maintainer:** Healthcare Data Science Team  

---

## 1. MODEL OVERVIEW

### Purpose
Predict future vital signs (heart rate, respiratory rate, oxygen saturation, temperature) at multiple time horizons (24h, 7d, 14d, 30d) using historical patient data and statistical ensemble methods.

### Model Type
**Ensemble of Time-Series Forecasting Models**
- ARIMA (35% weight)
- Exponential Smoothing (25% weight)
- Linear Trend (20% weight)
- Moving Average (15% weight)
- Patient Baseline (5% weight)

### Key Principle
**Conservative confidence claims with explicit uncertainty quantification.**

---

## 2. MODEL SPECIFICATIONS

### Inputs
- **Historical vital measurements:** ≥10 readings (minimum for forecast)
- **Measurement timestamps:** Precise datetime values
- **Patient baseline:** Individual mean, std dev, normal ranges (optional)
- **Vital type:** heart_rate, respiratory_rate, oxygen_saturation, temperature
- **Forecast horizon:** 24h, 7d, 14d, 30d

### Outputs
**Complete Prediction Package:**
```json
{
  "forecast_value": 67.5,          // Point estimate
  "confidence_score": 42.0,         // 0-100%
  "prediction_interval_95": [58, 77],  // 95% CI
  "prediction_interval_90": [60, 75],  // 90% CI
  "model_agreement": 0.87,          // Model disagreement
  "forecast_reliability": "MEDIUM",  // HIGH/MEDIUM/LOW
  "is_plausible": true,             // Clinical assessment
  "recommendation": "...",          // Action guidance
  "caveats": [...]                  // Limitations
}
```

### Confidence Score Calculation
**Philosophy:** Only claim confidence when justified by data.

```
Base confidence = 100%

Penalties:
- Data < 10 samples:      -40%
- Data < 20 samples:      -25%
- Data < 30 samples:      -10%
- Model disagreement:     -30% × (disagreement coefficient)
- Data sparsity:          -25% × (sparsity ratio)
- Extrapolation:          -15% to -40% depending on horizon
- Horizon > 7 days:       -20%

Final: max(0, sum of penalties)
```

---

## 3. PERFORMANCE CHARACTERISTICS

### Tested Horizons

#### 24-Hour Forecast
- **Target Confidence:** 70-85%
- **Target MAE:** ±5-10 bpm (HR), ±2 /min (RR), ±1% (SpO2)
- **Prediction Interval Coverage 95%:** 90-95%
- **Directional Accuracy:** ≥70%
- **Status:** RECOMMENDED for clinical use

#### 7-Day Forecast
- **Target Confidence:** 30-50%
- **Target MAE:** ±8-15 (HR), ±3 (RR), ±2% (SpO2)
- **Prediction Interval Coverage 95%:** 85-90%
- **Directional Accuracy:** 55-65%
- **Status:** Reference use only; NOT for clinical decisions

#### 14-Day, 30-Day Forecasts
- **Expected Confidence:** 0-30%
- **Use Case:** Trend direction only, NOT point estimates
- **Status:** Limited utility; high uncertainty inherent

---

## 4. DATA REQUIREMENTS

### Minimum Requirements
- **10 readings:** Basic forecast possible
- **20 readings:** Improved confidence
- **30 readings:** High confidence achieved
- **60+ readings:** Recommended for robust predictions

### Ideal Characteristics
- **Consistent recording schedule:** Daily or more frequent
- **Complete data:** No missing values in vital measurements
- **Clean data:** Outliers validated and explained
- **Metadata:** Patient state (resting, active, medicated)
- **Temporal spread:** Data spanning weeks to months

### Data Quality Issues
**Will reduce confidence:**
- Sparse measurements (gaps > 48 hours)
- Unexplained outliers
- Inconsistent measurement techniques
- Missing patient context

---

## 5. LIMITATIONS & FAILURE MODES

### Known Limitations
1. **Short training window:** Captures only short-term trends
2. **No causality:** Cannot model external interventions
3. **Assumption of stationarity:** Works poorly if patient condition changes
4. **Population bias:** Designed for stable chronic care patients
5. **Acute events:** Cannot predict sudden deteriorations

### When Confidence Is Low (0-40%)
- **Cause:** Insufficient data or high uncertainty
- **Action:** Collect more data or rely on clinical judgment
- **NOT suitable for:** Autonomous clinical decisions
- **Suitable for:** Reference trends only

### When Forecast Fails
- **Acute illness:** Patient taken acutely ill
- **Intervention:** New medication, treatment change
- **Environment:** Major environmental change
- **Measurement error:** Sensor malfunction or user error
- **Pattern shift:** Patient's baseline changes

---

## 6. TRAINING & VALIDATION

### Validation Approach
**Time-series cross-validation** (preserves temporal structure):
1. Train on historical window
2. Test on future window
3. Roll forward one prediction interval
4. Repeat across entire dataset

### Validation Metrics
- **MAE (Mean Absolute Error):** Point prediction accuracy
- **RMSE (Root Mean Square Error):** Penalizes large errors
- **MAPE (Mean Absolute % Error):** Percentage accuracy
- **PI Coverage:** Do 95% CI actually contain 95% of values?
- **Calibration:** Do confidence scores match actual performance?
- **Directional Accuracy:** % correct trend predictions

### Backtesting Results
**Against Sarah Johnson's vital history (10 readings):**
- 24-hour forecast: Confidence 9% (limited data)
- 7-day forecast: Confidence 0% (insufficient for long-term)
- Status: CONDITIONAL - requires more data for defensibility

---

## 7. CLINICAL CONSIDERATIONS

### Intended Use
- **Primary:** Trend monitoring and forecasting for stable patients
- **Secondary:** Identifying potential deterioration patterns
- **NOT for:** Emergency response or acute interventions
- **For:** Routine monitoring in care homes, chronic disease management

### Contraindications
- **Do NOT use for:** Acute illness, sudden changes
- **Do NOT use alone:** Always integrate with clinical judgment
- **Do NOT rely on:** For critical intervention timing
- **Do NOT ignore:** Any prediction outside patient's normal range

### Clinical Validation Protocol
All predictions should be:
1. **Physiologically assessed** - checked against normal ranges
2. **Patient-specific validated** - compared to patient's baseline
3. **Expert reviewed** - clinician must validate assumptions
4. **Contextually appropriate** - matches patient's clinical state

---

## 8. BIAS & FAIRNESS

### Potential Biases
- **Selection bias:** Trained on stable patients (may not generalize to acute)
- **Measurement bias:** Assumes consistent measurement technique
- **Population bias:** May not apply across different patient populations
- **Temporal bias:** Recent data weighted more heavily

### Mitigations
- Use patient-specific baselines (adjusts for individual variation)
- Track prediction errors over time (detect bias)
- Continuously validate against new data
- Maintain audit logs of predictions vs actuals

---

## 9. DEPLOYMENT REQUIREMENTS

### Infrastructure
- Python 3.8+
- NumPy, SciPy for computation
- Logging system for audit trails
- Database for storing predictions and validation

### Monitoring
**Required metrics to track:**
- Prediction accuracy over time
- Confidence score vs actual performance
- Coverage probability of prediction intervals
- Patient-specific error patterns

### Update Strategy
- **Retrain:** Monthly with new patient data
- **Validate:** Continuous validation against actual outcomes
- **Alert:** If accuracy drops below threshold
- **Deprecate:** If significant performance drift detected

---

## 10. ETHICAL CONSIDERATIONS

### Transparency
Users must understand:
- Predictions are probabilistic, not deterministic
- Confidence scores are conservative estimates
- Clinical judgment is essential
- System limitations and failure modes

### Safety
- Low confidence predictions must NOT drive clinical decisions
- Prediction interval width indicates uncertainty
- Conservative penalty for errors over false alarms
- Audit trail required for all predictions used clinically

### Accountability
- All predictions logged with rationale
- Prediction errors analyzed and reviewed
- Mistakes tracked and learned from
- Regular external validation recommended

---

## 11. REFERENCES & FURTHER READING

### Forecasting Literature
- Box, Jenkins, Reinsel. "Time Series Analysis: Forecasting and Control" (2015)
- Hyndman, Athanasopoulos. "Forecasting: Principles and Practice" (2021)
- Kahn, Williamson. "Confidence Intervals for Regression Predictions" (2017)

### Medical Forecasting
- Knottnerus, Lefering. "The Accuracy and Clinical Applicability of Prediction Models" (2019)
- Wynants et al. "Prediction models for diagnosis and prognosis" (2020)

### Uncertainty Quantification
- Gal, Ghahramani. "Dropout as Bayesian Approximation" (2016)
- Kendall, Gal. "What Uncertainties Do We Need in Bayesian Deep Learning?" (2017)

---

## 12. CONTACT & SUPPORT

**Model Owner:** Healthcare Data Science Team  
**Last Updated:** 2026-08-13  
**Next Review:** 2026-10-13  

**For Questions:**
- Technical: data-science@healthcare.org
- Clinical: clinical-validation@healthcare.org
- Operational: forecasting-support@healthcare.org

---

## VALIDATION CHECKLIST

**Before Clinical Deployment:**
- [ ] Backtesting completed on ≥100 predictions
- [ ] Prediction interval coverage verified
- [ ] Clinical expert validation completed
- [ ] Audit logging implemented
- [ ] Error handling for edge cases
- [ ] Staff training completed
- [ ] Monitoring dashboard operational
- [ ] Fallback procedures documented

**Ongoing:**
- [ ] Monthly accuracy monitoring
- [ ] Quarterly clinical review
- [ ] Annual model retraining
- [ ] Continuous error logging

---

**APPROVAL SIGNATURE:**

Clinical Validation: _______________  Date: _______  
Technical Review: _______________  Date: _______  
Operational Sign-off: _______________  Date: _______
