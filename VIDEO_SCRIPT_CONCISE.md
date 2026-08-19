# VIDEO SCRIPT - CONCISE BUT DETAILED (2 Minutes)

---

## INTRODUCTION (15 seconds)

"This system predicts vital sign deterioration 24 hours early. It uses 5 forecasting methods combined with explainable AI - meaning we don't just predict, we explain why we're confident.

Here's the demo."

---

## DATA (10 seconds)

"We load 50 heart rate measurements from the patient's database. Range: 60-85 bpm. Now we forecast what it will be tomorrow."

---

## THE 5 METHODS (45 seconds)

### ARIMA (35% weight)
"ARIMA analyzes the PATTERN OF CHANGES. If heart rate went up 2, up 1, down 2, up 3 - ARIMA calculates momentum and says the trend continues. This catches GRADUAL DETERIORATION. Why 35%? Because it's best at detecting health decline."

### Exponential Smoothing (25% weight)
"Recent measurements matter more than old ones. Formula: 30% today + 70% yesterday. Catches recent patient changes."

### Linear Trend (20% weight)
"Fits a straight line through data. Slope = 0.3 bpm/day. Catches sustained directional patterns."

### Moving Average (15% weight)
"Average last 3 measurements. Filters out measurement noise and random jumps."

### Baseline (5% weight)
"Average of ALL measurements (70.81 bpm). Safety anchor - prevents wild predictions."

---

## ENSEMBLE (30 seconds)

"Each method gives a different prediction:
- ARIMA: 67.16
- ExpSmoothing: 69.72
- LinearTrend: 71.74
- MovingAverage: 70.00
- Baseline: 70.81

We combine them with WEIGHTS:

**Forecast = (0.35×67.16) + (0.25×69.72) + (0.20×71.74) + (0.15×70) + (0.05×70.81) = 69.33**

Why combine? No single method catches all patterns. Together, they're stronger."

---

## CONFIDENCE SCORING (45 seconds)

We evaluate 4 independent factors:

### 1. DATA VOLUME (25% weight)
"Do we have enough data? 50 measurements = 95% ✓
Thresholds: <5 (10%) | 5-10 (30%) | 10-20 (60%) | 20-40 (85%) | 40+ (95%)"

### 2. MODEL AGREEMENT (25% weight)
"Do all 5 methods agree? Deviation = 2.06% = 85% ✓
Thresholds: <2% (95%) | 2-5% (85%) | 5-10% (70%) | >15% (30%)"

### 3. EXTRAPOLATION (20% weight)
"Is forecast realistic? 69.33 is within observed range [60-85] = 95% ✓
Thresholds: Within range (95%) | ±1std (80%) | ±2std (50%) | Beyond (20%)"

### 4. STABILITY (30% weight - MOST IMPORTANT)
"Is patient predictable? CV = 0.096 (9.6% variation) = 70% ✓
Thresholds: <0.05 (95%) | <0.08 (85%) | <0.12 (70%) | <0.15 (50%) | >0.15 (35%)
Why highest weight? Stable patients are predictable. Chaotic patients aren't."

---

## FINAL CONFIDENCE (20 seconds)

"**Confidence = (0.25×95) + (0.25×85) + (0.20×95) + (0.30×70) = 85%**

Classification:
- ≥90% = HIGH → Automatic alert
- 70-89% = MEDIUM → Nurse reviews first
- <70% = LOW → Information only

**Result: 85% MEDIUM confidence → Nurse validates before alert**"

---

## PREDICTION INTERVALS (15 seconds)

"We also calculate the range where actual value will fall:

**90% PI: [63.75, 74.90]** (tighter, more optimistic)
**95% PI: [62.68, 75.97]** (wider, more conservative)

This shows uncertainty. Clinicians know the margin of error."

---

## CLINICAL ACTION (10 seconds)

"85% confidence = MEDIUM

System says: 'I predict 69.33 bpm, but I'm moderately sure. A nurse should review this before I trigger an alert.'

This is safe design - humans validate uncertain predictions."

---

## SUMMARY (10 seconds)

"5 methods → Ensemble forecast → 4 confidence checks → Clinical action.

The system gives accurate predictions AND explains why. It's transparent AI for healthcare.

That's how early deterioration detection works."

---

**TOTAL: ~2 MINUTES OF NARRATION**
