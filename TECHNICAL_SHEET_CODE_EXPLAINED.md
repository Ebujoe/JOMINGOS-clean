# Technical Sheet: Regression Analysis & Explainable AI Code Explained
## Step-by-Step Code Walkthrough for Non-Programmers

**Purpose:** This document shows you the actual CODE and explains what each part does in simple language.

---

## TABLE OF CONTENTS

1. **How Data Flows Through the System**
2. **The Regression Methods (5 Different Approaches)**
3. **The Ensemble Combination System**
4. **Confidence Scoring System**
5. **Prediction Intervals**
6. **Complete Example: One Patient's Forecast**
7. **Real Code Snippets Explained**

---

## SECTION 1: HOW DATA FLOWS THROUGH THE SYSTEM

### The Big Picture Flow

```
Patient Vital Signs Data (Raw)
    ↓
    └─→ [STEP 1] Data Validation
        ├─ Is the data valid?
        ├─ Remove outliers
        └─ Clean the data
            ↓
    ├─→ [STEP 2] Train 5 Regression Models
    │   ├─ Model 1: Exponential Smoothing
    │   ├─ Model 2: ARIMA
    │   ├─ Model 3: Linear Trend
    │   ├─ Model 4: Moving Average
    │   └─ Model 5: Baseline
    │       ↓
    ├─→ [STEP 3] Each Model Makes a Prediction
    │   ├─ Model 1 predicts: 79 bpm
    │   ├─ Model 2 predicts: 80 bpm
    │   ├─ Model 3 predicts: 79 bpm
    │   ├─ Model 4 predicts: 75 bpm
    │   └─ Model 5 predicts: 73 bpm
    │       ↓
    ├─→ [STEP 4] Ensemble Combines with Weights
    │   └─ Final Prediction: 78 bpm (weighted average)
    │       ↓
    ├─→ [STEP 5] Calculate Confidence Score
    │   ├─ Data Volume: 95%
    │   ├─ Model Agreement: 92%
    │   ├─ Extrapolation: 95%
    │   └─ Stability: 90%
    │   └─ FINAL CONFIDENCE: 87%
    │       ↓
    └─→ [STEP 6] Output Result
        ├─ Prediction: 78 bpm
        ├─ Confidence: 87%
        ├─ 95% PI: 74-82 bpm
        └─ Alert if needed
```

---

## SECTION 2: THE REGRESSION METHODS (WITH CODE)

### Method 1: Exponential Smoothing (35% Weight)

**What It Does:** Gives more weight to recent measurements.

**Simple Code Example:**

```python
def exponential_smoothing(heart_rates, alpha=0.3):
    """
    alpha = how much to weight recent values
    alpha=0.3 means: 30% recent, 70% history
    """
    
    # Example heart rates: [72, 74, 71, 73, 75, 77]
    # Most recent: 77 bpm (this gets highest weight)
    
    if not heart_rates:
        return None
    
    # Start with the first value
    smoothed = heart_rates[0]
    
    # For each new measurement
    for rate in heart_rates[1:]:
        # New smoothed value = (alpha × new) + (1-alpha × old)
        # = (0.3 × 77) + (0.7 × 75)
        # = 23.1 + 52.5
        # = 75.6
        smoothed = (alpha * rate) + ((1 - alpha) * smoothed)
    
    return smoothed
```

**What's Happening:**
- Takes the most recent heart rate (77 bpm)
- Multiplies it by 0.3 (30% weight)
- Adds it to old smoothed value multiplied by 0.7 (70% weight)
- Result: Recent measurements have MORE influence

**Real Example:**
```
Patient: James Brown
Recent measurements: [72, 73, 75, 77, 79]

Exponential Smoothing calculation:
Step 1: Start with 72
Step 2: (0.3 × 73) + (0.7 × 72) = 21.9 + 50.4 = 72.3
Step 3: (0.3 × 75) + (0.7 × 72.3) = 22.5 + 50.6 = 73.1
Step 4: (0.3 × 77) + (0.7 × 73.1) = 23.1 + 51.2 = 74.3
Step 5: (0.3 × 79) + (0.7 × 74.3) = 23.7 + 52.0 = 75.7

Final Smoothed Value: 75.7 bpm
This is used as the prediction (or basis for prediction)
```

---

### Method 2: ARIMA (25% Weight)

**What It Does:** Analyzes the PATTERN OF CHANGES, not the values themselves.

**Simple Code Example:**

```python
def simplified_arima(heart_rates):
    """
    ARIMA = AutoRegressive Integrated Moving Average
    
    Step 1: Calculate the DIFFERENCES (changes between measurements)
    Step 2: Analyze the pattern in differences
    Step 3: Predict the next difference
    Step 4: Add difference to last value
    """
    
    # Example data: [72, 74, 71, 73, 75]
    heart_rates = [72, 74, 71, 73, 75]
    
    # STEP 1: Calculate differences (changes)
    differences = []
    for i in range(1, len(heart_rates)):
        diff = heart_rates[i] - heart_rates[i-1]
        differences.append(diff)
    
    # differences = [2, -3, 2, 2]
    # This means:
    # 72→74 = +2 (went up 2)
    # 74→71 = -3 (went down 3)
    # 71→73 = +2 (went up 2)
    # 73→75 = +2 (went up 2)
    
    # STEP 2: Analyze the pattern
    # Recent differences: [2, 2]
    # Pattern: "Trending up by 2 per measurement"
    
    average_diff = sum(differences) / len(differences)
    # average_diff = (2 + -3 + 2 + 2) / 4 = 3/4 = 0.75
    
    # But we care more about RECENT differences
    # Last 2 differences: [2, 2]
    # Recent average: (2 + 2) / 2 = 2
    
    recent_avg_diff = sum(differences[-2:]) / 2
    
    # STEP 3: Predict next value
    # Last value: 75
    # Expected change: +2 (based on recent trend)
    next_prediction = heart_rates[-1] + recent_avg_diff
    # = 75 + 2
    # = 77
    
    return next_prediction  # Returns 77 bpm
```

**What's Happening:**
1. Looks at HOW MUCH each measurement changed from the last
2. Finds the average change
3. Assumes the same change will happen next
4. Adds that change to the current value

**Real Example:**
```
Patient: Michael Brown
Measurements: [68, 69, 71, 72, 73, 74, 75, 76, 77, 78]

Changes (differences): [+1, +2, +1, +1, +1, +1, +1, +1, +1]
Pattern: "Going up by about 1 per hour"

Prediction: 78 + 1 = 79 bpm
Reasoning: "The trend will continue"
```

---

### Method 3: Linear Trend (20% Weight)

**What It Does:** Draws a straight line through the data and continues it.

**Simple Code Example:**

```python
def linear_trend(times, heart_rates):
    """
    Fits a straight line to the data
    Formula: y = m*x + b
    where:
        m = slope (how much it goes up/down per unit time)
        b = intercept (starting point)
    """
    
    # Example:
    times = [0, 1, 2, 3, 4, 5, 6, 7, 8]  # Hours
    heart_rates = [68, 69, 71, 72, 73, 74, 75, 76, 77]
    
    # STEP 1: Calculate slope (m)
    # Slope = change in heart_rate / change in time
    # = (77 - 68) / (8 - 0)
    # = 9 / 8
    # = 1.125 (goes up 1.125 bpm per hour)
    
    n = len(times)
    sum_xy = sum(t * r for t, r in zip(times, heart_rates))
    sum_x = sum(times)
    sum_y = sum(heart_rates)
    sum_x2 = sum(t**2 for t in times)
    
    # Slope formula (simplified)
    slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x**2)
    # slope ≈ 1.125
    
    # STEP 2: Calculate intercept (b)
    # intercept = average_y - slope * average_x
    avg_y = sum_y / n
    avg_x = sum_x / n
    intercept = avg_y - slope * avg_x
    # intercept ≈ 68
    
    # STEP 3: Make prediction at next time
    next_time = 9
    prediction = slope * next_time + intercept
    # = 1.125 * 9 + 68
    # = 10.125 + 68
    # = 78.125 ≈ 78 bpm
    
    return prediction
```

**What's Happening:**
1. Calculates the SLOPE (how fast it's changing)
2. Calculates the INTERCEPT (where it started)
3. Creates a formula: "Heart rate = 1.125 × hours + 68"
4. Uses formula to predict future values

**Real Example:**
```
Plotting heart rate over time:

HR
  78 |       *
     |      *
  76 |     *
     |    *
  74 |   *
     |  *
  72 | *
     |_______
     Time

This line goes up by 1 bpm per hour.
At hour 9: HR = 78 bpm
```

---

### Method 4: Moving Average (15% Weight)

**What It Does:** Averages recent measurements to smooth noise.

**Simple Code Example:**

```python
def moving_average(heart_rates, window_size=3):
    """
    window_size = how many recent measurements to average
    window_size=3 means average the last 3 values
    """
    
    # Example: [70, 68, 72, 69, 71, 73, 70, 72]
    heart_rates = [70, 68, 72, 69, 71, 73, 70, 72]
    
    moving_averages = []
    
    # For each position, average the window
    for i in range(window_size - 1, len(heart_rates)):
        # Get the window of last 3 values
        window = heart_rates[i - window_size + 1:i + 1]
        # Calculate average
        avg = sum(window) / len(window)
        moving_averages.append(avg)
    
    # Process:
    # i=2: window=[70, 68, 72], avg=(70+68+72)/3=70
    # i=3: window=[68, 72, 69], avg=(68+72+69)/3=69.7
    # i=4: window=[72, 69, 71], avg=(72+69+71)/3=70.7
    # i=5: window=[69, 71, 73], avg=(69+71+73)/3=71
    # i=6: window=[71, 73, 70], avg=(71+73+70)/3=71.3
    # i=7: window=[73, 70, 72], avg=(73+70+72)/3=71.7
    
    # moving_averages = [70, 69.7, 70.7, 71, 71.3, 71.7]
    
    # Use the most recent moving average as prediction
    return moving_averages[-1]  # Returns 71.7 bpm
```

**What's Happening:**
1. Takes last 3 measurements
2. Averages them
3. Repeats for each position
4. Creates a smooth line

**Real Example:**
```
Raw measurements: [70, 68, 72, 69, 71, 73, 70, 72]
                   70  68  72  69  71  73  70  72  <- Noisy

3-point Moving Average: [70, 69.7, 70.7, 71, 71.3, 71.7]
                         70  70    71   71   71   72  <- Smooth

Why? Removes random spikes and dips
```

---

### Method 5: Baseline (5% Weight)

**What It Does:** Uses the historical average.

**Simple Code Example:**

```python
def baseline_prediction(heart_rates):
    """
    Simplest possible prediction: just average all measurements
    """
    
    # Example: [70, 72, 71, 73, 72, 74, 71, 72]
    heart_rates = [70, 72, 71, 73, 72, 74, 71, 72]
    
    # STEP 1: Add all values
    total = sum(heart_rates)
    # total = 70 + 72 + 71 + 73 + 72 + 74 + 71 + 72 = 575
    
    # STEP 2: Divide by count
    avg = total / len(heart_rates)
    # avg = 575 / 8 = 71.875 ≈ 72 bpm
    
    # STEP 3: That's our prediction
    return avg  # Returns 72 bpm
```

**What's Happening:**
1. Simply averages ALL measurements
2. Predicts patient will stay at their average
3. Very stable, never changes much

**Why Include It?**
- Catches when nothing unusual is happening
- Acts as a "default" when other methods disagree
- Provides stability to ensemble

---

## SECTION 3: THE ENSEMBLE SYSTEM (How They Combine)

### Combining All 5 Methods

**The Code:**

```python
def ensemble_forecast(heart_rates, weights=None):
    """
    Combine all 5 methods with weighted average
    """
    
    if weights is None:
        # Default weights based on reliability
        weights = {
            'exp_smoothing': 0.35,    # 35%
            'arima': 0.25,            # 25%
            'linear_trend': 0.20,     # 20%
            'moving_average': 0.15,   # 15%
            'baseline': 0.05          # 5%
        }
    
    # STEP 1: Get prediction from each method
    pred1 = exponential_smoothing(heart_rates)  # 79.5
    pred2 = simplified_arima(heart_rates)       # 80.2
    pred3 = linear_trend(times, heart_rates)    # 79.1
    pred4 = moving_average(heart_rates)         # 74.0
    pred5 = baseline_prediction(heart_rates)    # 72.8
    
    print("Individual Predictions:")
    print(f"  Exp Smoothing: {pred1:.1f} bpm")
    print(f"  ARIMA: {pred2:.1f} bpm")
    print(f"  Linear Trend: {pred3:.1f} bpm")
    print(f"  Moving Avg: {pred4:.1f} bpm")
    print(f"  Baseline: {pred5:.1f} bpm")
    
    # STEP 2: Combine with weights
    ensemble = (
        weights['exp_smoothing'] * pred1 +
        weights['arima'] * pred2 +
        weights['linear_trend'] * pred3 +
        weights['moving_average'] * pred4 +
        weights['baseline'] * pred5
    )
    
    # Calculation:
    # = (0.35 × 79.5) + (0.25 × 80.2) + (0.20 × 79.1) + (0.15 × 74.0) + (0.05 × 72.8)
    # = 27.825 + 20.05 + 15.82 + 11.1 + 3.64
    # = 78.435 ≈ 78 bpm
    
    return ensemble
```

**What's Happening:**
1. Each method gives its prediction
2. Multiply each by its weight (importance)
3. Add them all together
4. Get final ensemble prediction

**Why This Works:**
```
Like asking 5 doctors:
Doctor 1 (newest trends expert): "79.5 bpm" - weight 35%
Doctor 2 (pattern expert): "80.2 bpm" - weight 25%
Doctor 3 (steady trend expert): "79.1 bpm" - weight 20%
Doctor 4 (noise reducer): "74.0 bpm" - weight 15%
Doctor 5 (baseline expert): "72.8 bpm" - weight 5%

Weighted vote: 78 bpm (trusts first 3 doctors more)
```

---

## SECTION 4: CONFIDENCE SCORING (The XAI Part)

### Factor 1: Data Volume Score

**The Code:**

```python
def calculate_data_volume_score(vital_measurements):
    """
    More data = more confident
    10 measurements = 60% confident
    30 measurements = 95% confident
    """
    
    data_count = len(vital_measurements)
    
    # RULE: confidence increases with data
    if data_count < 10:
        score = 40  # Not enough data
    elif data_count < 20:
        score = 60  # Minimal data
    elif data_count < 30:
        score = 80  # Good data
    else:
        score = 95  # Lots of data
    
    return score
```

**Example:**
```
Richard Anderson: 291 measurements
→ Data Volume Score: 95% (lots of data, very confident)

James Wilson: 45 measurements
→ Data Volume Score: 75% (decent data, moderately confident)

Demo Patient: 18 measurements
→ Data Volume Score: 60% (minimal data, less confident)
```

---

### Factor 2: Model Agreement Score

**The Code:**

```python
def calculate_model_agreement_score(predictions):
    """
    If all 5 models predict the same, we're confident
    If they disagree, we're less confident
    
    predictions = [79, 80, 79, 75, 73]  (from 5 methods)
    """
    
    # STEP 1: Calculate the spread (how much they differ)
    max_pred = max(predictions)  # 80
    min_pred = min(predictions)  # 73
    spread = max_pred - min_pred  # 80 - 73 = 7
    
    # STEP 2: Calculate standard deviation (how spread out they are)
    average = sum(predictions) / len(predictions)
    # average = (79+80+79+75+73)/5 = 386/5 = 77.2
    
    # Variance = average of squared differences from mean
    variance = sum((p - average)**2 for p in predictions) / len(predictions)
    # variance = sum of squared differences / 5
    
    # Standard deviation = square root of variance
    import math
    std_dev = math.sqrt(variance)
    
    # STEP 3: Convert to confidence score
    # Small std_dev = high confidence
    # Large std_dev = low confidence
    if std_dev <= 1:
        agreement_score = 95  # Very close agreement
    elif std_dev <= 2:
        agreement_score = 85  # Close agreement
    elif std_dev <= 3:
        agreement_score = 75  # Some spread
    else:
        agreement_score = 50  # Large disagreement
    
    return agreement_score
```

**Example:**
```
Scenario 1: Models agree perfectly
Predictions: [78, 78, 79, 77, 78]
Spread: 79-77=2, Std Dev: 0.7
→ Agreement Score: 95% (Models agree!)

Scenario 2: Models disagree
Predictions: [70, 75, 80, 72, 85]
Spread: 85-70=15, Std Dev: 6.5
→ Agreement Score: 30% (Models disagree!)
```

---

### Factor 3: Extrapolation Distance

**The Code:**

```python
def calculate_extrapolation_score(prediction, historical_min, historical_max):
    """
    Is the prediction within the range of historical data?
    If yes = confident
    If outside = less confident (extrapolating)
    """
    
    # Example:
    # Historical range: 68-79 bpm
    # Prediction: 78 bpm (within range)
    historical_min = 68
    historical_max = 79
    prediction = 78
    
    # STEP 1: Check if prediction is within range
    if historical_min <= prediction <= historical_max:
        # Within historical range = safe
        score = 95
    else:
        # Outside range = risky
        distance_outside = 0
        
        if prediction < historical_min:
            distance_outside = historical_min - prediction
        else:
            distance_outside = prediction - historical_max
        
        # Score decreases based on how far outside
        score = 95 - (distance_outside * 10)
        score = max(score, 20)  # Don't go below 20
    
    return score
```

**Example:**
```
Patient: Michael Brown
Historical HR range: 68-80 bpm

Prediction: 78 bpm
→ Within range
→ Extrapolation Score: 95% (confident)

Prediction: 85 bpm
→ Outside range by 5 bpm
→ Extrapolation Score: 45% (less confident)

Prediction: 95 bpm
→ Outside range by 15 bpm
→ Extrapolation Score: 20% (very uncertain)
```

---

### Factor 4: Stability Score

**The Code:**

```python
def calculate_stability_score(heart_rates):
    """
    Stable patterns are predictable
    Chaotic patterns are unpredictable
    """
    
    # Example stable patient: [72, 72, 71, 72, 71, 72, 73, 72]
    heart_rates = [72, 72, 71, 72, 71, 72, 73, 72]
    
    # STEP 1: Calculate average
    avg = sum(heart_rates) / len(heart_rates)
    # avg = 72
    
    # STEP 2: Calculate how much each value differs from average
    differences_from_avg = [abs(hr - avg) for hr in heart_rates]
    # differences = [0, 0, 1, 0, 1, 0, 1, 0]
    
    # STEP 3: Calculate average difference (variability)
    avg_difference = sum(differences_from_avg) / len(differences_from_avg)
    # avg_difference = 3/8 = 0.375
    
    # STEP 4: Convert to stability score
    # Small variability = stable = high confidence
    # Large variability = chaotic = low confidence
    
    if avg_difference <= 1:
        stability = 95  # Very stable
    elif avg_difference <= 2:
        stability = 80  # Moderately stable
    elif avg_difference <= 3:
        stability = 65  # Some variability
    else:
        stability = 40  # Very chaotic
    
    return stability
```

**Example:**
```
Patient A: [72, 72, 71, 72, 71, 72, 73, 72]
Avg difference from mean: 0.375
→ Stability Score: 95% (very stable)

Patient B: [70, 72, 75, 68, 79, 71, 77, 73]
Avg difference from mean: 3.5
→ Stability Score: 35% (very chaotic)
```

---

### Combining All 4 Factors into Final Confidence

**The Code:**

```python
def calculate_final_confidence(
    data_volume_score,
    model_agreement_score,
    extrapolation_score,
    stability_score
):
    """
    Combine all 4 factors with weights
    """
    
    # STEP 1: Assign weights to each factor
    weights = {
        'data_volume': 0.25,      # 25% importance
        'agreement': 0.25,        # 25% importance
        'extrapolation': 0.20,    # 20% importance
        'stability': 0.30         # 30% importance
    }
    
    # STEP 2: Weighted average
    confidence = (
        weights['data_volume'] * data_volume_score +
        weights['agreement'] * model_agreement_score +
        weights['extrapolation'] * extrapolation_score +
        weights['stability'] * stability_score
    )
    
    # Example calculation:
    # data_volume_score = 95
    # model_agreement_score = 92
    # extrapolation_score = 95
    # stability_score = 90
    
    # confidence = (0.25×95) + (0.25×92) + (0.20×95) + (0.30×90)
    #            = 23.75 + 23 + 19 + 27
    #            = 92.75 ≈ 93%
    
    return round(confidence)
```

**Real Example:**

```
Richard Anderson's Heart Rate Prediction

Step 1: Gather scores
  Data Volume Score:    95% (291 measurements)
  Model Agreement:      92% (predictions: 77,78,77,76,78)
  Extrapolation:        95% (78 is within his range 70-80)
  Stability:            90% (heart rate typically 70-80)

Step 2: Calculate final confidence
  = (0.25 × 95) + (0.25 × 92) + (0.20 × 95) + (0.30 × 90)
  = 93%

RESULT: 93% CONFIDENCE
"We are 93% confident Richard's heart rate will be 78 bpm"
```

---

## SECTION 5: PREDICTION INTERVALS (Ranges, Not Just Points)

### How Prediction Intervals Are Calculated

**The Code:**

```python
def calculate_prediction_interval_95(predictions, actual_values):
    """
    95% PI means: 95% confident the value will be in this range
    
    We calculate this using the errors from past predictions
    """
    
    # Step 1: Calculate past prediction errors
    errors = [abs(pred - actual) for pred, actual in zip(predictions, actual_values)]
    # errors = [1, 1, 2, 2, 1]  (how wrong past predictions were)
    
    # Step 2: Calculate standard deviation of errors
    import math
    avg_error = sum(errors) / len(errors)
    # avg_error = 7/5 = 1.4
    
    variance = sum((e - avg_error)**2 for e in errors) / len(errors)
    std_dev_error = math.sqrt(variance)
    # std_dev_error ≈ 0.57
    
    # Step 3: For 95% confidence, multiply by 1.96
    # (This is a statistical constant)
    margin_of_error_95 = 1.96 * std_dev_error
    # margin_of_error_95 ≈ 1.12
    
    # Step 4: Apply to current prediction
    current_prediction = 78  # Our ensemble prediction
    
    pi_95_lower = current_prediction - margin_of_error_95
    pi_95_upper = current_prediction + margin_of_error_95
    # pi_95_lower ≈ 76.88 ≈ 77
    # pi_95_upper ≈ 79.12 ≈ 79
    
    # But we also account for the ensemble predictions spread
    ensemble_std_dev = std_dev_errors_from_ensemble(predictions)
    
    # Final 95% PI:
    pi_95_lower = current_prediction - 2 * ensemble_std_dev  # Conservative
    pi_95_upper = current_prediction + 2 * ensemble_std_dev
    
    return (pi_95_lower, pi_95_upper)
```

**Example:**

```
Michael Brown's Heart Rate

Ensemble Prediction: 78 bpm

Historical errors from our predictions: ±2 bpm

95% Prediction Interval:
Lower: 78 - (1.96 × 2) = 78 - 3.92 ≈ 74 bpm
Upper: 78 + (1.96 × 2) = 78 + 3.92 ≈ 82 bpm

Result: 95% PI = [74, 82] bpm

Meaning: "We're 95% confident the actual value will be between 74-82 bpm"
```

---

## SECTION 6: COMPLETE EXAMPLE (One Patient's Forecast)

### Full Walk-Through: Richard Anderson's Heart Rate Prediction

**Step 1: Get Patient Data**

```python
patient = Patient.objects.get(first_name='Richard', last_name='Anderson')
vital_history = VitalSigns.objects.filter(
    patient=patient,
    vital_type='heart_rate'
).order_by('-recorded_at')[:30]  # Last 30 measurements

# Data: [68, 69, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, ...]
```

**Step 2: Train All 5 Models**

```python
# Each model learns from the historical data

exp_smooth_model = train_exponential_smoothing(vital_history)
arima_model = train_arima(vital_history)
trend_model = train_linear_trend(vital_history)
ma_model = train_moving_average(vital_history)
baseline_model = train_baseline(vital_history)

print("Models trained successfully")
```

**Step 3: Make Predictions**

```python
# Each model predicts independently
pred1 = exp_smooth_model.predict()  # 79.5 bpm
pred2 = arima_model.predict()       # 80.2 bpm
pred3 = trend_model.predict()       # 79.1 bpm
pred4 = ma_model.predict()          # 74.0 bpm
pred5 = baseline_model.predict()    # 72.8 bpm

print(f"Exp Smoothing: {pred1}")
print(f"ARIMA: {pred2}")
print(f"Linear Trend: {pred3}")
print(f"Moving Average: {pred4}")
print(f"Baseline: {pred5}")
```

**Step 4: Combine with Ensemble**

```python
# Weighted average
ensemble_pred = (0.35 * pred1 +
                 0.25 * pred2 +
                 0.20 * pred3 +
                 0.15 * pred4 +
                 0.05 * pred5)

# ensemble_pred = 78.4 ≈ 78 bpm
print(f"Ensemble Prediction: {ensemble_pred:.1f} bpm")
```

**Step 5: Calculate Confidence Scores**

```python
# Factor 1: Data volume
data_score = 95  # 291 measurements = lots of data

# Factor 2: Model agreement
agreement_score = 92  # predictions: [79.5, 80.2, 79.1, 74, 72.8]
                      # Pretty close agreement

# Factor 3: Extrapolation
extrapolation_score = 95  # 78 is within his normal range (70-80)

# Factor 4: Stability
stability_score = 90  # His HR is pretty stable (±2 bpm)

# Final confidence
final_confidence = (0.25 * 95 +
                    0.25 * 92 +
                    0.20 * 95 +
                    0.30 * 90)
# = 93%

print(f"Confidence Score: {final_confidence:.0f}%")
```

**Step 6: Calculate Prediction Intervals**

```python
# Based on past errors
std_error = 2  # Our predictions are usually off by ±2 bpm

# 95% PI (wider range, more confident)
pi_95_lower = 78 - (1.96 * 2)  # 74 bpm
pi_95_upper = 78 + (1.96 * 2)  # 82 bpm

# 90% PI (narrower range, less confident)
pi_90_lower = 78 - (1.645 * 2)  # 75 bpm
pi_90_upper = 78 + (1.645 * 2)  # 81 bpm

print(f"90% PI: {pi_90_lower:.0f}-{pi_90_upper:.0f} bpm")
print(f"95% PI: {pi_95_lower:.0f}-{pi_95_upper:.0f} bpm")
```

**Step 7: Create Forecast Record**

```python
# Store all this in the database

forecast = PatientForecast.objects.create(
    patient=patient,
    vital_name='heart_rate',
    
    # The prediction
    forecast_value=78,
    
    # The ranges
    prediction_interval_90_lower=75,
    prediction_interval_90_upper=81,
    prediction_interval_95_lower=74,
    prediction_interval_95_upper=82,
    
    # The confidence
    confidence_score=93,
    
    # When it was made
    forecast_timestamp=timezone.now()
)

print(f"Forecast created: {forecast}")
```

**Step 8: Create Alert if Needed**

```python
# Check if this is concerning
if forecast.forecast_value > 90 and forecast.confidence_score > 85:
    Alert.objects.create(
        patient=patient,
        message=f"Heart rate predicted to reach {forecast.forecast_value} bpm",
        severity='WARNING',
        confidence=forecast.confidence_score
    )
    notify_staff()
else:
    print("No alert needed - prediction is normal")
```

**Final Output:**

```
═══════════════════════════════════════════════════════
RICHARD ANDERSON - HEART RATE FORECAST
═══════════════════════════════════════════════════════

Forecast Details:
  Point Estimate:       78 bpm
  Confidence:           93%
  90% Prediction Int.:  75-81 bpm
  95% Prediction Int.:  74-82 bpm

Reasoning:
  • Extensive data (291 measurements)
  • All models agree closely
  • Prediction within normal range
  • Patient is very stable

Clinical Interpretation:
  Richard's heart rate is expected to be 78 bpm.
  We are 93% confident in this prediction.
  This is slightly elevated from his baseline (72 bpm)
  but within his typical range. Monitor normally.

Alert Status: NO ALERT
═══════════════════════════════════════════════════════
```

---

## SECTION 7: THE COMPLETE CODE FLOW

### Simplified Code Structure

```python
# FILE: model_training.py

class TimeSeriesModel:
    """Main forecasting class"""
    
    def __init__(self):
        self.models = {}  # Store trained models
    
    def train_models(self, patient_data):
        """
        Step 1: Train all 5 models
        """
        self.models['exp_smooth'] = self._fit_exp_smoothing(patient_data)
        self.models['arima'] = self._fit_arima(patient_data)
        self.models['linear'] = self._fit_linear_trend(patient_data)
        self.models['moving_avg'] = self._fit_moving_average(patient_data)
        self.models['baseline'] = self._fit_baseline(patient_data)
    
    def make_prediction(self, patient_data):
        """
        Step 2-6: Make predictions and calculate confidence
        """
        
        # Get individual predictions
        predictions = {
            'exp_smooth': self.models['exp_smooth'].predict(),
            'arima': self.models['arima'].predict(),
            'linear': self.models['linear'].predict(),
            'moving_avg': self.models['moving_avg'].predict(),
            'baseline': self.models['baseline'].predict()
        }
        
        # Ensemble
        ensemble = self.ensemble_forecast(predictions)
        
        # Confidence
        confidence = self.calculate_confidence(
            patient_data,
            predictions,
            ensemble
        )
        
        # Intervals
        pi_90, pi_95 = self.calculate_intervals(predictions)
        
        return {
            'forecast': ensemble,
            'confidence': confidence,
            'pi_90': pi_90,
            'pi_95': pi_95
        }
    
    def ensemble_forecast(self, predictions):
        """Combine predictions"""
        return (
            0.35 * predictions['exp_smooth'] +
            0.25 * predictions['arima'] +
            0.20 * predictions['linear'] +
            0.15 * predictions['moving_avg'] +
            0.05 * predictions['baseline']
        )
    
    def calculate_confidence(self, data, predictions, ensemble):
        """Calculate 0-100% confidence"""
        
        data_score = self._data_volume_score(len(data))
        agree_score = self._model_agreement_score(predictions.values())
        extrap_score = self._extrapolation_score(ensemble, data)
        stable_score = self._stability_score(data)
        
        final = (
            0.25 * data_score +
            0.25 * agree_score +
            0.20 * extrap_score +
            0.30 * stable_score
        )
        
        return final


# FILE: views.py (How it's used)

def generate_forecast(request, patient_id):
    """
    Main function called to create a forecast
    """
    patient = Patient.objects.get(id=patient_id)
    
    # Get historical data
    vitals = VitalSigns.objects.filter(patient=patient).order_by('-recorded_at')[:30]
    
    # Create model
    model = TimeSeriesModel()
    model.train_models(vitals)
    
    # Make prediction
    result = model.make_prediction(vitals)
    
    # Save to database
    forecast = PatientForecast.objects.create(
        patient=patient,
        forecast_value=result['forecast'],
        confidence_score=result['confidence'],
        prediction_interval_90_lower=result['pi_90'][0],
        prediction_interval_90_upper=result['pi_90'][1],
        prediction_interval_95_lower=result['pi_95'][0],
        prediction_interval_95_upper=result['pi_95'][1],
    )
    
    return forecast
```

---

## QUICK REFERENCE: What Each Part Does

| Component | Purpose | Code |
|-----------|---------|------|
| Exp Smoothing | Recent changes matter more | `(0.3 × new) + (0.7 × old)` |
| ARIMA | Detect trend patterns | `next = last + average_change` |
| Linear Trend | Draw straight line | `HR = 1.5 × hours + 68` |
| Moving Avg | Smooth out noise | `avg(last 3 values)` |
| Baseline | Use historical average | `avg(all measurements)` |
| **Ensemble** | **Combine all** | **Weighted average** |
| **Confidence** | **How sure are we?** | **0-100% score** |
| **PI (Range)** | **Where could value be?** | **Lower to upper bound** |

---

## Summary

**This is what happens:**

1. **Collect** patient vital signs data (30+ measurements)
2. **Train** 5 different regression models on that data
3. **Predict** - each model makes its own prediction
4. **Combine** - weighted ensemble creates final prediction
5. **Analyze** - calculate 4 confidence factors
6. **Score** - combine factors into 0-100% confidence
7. **Range** - calculate 90% and 95% prediction intervals
8. **Store** - save prediction with all metrics
9. **Alert** - if prediction suggests problem, notify staff

**All this happens in milliseconds** and helps nurses know when to watch a patient more closely!

