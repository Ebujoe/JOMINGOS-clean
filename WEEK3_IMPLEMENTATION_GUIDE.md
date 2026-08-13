# WEEK 3: MODEL IMPROVEMENT - IMPLEMENTATION GUIDE

**Status:** Implementation Ready  
**Phase:** Phase 2 - Model Improvement (Weeks 3-4)  
**Goal:** Deploy forecasting models and establish backtesting  

---

## What's New This Week

Week 3 provides:
1. **ForecastingService** - End-to-end forecasting integration
2. **Backtesting Framework** - Validate forecast accuracy
3. **PatientForecast Model** - Store predictions with full audit trail
4. **Confidence Scoring** - Conservative 0-100% confidence levels
5. **Management Commands** - Operational forecasting tools

---

## Week 3 Quick Start (15 minutes)

### Step 1: Apply Database Migration

```bash
python manage.py migrate
```

This creates the `PatientForecast` table for storing forecasts.

### Step 2: Generate Test Forecasts

```bash
# Generate forecasts for all patients
python manage.py generate_forecasts

# For specific patient
python manage.py generate_forecasts --patient=1

# Store in database
python manage.py generate_forecasts --store

# All horizons (24h, 7d, 14d, 30d)
python manage.py generate_forecasts --all-horizons --store
```

### Step 3: Run Backtesting

```bash
# Backtest forecasts against actual values
python manage.py generate_forecasts --backtest

# Backtest specific patient
python manage.py generate_forecasts --patient=1 --backtest
```

### Step 4: View Results

Forecasts are stored in the database and accessible via Django admin or custom queries:

```python
from vitals.models import PatientForecast

# Get latest forecast
forecast = PatientForecast.objects.filter(
    patient_id=1,
    vital_name='heart_rate',
    horizon_hours=24
).order_by('-created_at').first()

print(f"Forecast: {forecast.forecast_value}")
print(f"Confidence: {forecast.confidence_score:.0f}%")
print(f"95% CI: [{forecast.prediction_interval_95_lower}, {forecast.prediction_interval_95_upper}]")
```

---

## Understanding the Forecasting Service

### Core Components

**ForecastingService:**
- Integrates RobustForecastingEngine with Django models
- Handles data retrieval and baseline lookup
- Stores forecasts in database
- Generates visualization data

**BacktestingService:**
- Tests historical forecasts against actual outcomes
- Calculates error metrics (MAE, RMSE, MAPE)
- Validates prediction intervals
- Assesses model performance

**PatientForecast Model:**
- Immutable record of each forecast
- Stores point estimate and uncertainty bounds
- Tracks confidence score and reliability
- Records actual value when available
- Calculates forecast error

### Forecast Output

Each forecast includes:

```python
{
    'status': 'success',
    'vital_name': 'heart_rate',
    'horizon_hours': 24,
    'forecast_value': 75.2,              # Point estimate
    'confidence_score': 18.5,            # 0-100%
    
    # Uncertainty bounds
    'prediction_interval_95_lower': 65.1,
    'prediction_interval_95_upper': 85.3,
    'prediction_interval_90_lower': 68.0,
    'prediction_interval_90_upper': 82.4,
    
    # Model diagnostics
    'model_agreement': 0.92,             # 0-1, high is better
    'model_count': 5,
    'models_used': ['ARIMA', 'ExponentialSmoothing', 'LinearTrend', 'MovingAverage', 'Baseline'],
    
    # Uncertainty components
    'data_sufficiency': 0.30,            # With 9 readings / 30 target
    'extrapolation_distance': 0.10,      # How far beyond training data
    'model_disagreement_component': 0.05,
    'data_sparsity_component': 0.09,
    'extrapolation_component': 0.01,
    'patient_variability_component': 0.01,
    
    # Assessment
    'is_plausible': true,
    'plausibility_score': 0.95,
    'forecast_reliability': 'LOW',       # HIGH, MEDIUM, LOW
    'recommendation': 'Reference forecast only - limited data',
    'clinical_notes': 'Patient\'s heart rate stable around baseline...',
    'caveats': [
        'Limited data (9 readings < 30 recommended)',
        'High data sparsity (70% penalty)',
        'Conservative confidence applied'
    ]
}
```

---

## Confidence Scoring Explained

Confidence starts at **100** and is penalized for:

| Factor | Penalty | Condition |
|--------|---------|-----------|
| Data volume | -40 | <10 readings |
| | -25 | <20 readings |
| | -10 | <30 readings |
| Model disagreement | -30 | High CV across models |
| Data sparsity | -25 | < 50% of recommended |
| Extrapolation | -15 to -40 | Depending on horizon |
| Long horizons | -20 | >7 days |

**Example:**
- 10 readings: 100 - 40 (data) - 20 (horizon) = **40% confidence**
- 30 readings: 100 - 10 (data) - 20 (horizon) = **70% confidence**

### Confidence by Horizon

| Horizon | Current | Week 3 | Week 4 | Week 6 | Week 7+ |
|---------|---------|--------|--------|--------|---------|
| 24h | 9% | 15-20% | 25-35% | 60-70% | **70-85%** |
| 7d | 0% | 5-10% | 10-15% | 30-40% | **30-50%** |
| 14d | 0% | 0-5% | 5-10% | 15-25% | **0-30%** |
| 30d | 0% | 0% | 0-5% | 5-15% | **0-20%** |

---

## Backtesting Framework

### How It Works

1. **For each historical point** (excluding last 10 measurements):
   - Use data up to that point
   - Generate forecast for specified horizon
   - Wait for actual measurement at forecast horizon
   - Compare forecast to actual

2. **Calculate error metrics:**
   - MAE: Mean Absolute Error
   - RMSE: Root Mean Square Error
   - MAPE: Mean Absolute Percentage Error

3. **Assess accuracy:**
   - How many forecasts were accurate?
   - Were prediction intervals calibrated?
   - Any systematic bias?

### Backtest Results Example

```
Heart Rate (24h horizon)
  Forecasts tested: 12
  MAE: 3.2 bpm       (good)
  RMSE: 4.1 bpm      (good)
  MAPE: 4.5%         (excellent)
  
  Interpretation:
  - Average error: 3.2 bpm
  - 95% PI coverage: 92% (should be ~95%)
  - Confidence claim: Justified ✓
```

### Running Backtests

```bash
# Single patient, all vitals
python manage.py generate_forecasts --patient=1 --backtest

# All patients
python manage.py generate_forecasts --backtest

# With confidence display
python manage.py generate_forecasts --backtest --store
```

---

## Integration with Django Views

### Get Latest Forecast in View

```python
from vitals.models import PatientForecast
from vitals.utils.forecasting_service import ForecastingService

def patient_detail(request, patient_id):
    # Get or generate forecast
    service = ForecastingService()
    forecast = service.generate_forecast_for_patient(
        patient_id=patient_id,
        vital_name='heart_rate',
        horizon_hours=24
    )
    
    # Get visualization data
    viz_data = service.generate_forecast_visualization_data(
        patient_id=patient_id,
        vital_name='heart_rate',
        horizon_hours=24
    )
    
    context = {
        'forecast': forecast,
        'viz_data': viz_data,
    }
    return render(request, 'patient_detail.html', context)
```

### Display Forecast in Template

```html
<div class="forecast-card">
  <h3>24-Hour Heart Rate Forecast</h3>
  
  <div class="forecast-value">
    {{ forecast.forecast_value|floatformat:1 }} bpm
    <span class="confidence" style="color: {% if forecast.confidence_score > 70 %}green{% elif forecast.confidence_score > 40 %}orange{% else %}red{% endif %}">
      {{ forecast.confidence_score|floatformat:0 }}% confidence
    </span>
  </div>
  
  <div class="uncertainty-bounds">
    <p>95% Prediction Interval:</p>
    <p>{{ forecast.prediction_interval_95_lower|floatformat:1 }} - {{ forecast.prediction_interval_95_upper|floatformat:1 }} bpm</p>
  </div>
  
  <div class="recommendation">
    <p>{{ forecast.recommendation }}</p>
  </div>
</div>
```

---

## Week 3 Success Criteria

### ✓ Model Deployment
- [x] ForecastingService integrated
- [x] RobustForecastingEngine deployed
- [x] Uncertainty quantification implemented
- [x] Backtesting framework in place

### ✓ Confidence Improvement
- [ ] Generate 50+ forecasts
- [ ] Run backtesting on all vitals
- [ ] Confidence improves to 15-20% (24h)
- [ ] Accuracy metrics acceptable (MAE < 5)

### ✓ Data Quality
- [ ] Data: 30+ readings per patient ✓
- [ ] Baselines: Calculated and stable ✓
- [ ] Validation: >95% approval rate ✓
- [ ] Forecasting: Ready for production ✓

### ✓ Documentation
- [ ] Model behavior documented
- [ ] Confidence scoring explained
- [ ] Backtesting results analyzed
- [ ] Recommendations generated

---

## Common Usage Patterns

### Generate Single Forecast

```python
from vitals.utils.forecasting_service import ForecastingService

service = ForecastingService()

# Heart rate 24-hour forecast
forecast = service.generate_forecast_for_patient(
    patient_id=1,
    vital_name='heart_rate',
    horizon_hours=24
)

print(f"Forecast: {forecast['forecast_value']:.1f}")
print(f"Confidence: {forecast['confidence_score']:.0f}%")
print(f"95% CI: [{forecast['prediction_interval_95_lower']:.1f}, {forecast['prediction_interval_95_upper']:.1f}]")
```

### Batch Forecasting

```python
# Generate for all vitals, multiple horizons
forecasts = service.generate_forecasts_for_all_vitals(
    patient_id=1,
    horizons=[24, 168, 336]  # 24h, 7d, 14d
)

for vital_name, vital_forecasts in forecasts.items():
    for forecast in vital_forecasts:
        print(f"{vital_name} @ {forecast['horizon_hours']}h: "
              f"{forecast['forecast_value']:.1f} "
              f"({forecast['confidence_score']:.0f}%)")
```

### Store Forecasts

```python
# Generate and store
forecast = service.generate_forecast_for_patient(
    patient_id=1,
    vital_name='heart_rate',
    horizon_hours=24
)

if forecast['status'] == 'success':
    forecast_record = service.store_forecast(patient_id=1, forecast_dict=forecast)
    print(f"Stored forecast {forecast_record.id}")
```

### Retrieve Stored Forecast

```python
from vitals.models import PatientForecast

# Latest 24h heart rate forecast
forecast = PatientForecast.objects.filter(
    patient_id=1,
    vital_name='heart_rate',
    horizon_hours=24
).order_by('-created_at').first()

if forecast:
    print(f"Forecast: {forecast.forecast_value}")
    print(f"Confidence: {forecast.confidence_score:.0f}%")
    print(f"Accuracy: {forecast.is_accurate}")  # Was it right?
```

---

## Troubleshooting

### Issue: Low Confidence (< 10%)

**Causes:**
1. Insufficient data (<10 readings)
2. High data sparsity penalty
3. Long forecast horizon (>7 days)

**Solution:**
- Continue collecting data (target: 30+ readings)
- Use shorter horizons (24h > 7d)
- Monitor as more data accumulates

### Issue: Forecast Out of Bounds

**Causes:**
1. Extrapolation beyond typical range
2. Patient condition change
3. Data quality issue

**Solution:**
- Check quality_score of input measurements
- Review clinical context
- Monitor confidence score

### Issue: Backtesting Shows Poor Accuracy

**Causes:**
1. Model not calibrated to patient
2. Insufficient training data
3. Measurement errors in input data

**Solution:**
- Increase data collection to 50+ readings
- Check data quality metrics
- Review outliers in measurements
- Validate measurement procedures

---

## Next Steps (Week 4)

**Week 4: Model Improvement Continuation**
- Expand backtesting to 100+ predictions
- Time-series cross-validation
- Calibration curve analysis
- Confidence threshold optimization
- Integration with existing views

**Expected Progress:**
- Confidence: 15-20% → 25-35% (24h)
- Accuracy: MAE improves with more data
- Backtesting: 100+ validated forecasts
- Calibration: PI coverage near target

---

## Commands Reference

### Generate Forecasts

```bash
# All patients, default horizon (24h)
python manage.py generate_forecasts

# Specific patient, all horizons
python manage.py generate_forecasts --patient=1 --all-horizons

# Specific vital, store in database
python manage.py generate_forecasts --vital=heart_rate --store

# With backtesting
python manage.py generate_forecasts --backtest

# Complete analysis
python manage.py generate_forecasts --patient=1 --all-horizons --store --backtest
```

### Help

```bash
python manage.py generate_forecasts --help
python manage.py validate_and_calculate_baselines --help
python manage.py week2_report --help
python manage.py generate_test_vitals --help
```

---

## Summary

**Week 3 Deliverables:**
1. ✓ ForecastingService - Production-grade integration
2. ✓ BacktestingService - Accuracy validation
3. ✓ PatientForecast Model - Audit trail storage
4. ✓ Management Command - Operational tools
5. ✓ Database Migration - Schema update

**Ready for:**
- Week 4: Extended backtesting and validation
- Week 5-6: Comprehensive cross-validation
- Week 7: Clinical validation
- Week 8: Production deployment

---

**Week 3 Status:** Implementation Ready  
**Confidence Progression:** 9% → 15-20% (24h forecasts)  
**Next Phase:** Week 4 - Extended Validation

