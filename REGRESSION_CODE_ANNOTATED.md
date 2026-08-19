# Regression & Explainable AI - Raw Code with Annotations

## FILE 1: vital_forecaster.py
**Location:** `backend/vitals/regression/vital_forecaster.py`

### MAIN CLASS - VitalSignsForecaster (Line 75-220)

```python
class VitalSignsForecaster:
    """Complete vital signs forecasting system with regression + explainable AI."""

    def __init__(self, vital_type: str):
        # INITIALIZATION - Set up the forecaster
        # Line 92: Store which vital sign we're forecasting (heart_rate, blood_pressure, etc)
        self.vital_type = vital_type
        
        # Line 93: Create ensemble object that will run 5 methods
        # This imports: ensemble_forecaster.py and creates EnsembleForecaster()
        self.ensemble = EnsembleForecaster()
        
        # Line 94: Create explainable AI scorer for confidence calculation
        # This imports: explainable_ai.py and creates ExplainableAIScorer()
        self.xai_scorer = ExplainableAIScorer()
```

### MAIN FORECAST METHOD (Line 96-155)

```python
def forecast(self, measurements: List[float]) -> ForecastResult:
    """
    THIS IS THE MAIN METHOD THAT DOES EVERYTHING
    Input: measurements = [72, 74, 75, 73, 76, 75, 77, 76, 78, 77, ...]
    Output: ForecastResult with forecast, confidence, and explanation
    """
    
    # ============ STEP 1: VALIDATION ============
    # Line 112-113: Check if we have data
    if not measurements or len(measurements) < 2:
        raise ValueError("Need at least 2 measurements")
    # Why? Need at least 2 points to calculate change

    # ============ STEP 2: RUN ENSEMBLE ============
    # Line 116: THIS IS WHERE THE REGRESSION HAPPENS
    # Goes to ensemble_forecaster.py and runs ALL 5 METHODS
    ensemble_forecast = self.ensemble.fit_and_predict(measurements)
    #
    # What happens here:
    # - ARIMA runs and produces: 67.16
    # - Exponential Smoothing runs and produces: 69.72
    # - Linear Trend runs and produces: 71.74
    # - Moving Average runs and produces: 70.00
    # - Baseline runs and produces: 70.81
    #
    # Then they are WEIGHTED and AVERAGED:
    # ensemble_forecast = (0.35*67.16) + (0.25*69.72) + (0.20*71.74) + (0.15*70.00) + (0.05*70.81)
    # ensemble_forecast = 69.33 bpm

    # ============ STEP 3: CALCULATE CONFIDENCE ============
    # Line 119-123: EXPLAINABLE AI SCORING HAPPENS HERE
    # Goes to explainable_ai.py and runs 4 confidence factors
    confidence_score = self.xai_scorer.calculate_confidence(
        measurements=measurements,
        ensemble_forecast=ensemble_forecast,
        individual_predictions=self.ensemble.predictions
    )
    #
    # What happens:
    # Factor 1 (Data Volume): Checks if we have enough data
    #   291 measurements → 95% confidence
    #
    # Factor 2 (Model Agreement): Check if all 5 methods agree
    #   All within 5% of ensemble → 85% confidence
    #
    # Factor 3 (Extrapolation): Is forecast within historical range?
    #   Forecast 69.33, Range 57-85 → Within range → 95% confidence
    #
    # Factor 4 (Stability): How chaotic is patient?
    #   CV = 0.096 (9.6% variation) → 70% confidence
    #
    # Combined: 0.25*95 + 0.25*85 + 0.20*95 + 0.30*70 = 85.0% MEDIUM

    # ============ STEP 4: PREDICTION INTERVALS ============
    # Line 126-127: Calculate 90% and 95% prediction ranges
    pi_90 = self._calculate_prediction_interval(measurements, ensemble_forecast, 0.90)
    pi_95 = self._calculate_prediction_interval(measurements, ensemble_forecast, 0.95)
    #
    # What this calculates:
    # 90% PI = [63.75, 74.90]  (90% chance actual value is here)
    # 95% PI = [62.68, 75.97]  (95% chance actual value is here)

    # ============ STEP 5: GET INDIVIDUAL PREDICTIONS ============
    # Line 130: Get breakdown of what each method predicted
    breakdown = self.ensemble.get_predictions_breakdown()
    # Returns:
    # {
    #   'arima': {'prediction': 67.16, 'weight': 0.35, 'contribution': 23.51},
    #   'exp_smooth': {'prediction': 69.72, 'weight': 0.25, 'contribution': 17.43},
    #   ...
    # }

    # Line 131: Get measurement statistics
    data = np.array(measurements, dtype=np.float64)

    # ============ STEP 6: PACKAGE RESULT ============
    # Line 134-153: CREATE RETURN OBJECT
    result = ForecastResult(
        vital_type=self.vital_type,                    # 'heart_rate'
        forecast_value=ensemble_forecast,               # 69.33
        confidence=round(confidence_score.overall, 2),  # 85.0
        confidence_level=confidence_score.level,        # 'MEDIUM'
        prediction_interval_90=pi_90,                   # (63.75, 74.90)
        prediction_interval_95=pi_95,                   # (62.68, 75.97)
        individual_predictions=self.ensemble.predictions,  # {arima: 67.16, ...}
        individual_weights=self.ensemble.weights,       # {arima: 0.35, ...}
        confidence_factors={
            'data_volume': round(confidence_score.data_volume, 2),        # 95.0
            'model_agreement': round(confidence_score.model_agreement, 2), # 85.0
            'extrapolation_distance': round(confidence_score.extrapolation_distance, 2), # 95.0
            'stability': round(confidence_score.stability, 2)  # 70.0
        },
        reasoning=confidence_score.reasoning,  # Full explanation
        n_measurements=len(measurements),      # 291
        measurement_mean=float(np.mean(data)), # 70.81
        measurement_std=float(np.std(data))    # 6.78
    )

    # Line 155: RETURN THE COMPLETE RESULT
    return result
```

### PREDICTION INTERVAL CALCULATION (Line 157-209)

```python
def _calculate_prediction_interval(self, measurements, forecast, confidence_level=0.95):
    """
    Calculate 90% and 95% prediction intervals
    These tell us: "95% confident the value will be between X and Y"
    """
    
    # Line 185-190: Get data statistics
    data = np.array(measurements, dtype=np.float64)
    mean = np.mean(data)      # 70.81
    std = np.std(data)        # 6.78 (standard deviation)
    std_error = std * 0.5     # 3.39 (conservative estimate)

    # Line 199-204: Get z-score for confidence level
    z_scores = {
        0.90: 1.645,  # For 90% confidence
        0.95: 1.96,   # For 95% confidence (most common)
        0.99: 2.576   # For 99% confidence
    }
    z_score = z_scores.get(confidence_level, 1.96)

    # Line 207-209: CALCULATE THE INTERVAL
    # Formula: PI = Forecast ± (z_score × standard_error)
    margin = z_score * std_error        # 1.96 × 3.39 = 6.65
    lower = forecast - margin           # 69.33 - 6.65 = 62.68
    upper = forecast + margin           # 69.33 + 6.65 = 75.97
    
    # Returns: (62.68, 75.97)
    # Meaning: 95% certain actual heart rate will be between 62.68 and 75.97
    
    return (lower, upper)
```

---

## FILE 2: ensemble_forecaster.py
**Location:** `backend/vitals/regression/ensemble_forecaster.py`

### ENSEMBLE CLASS (Line 47-80)

```python
class EnsembleForecaster:
    """
    Combines 5 regression methods using weighted averaging
    """

    def __init__(self, weights: Dict[str, float] = None):
        # Line 73-84: WEIGHTS FOR EACH METHOD (these are the magic numbers!)
        self.default_weights = {
            'arima': 0.35,           # 35% - ARIMA (trend detection)
            'exp_smooth': 0.25,      # 25% - Exponential Smoothing (responsiveness)
            'linear_trend': 0.20,    # 20% - Linear Trend (sustained changes)
            'moving_average': 0.15,  # 15% - Moving Average (noise reduction)
            'baseline': 0.05         # 5%  - Baseline (stability anchor)
        }
        # TOTAL: 35+25+20+15+5 = 100% ✓

        # Line 92-95: Verify weights sum to 1.0 (safety check)
        total_weight = sum(self.weights.values())
        if abs(total_weight - 1.0) > 0.001:
            raise ValueError(f"Weights must sum to 1.0, got {total_weight}")

        # Line 98-104: INITIALIZE ALL 5 FORECASTERS
        self.forecasters = {
            'arima': ARIMAForecaster(p=1, d=1, q=0),              # Import from arima_model.py
            'exp_smooth': ExponentialSmoothingForecaster(alpha=0.3),  # Import from exponential_smoothing.py
            'linear_trend': LinearTrendForecaster(),              # Import from linear_trend.py
            'moving_average': MovingAverageForecaster(window=3),  # Import from moving_average.py
            'baseline': CumulativeMovingAverageForecaster()       # Import from moving_average.py
        }
```

### FIT AND PREDICT METHOD (Line 110-142)

```python
def fit_and_predict(self, measurements: List[float]) -> float:
    """
    THIS METHOD RUNS ALL 5 REGRESSION METHODS
    """
    
    # Line 112-127: RUN EACH METHOD INDEPENDENTLY
    for method_name, forecaster in self.forecasters.items():
        try:
            # Call each method's fit_and_predict
            # For ARIMA: Line 132 calls arima_model.py ARIMAForecaster.fit_and_predict()
            # For ExpSmoothing: calls exponential_smoothing.py ExponentialSmoothingForecaster.fit_and_predict()
            # etc.
            prediction = forecaster.fit_and_predict(measurements)
            self.predictions[method_name] = prediction
            
            # RESULTS:
            # self.predictions['arima'] = 67.16
            # self.predictions['exp_smooth'] = 69.72
            # self.predictions['linear_trend'] = 71.74
            # self.predictions['moving_average'] = 70.00
            # self.predictions['baseline'] = 70.81
            
        except Exception as e:
            # Line 135-137: If method fails, use mean as fallback
            logger.warning(f"Forecaster {method_name} failed: {e}")
            self.predictions[method_name] = float(np.mean(measurements))

    # Line 140: CALCULATE WEIGHTED AVERAGE (goes to next method)
    self.ensemble_forecast = self._calculate_weighted_average()
    
    return self.ensemble_forecast
```

### WEIGHTED AVERAGE CALCULATION (Line 144-162)

```python
def _calculate_weighted_average(self) -> float:
    """
    THIS IS WHERE THE 5 PREDICTIONS ARE COMBINED
    """
    
    total = 0.0
    
    # Line 157-160: Loop through each method
    for method_name, weight in self.weights.items():
        prediction = self.predictions.get(method_name, 0.0)  # Get prediction for this method
        contribution = weight * prediction                    # Multiply by weight
        total += contribution                                 # Add to total

    # STEP BY STEP CALCULATION:
    # method='arima', weight=0.35, prediction=67.16
    #   contribution = 0.35 × 67.16 = 23.51
    #   total = 0 + 23.51 = 23.51
    #
    # method='exp_smooth', weight=0.25, prediction=69.72
    #   contribution = 0.25 × 69.72 = 17.43
    #   total = 23.51 + 17.43 = 40.94
    #
    # method='linear_trend', weight=0.20, prediction=71.74
    #   contribution = 0.20 × 71.74 = 14.35
    #   total = 40.94 + 14.35 = 55.29
    #
    # method='moving_average', weight=0.15, prediction=70.00
    #   contribution = 0.15 × 70.00 = 10.50
    #   total = 55.29 + 10.50 = 65.79
    #
    # method='baseline', weight=0.05, prediction=70.81
    #   contribution = 0.05 × 70.81 = 3.54
    #   total = 65.79 + 3.54 = 69.33

    # Line 162: Return ensemble forecast
    return float(total)  # Returns 69.33
```

---

## FILE 3: explainable_ai.py
**Location:** `backend/vitals/regression/explainable_ai.py`

### MAIN CONFIDENCE CALCULATION (Line 269-363)

```python
def calculate_confidence(self, measurements, ensemble_forecast, individual_predictions):
    """
    THIS IS THE EXPLAINABLE AI PART
    Calculates 4 confidence factors and combines them
    """
    
    # ============ FACTOR 1: DATA VOLUME ============
    # Line 293: Call method to assess data quantity
    data_volume_score, data_volume_reason = self.calculate_data_volume_score(len(measurements))
    # For 291 measurements:
    #   Goes to Line 95-126
    #   Since 291 > 40: score = 95.0
    #   reason = "Excellent: Abundant data (40+ measurements)"

    # ============ FACTOR 2: MODEL AGREEMENT ============
    # Line 294-296: Check if all methods agree
    model_agreement_score, agreement_reason = self.calculate_model_agreement_score(
        ensemble_forecast, individual_predictions
    )
    # Goes to Line 128-170
    # Calculates: How far is each prediction from ensemble average?
    # [67.16, 69.72, 71.74, 70.00, 70.81] vs ensemble 69.33
    # Deviations: [2.17, 0.39, 2.41, 0.67, 1.52]
    # Mean deviation: 1.43 / 69.33 = 2.06%
    # Since 2.06% < 5%: score = 85.0
    # reason = "Good agreement: Methods within 5%"

    # ============ FACTOR 3: EXTRAPOLATION DISTANCE ============
    # Line 297-298: Check if forecast is within historical range
    extrapolation_score, extrapolation_reason = self.calculate_extrapolation_score(
        ensemble_forecast, measurements
    )
    # Goes to Line 177-224
    # min = 57, max = 85, forecast = 69.33
    # Is 57 <= 69.33 <= 85? YES
    # score = 95.0
    # reason = "Within range: Forecast within observed range"

    # ============ FACTOR 4: STABILITY ============
    # Line 300: Check how chaotic the patient is
    stability_score, stability_reason = self.calculate_stability_score(measurements)
    # Goes to Line 226-267
    # Calculates: Coefficient of Variation = std / mean
    # cv = 6.78 / 70.81 = 0.0957 (9.57% variation)
    # Since 0.0957 < 0.12: score = 70.0
    # reason = "Acceptable stability: Moderate variation (CV = 0.096)"

    # ============ COMBINE ALL 4 FACTORS ============
    # Line 303-308: WEIGHTED AVERAGE OF CONFIDENCE FACTORS
    overall = (
        0.25 * data_volume_score +      # 0.25 × 95 = 23.75
        0.25 * model_agreement_score +  # 0.25 × 85 = 21.25
        0.20 * extrapolation_score +    # 0.20 × 95 = 19.00
        0.30 * stability_score          # 0.30 × 70 = 21.00
    )
    # overall = 23.75 + 21.25 + 19.00 + 21.00 = 85.0%

    # ============ DETERMINE CONFIDENCE LEVEL ============
    # Line 311-316: Classify as HIGH, MEDIUM, or LOW
    if overall >= 90:
        level = 'HIGH'      # Can trigger alerts automatically
    elif overall >= 70:
        level = 'MEDIUM'    # Requires manual review
    else:
        level = 'LOW'       # Information only

    # For our case: overall=85, so level = 'MEDIUM'

    # ============ CREATE DETAILED REASONING ============
    # Line 319-350: Format explanation for clinicians
    reasoning = f"""
CONFIDENCE BREAKDOWN (Overall: {overall:.1f}%):

1. DATA VOLUME (25% weight = {0.25*data_volume_score:.1f}):
   {data_volume_reason}

2. MODEL AGREEMENT (25% weight = {0.25*model_agreement_score:.1f}):
   {agreement_reason}

3. EXTRAPOLATION DISTANCE (20% weight = {0.20*extrapolation_score:.1f}):
   {extrapolation_reason}

4. STABILITY (30% weight = {0.30*stability_score:.1f}):
   {stability_reason}

CLINICAL RECOMMENDATION:
- HIGH (90%+) - Use as alert trigger
- MEDIUM (70-89%) - Manual review recommended
- LOW (<70%) - Information only
"""

    # Line 352-360: RETURN CONFIDENCE SCORE OBJECT
    confidence_score = ConfidenceScore(
        overall=overall,                    # 85.0
        data_volume=data_volume_score,      # 95.0
        model_agreement=model_agreement_score,  # 85.0
        extrapolation_distance=extrapolation_score,  # 95.0
        stability=stability_score,          # 70.0
        level=level,                        # 'MEDIUM'
        reasoning=reasoning.strip()         # Full text explanation
    )

    return confidence_score
```

---

## FILE 4: exponential_smoothing.py
**Location:** `backend/vitals/regression/exponential_smoothing.py`

### EXPONENTIAL SMOOTHING METHOD (Line 54-92)

```python
def fit_and_predict(self, measurements: List[float]) -> float:
    """
    REGRESSION METHOD 1: EXPONENTIAL SMOOTHING
    Recent measurements weighted more than old ones
    """
    
    # Line 71: Convert to numpy array for math operations
    data = np.array(measurements, dtype=np.float64)

    # Line 77: Initialize with first measurement
    smoothed_value = data[0]  # Start with 72
    self.smoothed_series = [smoothed_value]

    # Line 84-87: APPLY EXPONENTIAL SMOOTHING FORMULA
    for t in range(1, len(data)):
        # FORMULA: S_t = α × X_t + (1 - α) × S_{t-1}
        # α = 0.3 (alpha)
        # X_t = current measurement
        # S_{t-1} = previous smoothed value
        
        smoothed_value = (self.alpha * data[t]) + ((1 - self.alpha) * smoothed_value)
        self.smoothed_series.append(smoothed_value)

    # STEP BY STEP FOR [72, 74, 75, 73, 76]:
    # t=1, X_t=74: S_1 = 0.3×74 + 0.7×72 = 22.2 + 50.4 = 72.6
    # t=2, X_t=75: S_2 = 0.3×75 + 0.7×72.6 = 22.5 + 50.82 = 73.32
    # t=3, X_t=73: S_3 = 0.3×73 + 0.7×73.32 = 21.9 + 51.32 = 73.22
    # t=4, X_t=76: S_4 = 0.3×76 + 0.7×73.22 = 22.8 + 51.25 = 74.05

    # Line 90: Forecast is the last smoothed value
    self.forecast = float(smoothed_value)  # 74.05
    
    return self.forecast
```

---

## FILE 5: arima_model.py
**Location:** `backend/vitals/regression/arima_model.py`

### ARIMA METHOD (Line 110-142)

```python
def fit_and_predict(self, measurements: List[float]) -> float:
    """
    REGRESSION METHOD 2: ARIMA
    Detects patterns in HOW VALUES CHANGE (not just values themselves)
    """
    
    # Line 134: Convert to array
    data = np.array(measurements, dtype=np.float64)

    # ============ STEP 1: DIFFERENCING ============
    # Line 142: Remove trend by calculating differences
    diff = np.diff(data)  # Subtracts each value from the next
    
    # For [72, 74, 75, 73, 76]:
    # diff = [74-72, 75-74, 73-75, 76-73] = [2, 1, -2, 3]
    # This shows: increased 2, then 1, then decreased 2, then increased 3

    # ============ STEP 2: CALCULATE AR COEFFICIENT ============
    # Line 147-152: Find correlation between changes
    # ar_coeff = correlation(diff[:-1], diff[1:])
    # This answers: "If last change was +2, what's next change likely to be?"
    
    if len(diff) > 1:
        ar_coeff = np.corrcoef(diff[:-1], diff[1:])[0, 1]
        # For our example: ar_coeff ≈ 0.15 (weak momentum)
    else:
        ar_coeff = 0

    # ============ STEP 3: FORECAST NEXT DIFFERENCE ============
    # Line 158: Use AR coefficient to predict next change
    last_diff = diff[-1]           # Last change = 3
    forecast_diff = ar_coeff * last_diff  # 0.15 × 3 = 0.45

    # ============ STEP 4: REVERSE DIFFERENCING ============
    # Line 163: Convert back to original scale
    last_original_value = data[-1]  # 76
    forecast = last_original_value + forecast_diff  # 76 + 0.45 = 76.45
    
    self.forecast = float(forecast)
    return self.forecast
```

---

## FILE 6: linear_trend.py
**Location:** `backend/vitals/regression/linear_trend.py`

### LINEAR TREND METHOD (Line 64-91)

```python
def fit_and_predict(self, measurements: List[float]) -> float:
    """
    REGRESSION METHOD 3: LINEAR TREND
    Fits straight line y = mx + b through data
    """
    
    # Line 66-67: Create time index
    x = np.arange(len(measurements))  # [0, 1, 2, 3, 4, ...]
    y = np.array(measurements)         # [72, 74, 75, 73, 76, ...]

    # Line 71-72: Calculate means
    mean_x = np.mean(x)
    mean_y = np.mean(y)

    # ============ CALCULATE SLOPE ============
    # Line 75-77: LEAST SQUARES FORMULA
    # m = Σ((x_i - mean_x)(y_i - mean_y)) / Σ((x_i - mean_x)²)
    
    numerator = np.sum((x - mean_x) * (y - mean_y))
    denominator = np.sum((x - mean_x) ** 2)
    m = numerator / denominator  # This is the slope (rate of change)

    # For example:
    # If m = 0.3, it means heart rate increases 0.3 bpm per measurement

    # ============ CALCULATE INTERCEPT ============
    # Line 79: b = mean_y - m × mean_x
    b = mean_y - (m * mean_x)  # This is where line crosses y-axis at x=0

    # ============ FORECAST NEXT VALUE ============
    # Line 83-84: y = mx + b for next time point
    next_x = len(measurements)  # Time of next measurement
    forecast = m * next_x + b   # Calculate y value on the line
    
    self.forecast = float(forecast)
    return self.forecast
```

---

## FILE 7: moving_average.py
**Location:** `backend/vitals/regression/moving_average.py`

### MOVING AVERAGE METHOD (Line 58-65)

```python
def _calculate_simple_ma(self, measurements):
    """
    REGRESSION METHOD 4: MOVING AVERAGE
    Average the last N measurements
    """
    
    # Line 59: Use last 'window' measurements (default window=3)
    recent_measurements = measurements[-self.window:]
    
    # For [72, 74, 75, 73, 76], window=3:
    # recent_measurements = [73, 76, 75] (last 3)

    # Line 62: Calculate mean
    ma = np.mean(recent_measurements)
    # ma = (73 + 76 + 75) / 3 = 74.67
    
    return float(ma)
```

### BASELINE METHOD (Line 223-230)

```python
class CumulativeMovingAverageForecaster:
    """
    REGRESSION METHOD 5: BASELINE
    All-time average
    """
    
    def fit_and_predict(self, measurements):
        # SIMPLEST METHOD: Average ALL measurements
        forecast = float(np.mean(measurements))
        # For [72, 74, 75, 73, 76]: forecast = 74.0
        return forecast
```

---

## HOW TO NAVIGATE IN VS CODE

```
Open your VS Code project:

📁 backend/vitals/regression/
   ├── 📄 vital_forecaster.py      ← MAIN ENTRY POINT (start here)
   │   └── Lines 96-155: forecast() method (ALL 7 STEPS HAPPEN HERE)
   │
   ├── 📄 ensemble_forecaster.py   ← COMBINES 5 METHODS
   │   ├── Lines 98-104: Initialize 5 forecasters
   │   ├── Lines 110-142: fit_and_predict() (runs all 5)
   │   └── Lines 144-162: _calculate_weighted_average()
   │
   ├── 📄 explainable_ai.py        ← CONFIDENCE SCORING
   │   ├── Lines 95-126: calculate_data_volume_score()
   │   ├── Lines 128-170: calculate_model_agreement_score()
   │   ├── Lines 177-224: calculate_extrapolation_score()
   │   ├── Lines 226-267: calculate_stability_score()
   │   └── Lines 269-363: calculate_confidence() (COMBINES 4 FACTORS)
   │
   ├── 📄 exponential_smoothing.py ← METHOD 1
   │   └── Lines 54-92: fit_and_predict()
   │
   ├── 📄 arima_model.py           ← METHOD 2
   │   └── Lines 110-142: fit_and_predict()
   │
   ├── 📄 linear_trend.py          ← METHOD 3
   │   └── Lines 46-91: fit_and_predict()
   │
   └── 📄 moving_average.py        ← METHODS 4 & 5
       ├── Lines 58-65: _calculate_simple_ma()
       └── Lines 225-230: CumulativeMovingAverageForecaster
```

---

## QUICK REFERENCE: WHAT EACH LINE DOES

```
vital_forecaster.py:
  Line 93: Create ensemble (calls ensemble_forecaster.py)
  Line 94: Create XAI scorer (calls explainable_ai.py)
  Line 116: Run all 5 methods → returns 69.33 bpm
  Line 119: Calculate confidence → returns 85.0%
  Line 126: Calculate 90% PI → returns [63.75, 74.90]
  Line 127: Calculate 95% PI → returns [62.68, 75.97]
  Line 134-153: Package result → returns ForecastResult

ensemble_forecaster.py:
  Line 130-137: Loop through 5 methods, collect predictions
  Line 140: Weighted average calculation
  Line 162: Return 69.33 bpm

explainable_ai.py:
  Line 293: Data Volume Score (95.0 for 291 measurements)
  Line 294: Model Agreement Score (85.0 methods agree)
  Line 297: Extrapolation Score (95.0 within range)
  Line 300: Stability Score (70.0 some variation)
  Line 303-308: Combine 4 factors → 85.0% overall
  Line 311-316: Classify as MEDIUM confidence

exponential_smoothing.py:
  Line 84-87: Loop through each measurement
  Line 86: S_t = 0.3 × X_t + 0.7 × S_{t-1} (the formula)
  Line 90: Return smoothed value

arima_model.py:
  Line 142: Calculate differences between measurements
  Line 147: Find AR coefficient (correlation)
  Line 158: Forecast next difference
  Line 163: Add difference to last measurement

linear_trend.py:
  Line 75-77: Calculate slope (m)
  Line 79: Calculate intercept (b)
  Line 83-84: Calculate y = mx + b for next point

moving_average.py:
  Line 62: Mean of last 3 measurements
  Line 225: Mean of ALL measurements (baseline)
```

