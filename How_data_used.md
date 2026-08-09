## Overview

JOMINGOS predicts patient deterioration **BEFORE it becomes critical** by analyzing:
1. **Current vital signs** (NEWS2 score)
2. **Historical vital signs** (past 20 recordings)
3. **Trend analysis** (rate of change)
4. **Combined risk assessment**

---

## How Data is Stored & Used

### Data Storage Architecture

```
Patient
    ├── Vital Recording #1 (4 hours ago)
    │   ├── HR: 72 bpm
    │   ├── RR: 16 br/min
    │   ├── SpO2: 97%
    │   ├── BP: 120/80
    │   └── Temp: 37.0°C
    │
    ├── Vital Recording #2 (3 hours ago)
    │   ├── HR: 75 bpm
    │   ├── RR: 18 br/min
    │   ├── SpO2: 96%
    │   ├── BP: 122/82
    │   └── Temp: 37.2°C
    │
    ├── Vital Recording #3 (2 hours ago) ← CURRENT
    │   ├── HR: 85 bpm
    │   ├── RR: 22 br/min
    │   ├── SpO2: 94%
    │   ├── BP: 128/85
    │   └── Temp: 37.8°C
    │
    └── ... previous 17 recordings (history)
```

**Key Insight**: Instead of looking at ONE vital sign and making a yes/no decision, JOMINGOS looks at the **HISTORY** and detects **PATTERNS**.

---

## The Prediction Algorithm (Step-by-Step)

### Step 1: Calculate NEWS2 Score (Absolute Risk)

NEWS2 assigns points to each vital sign based on how far it deviates from normal:

```
NEWS2 Calculation:

For each vital sign:
  - Heart Rate: 51-90 bpm = 0 points (normal)
              91-110 bpm = 1 point (slightly high)
             111-130 bpm = 2 points (high)
                  ≥131 bpm = 3 points (critical)

  - Respiratory Rate: 12-20 br/min = 0 points (normal)
                      21-24 br/min = 2 points (high)
                       ≥25 br/min = 3 points (critical)

  - SpO2: ≥95% = 0 points (normal)
          94-95% = 1 point (slightly low)
          92-93% = 2 points (low)
           ≤91% = 3 points (critical)

  - Blood Pressure: 110-219 mmHg = 0 points (normal)
                    100-109 mmHg = 1 point (low)
                      ≤90 mmHg = 3 points (critical)

  - Temperature: 36.1-38.0°C = 0 points (normal)
                 35.1-36.0°C = 1 point (low)
                 38.1-39.0°C = 1 point (high)
                    ≤35.0°C = 3 points (critical)

NEWS2_TOTAL = Sum of all component scores
```

#### Example 1: Stable Patient
```
Current Vitals:
  HR: 78 bpm           → Score 0 (normal range 51-90)
  RR: 16 br/min        → Score 0 (normal range 12-20)
  SpO2: 97%            → Score 0 (≥95%)
  SBP: 125 mmHg        → Score 0 (110-219 range)
  Temp: 37.2°C         → Score 0 (36.1-38.0 range)
  ─────────────────────────────
  NEWS2 TOTAL: 0 (LOW RISK)
  
Interpretation: Patient is STABLE. Continue routine monitoring (≥12 hourly).
```

#### Example 2: Medium Risk Patient
```
Current Vitals:
  HR: 105 bpm          → Score 1 (91-110 range)
  RR: 24 br/min        → Score 2 (21-24 range)
  SpO2: 94%            → Score 1 (94-95 range)
  SBP: 135 mmHg        → Score 0 (110-219 range)
  Temp: 38.5°C         → Score 1 (38.1-39.0 range)
  ─────────────────────────────
  NEWS2 TOTAL: 5 (MEDIUM RISK)
  
Interpretation: Patient shows abnormal vitals. Escalate to senior staff,
increase monitoring frequency.
```

---

### Step 2: Analyze Trends (Historical Analysis)

Here's where JOMINGOS becomes **PREDICTIVE** instead of reactive:

```
Trend Analysis Logic:

Get the LAST 20 vital recordings for this patient (history)
Compare CURRENT vitals with PREVIOUS vitals
Calculate RATE OF CHANGE per hour
```

#### Rate of Change Calculation

```
Rate_of_Change = (Current_Value - Previous_Value) / Time_Elapsed_Hours

Example:
  If SpO2 drops from 96% to 92% in 1 hour:
  ROC = (92 - 96) / 1 = -4%/hour
  
  At this rate, SpO2 will reach 91% (critical) in:
  91% = 96% + (-4%/hour × T)
  T = 1.25 hours = 75 minutes
  
  ⚠️ ALERT: Patient will reach CRITICAL in 75 minutes!
  This gives staff TIME TO INTERVENE BEFORE CRISIS.
```

#### Trend Scoring Rules

Each vital sign has a threshold. When exceeded, trend score increases:

```
Trend Scoring:

Heart Rate:
  ├─ Rising > 10 bpm/hour        → +2 points (cardiovascular stress)
  └─ Stable or decreasing        → 0 points

Respiratory Rate:
  ├─ Rising > 5 br/hour          → +2 points (respiratory distress)
  └─ Stable or decreasing        → 0 points

Oxygen Saturation (SpO2):
  ├─ Dropping > 2%/hour          → +3 points (MOST CRITICAL)
  └─ Stable or increasing        → 0 points

Systolic Blood Pressure:
  ├─ Dropping > 10 mmHg/hour     → +2 points (circulation failure)
  └─ Stable or increasing        → 0 points

Temperature:
  ├─ Abnormal trend > 0.5°C/hour → +2 points (fever/hypothermia progression)
  └─ Stable trend                → 0 points

TREND_SCORE = Sum of all trend points
```

#### Example 3: Patient Trending Toward Critical

```
Recording Timeline:

Time 1 (4 hours ago):
  SpO2: 96%
  HR: 72 bpm
  RR: 16 br/min

Time 2 (3 hours ago):
  SpO2: 95%
  HR: 78 bpm
  RR: 18 br/min

Time 3 (2 hours ago):
  SpO2: 94%
  HR: 82 bpm
  RR: 20 br/min

Time 4 (1 hour ago):
  SpO2: 93%
  HR: 90 bpm
  RR: 23 br/min

Time 5 (NOW - Current):
  SpO2: 91%              ← CRITICAL THRESHOLD REACHED!
  HR: 95 bpm
  RR: 25 br/min

Calculate Rate of Change (Time 4 → Time 5):
  SpO2 ROC: (91 - 93) / 1 hour = -2%/hour    → Score: +3 (dropping)
  HR ROC:   (95 - 90) / 1 hour = +5 bpm/hour → Score: 0 (< 10 threshold)
  RR ROC:   (25 - 23) / 1 hour = +2 br/hour  → Score: 0 (< 5 threshold)

TREND_SCORE: 3 points

NEWS2 Total (current): 
  SpO2: 91% = 3 points (critical)
  HR: 95 bpm = 1 point
  RR: 25 br/min = 3 points
  BP: normal = 0 points
  Temp: normal = 0 points
  ─────────────────
  NEWS2 TOTAL: 7 (CRITICAL!)

Combined Risk: NEWS2 (7) + Trend (3) = 10 (VERY HIGH)
```

---

### Step 3: Alert Decision Engine

The system uses **MULTIPLE CRITERIA** to decide whether to alert:

```
ALERT DECISION RULES:

Rule 1: REACTIVE ALERT (Already Critical)
  ├─ IF NEWS2 >= 7
  └─ THEN Alert = CRITICAL (immediate review required)

Rule 2: DETERIORATING ALERT (Medium Risk + Trends)
  ├─ IF NEWS2 >= 5 AND TREND_SCORE > 0
  └─ THEN Alert = HIGH (escalate to senior staff)

Rule 3: PREDICTIVE ALERT (Significant Trend Alone)
  ├─ IF TREND_SCORE >= 5
  └─ THEN Alert = HIGH (patient trending toward critical)

Rule 4: NO ALERT (Stable)
  ├─ IF none of above conditions met
  └─ THEN Alert = NONE (routine monitoring)
```

#### Example 4: How Conclusions Are Reached

**Scenario: Patient Jane Doe**

```
Step 1: Get Current Vitals
  ─────────────────────────────────────────
  Heart Rate:        105 bpm
  Respiratory Rate:  24 br/min
  SpO2:              94%
  Systolic BP:       130 mmHg
  Temperature:       38.5°C

Step 2: Calculate NEWS2 Score
  ─────────────────────────────────────────
  HR 105:   Score 1 (in 91-110 range)
  RR 24:    Score 2 (in 21-24 range)
  SpO2 94:  Score 1 (in 94-95 range)
  BP 130:   Score 0 (in 110-219 range)
  Temp 38.5: Score 1 (in 38.1-39.0 range)
  ──────────────────────────────────────
  NEWS2 TOTAL: 5 (MEDIUM RISK - not yet critical)

Step 3: Get Previous Vitals (from history)
  ─────────────────────────────────────────
  Previous Recording (1 hour ago):
    HR: 92 bpm
    RR: 20 br/min
    SpO2: 96%
    Temp: 38.0°C

Step 4: Calculate Trends (Rate of Change)
  ─────────────────────────────────────────
  HR ROC:    (105 - 92) / 1 = +13 bpm/hour  → Score: +2 (> 10 threshold)
  RR ROC:    (24 - 20) / 1 = +4 br/hour     → Score: 0 (< 5 threshold)
  SpO2 ROC:  (94 - 96) / 1 = -2%/hour       → Score: +3 (= threshold!)
  Temp ROC:  (38.5 - 38.0) / 1 = +0.5°C/hr  → Score: +2 (abnormal)
  ──────────────────────────────────────────
  TREND_SCORE: 7 (SIGNIFICANT!)

Step 5: Apply Alert Decision Rules
  ─────────────────────────────────────────
  ✓ Check Rule 1: NEWS2 >= 7?  NO (only 5)
  ✓ Check Rule 2: NEWS2 >= 5 AND Trend > 0?  YES!
  
  ∴ ALERT TRIGGERED!

Step 6: Determine Priority
  ─────────────────────────────────────────
  Since Rule 2 matched (HIGH RISK + DETERIORATING)
  Priority = HIGH (not yet CRITICAL, but escalate to senior)

Step 7: Generate Reasoning Message
  ─────────────────────────────────────────
  "HIGH RISK WITH DETERIORATING TREND:
   NEWS2=5 (medium), Trend Score=7
   - Heart Rate rising 13 bpm/hour
   - SpO2 dropping 2%/hour
   - Temperature rising 0.5°C/hour
   
   ACTION: Escalate to senior staff immediately.
   Patient showing multiple adverse trends that suggest
   deterioration. Clinical intervention may prevent
   progression to critical state."

CONCLUSION: Alert is raised, giving staff TIME to act
BEFORE patient becomes critical (NEWS2 >= 7).
```

---

## Real-World Example: How Prevention Works

### Scenario: Without JOMINGOS (Reactive)

```
Time 1 (4 hours ago): NEWS2 = 4 (stable)
  → No monitoring change needed

Time 2 (3 hours ago): NEWS2 = 4 (stable)
  → No monitoring change needed

Time 3 (2 hours ago): NEWS2 = 5 (medium)
  → Staff: "Hmm, slightly elevated. Monitor closely."

Time 4 (1 hour ago): NEWS2 = 6 (medium)
  → Staff: "Still medium risk. Waiting..."

Time 5 (NOW): NEWS2 = 7 (CRITICAL!)
  → ALERT! But patient is already in danger zone
  → Emergency action required
  → Possible hospital transfer
  → 🚨 CRISIS SITUATION

Result: Staff reacted to crisis AFTER it happened.
Opportunity for prevention MISSED.
```

### Same Scenario: With JOMINGOS (Predictive)

```
Time 1 (4 hours ago): NEWS2 = 4, Trend = 0
  → Stable, routine monitoring

Time 2 (3 hours ago): NEWS2 = 4, Trend = 0
  → Stable, routine monitoring

Time 3 (2 hours ago): NEWS2 = 4, Trend = 2 (HR rising)
  → Slight trend detected, increase monitoring

Time 4 (1 hour ago): NEWS2 = 5, Trend = 5 (SpO2 dropping!)
  → 🚨 ALERT TRIGGERED (Rule 2: Medium + Deteriorating)
  → "ALERT: Patient trending toward critical"
  → Staff escalate to senior nurse
  → Senior nurse reviews: "Patient declining, let's intervene"
  → Oxygen therapy started
  → Breathing exercises recommended

Time 5 (NOW): NEWS2 = 6, Trend = 3 (improvement starting)
  → ✅ CRISIS PREVENTED
  → Patient stabilizing
  → No emergency transfer needed

Result: Staff took PREVENTIVE action based on TREND.
Patient never reached critical state.
Healthcare cost reduced. Patient safety improved.
```

---

## How the System Shows All This Clearly

### Backend Dashboard (Patient Vital History View)

When you click on a patient in the Vitals Dashboard, you see:

```
📋 PATIENT VITAL HISTORY & PREDICTION ANALYSIS
══════════════════════════════════════════════════

Patient: Jane Doe (ID: 2)
Total Recordings: 45 | Active Alerts: 3

─────────────────────────────────────────────────

Recording #1 (4 hours ago) ✅ No Alert
──────────────────────────
Current Vital Signs:
  ❤️  Heart Rate: 78 bpm (Score: 0)
  🫁 Respiratory Rate: 16 br/min (Score: 0)
  💨 SpO2: 97% (Score: 0)
  🩸 BP: 120/80 mmHg (Score: 0)
  🌡️  Temperature: 37.0°C (Score: 0)

Trend Analysis (vs Previous):
  Heart Rate: +2.5 bpm/hour (Stable)
  Respiratory Rate: +1.0 br/hour (Stable)
  SpO2: +0.5%/hour (Stable)
  Systolic BP: +1.2 mmHg/hour (Stable)

Alert Prediction Reasoning (Step-by-Step):
  Step 1: Calculate NEWS2 Score = 0
  Step 2: Analyze Trends
    • No significant trends detected
  Step 3: Calculate Trend Score = 0
  Step 4: Combined Risk = 0 + 0 = 0
  Step 5: Alert Decision Engine
    ✗ NEWS2 >= 7? NO
    ✗ NEWS2 >= 5 AND Trend > 0? NO
    ✗ Trend Score >= 5? NO
  Step 6: Clinical Interpretation
    ✅ STABLE: Continue routine monitoring

Alert Decision Result:
  Alert Triggered: NO
  Priority: NONE
  Reason: Routine monitoring: NEWS2=0 (LOW risk)

─────────────────────────────────────────────────

Recording #4 (1 hour ago) 🚨 ALERT TRIGGERED
──────────────────────────
Current Vital Signs:
  ❤️  Heart Rate: 95 bpm (Score: 1)
  🫁 Respiratory Rate: 25 br/min (Score: 3)
  💨 SpO2: 91% (Score: 3)
  🩸 BP: 125/80 mmHg (Score: 0)
  🌡️  Temperature: 38.5°C (Score: 1)

Trend Analysis (vs Previous Recording):
  Heart Rate: +13.0 bpm/hour (🚨 RISING FAST)
  Respiratory Rate: +5.0 br/hour (Slightly rising)
  SpO2: -2.5%/hour (🚨 DROPPING CRITICALLY)
  Systolic BP: -2.0 mmHg/hour (Stable)

Alert Prediction Reasoning (Step-by-Step):
  Step 1: Calculate NEWS2 Score = 8
  Step 2: Analyze Trends (Rate of Change)
    • HR rising 13.0 bpm/hour
    • RR rising 5.0 br/hour
    • SpO2 DROPPING 2.5%/hour (HIGH RISK)
  Step 3: Calculate Trend Score = 8
  Step 4: Combined Risk = 8 + 8 = 16
  Step 5: Alert Decision Engine
    ✓ NEWS2 >= 7? YES → ALERT TRIGGERED
    ✓ CRITICAL condition detected
  Step 6: Clinical Interpretation
    🚨 CRITICAL: Immediate medical review required

Alert Decision Result:
  Alert Triggered: YES
  Priority: CRITICAL
  Reason: CRITICAL: NEWS2 score 8 (immediate review required)

How This Conclusion Was Reached:
  1. System stored 20 previous vital recordings
  2. Noticed SpO2 dropping 2.5% per hour
  3. Calculated that critical SpO2 (≤91%) would be reached
  4. NEWS2 score jumped from 5 to 8
  5. Multiple adverse trends (HR, RR, SpO2 all worsening)
  6. Combined risk score = 16 (very high)
  7. Alert triggered BEFORE complete crisis
  8. Staff notified to intervene
```

---

## Summary: How JOMINGOS Prevents Emergencies

| Aspect | Traditional (Reactive) | JOMINGOS (Predictive) |
|--------|------------------------|----------------------|
| **Data Used** | Current vital only | Current + Past 20 recordings |
| **Analysis** | Single snapshot | Historical trends |
| **Alert Timing** | When critical (NEWS2≥7) | Before critical (trends detected) |
| **Warning Time** | 0 minutes | 15-60 minutes |
| **Intervention** | Emergency action | Preventive care |
| **Staff Action** | Crisis management | Proactive management |
| **Outcome** | Hospital transfers | Avoided emergencies |

---

## Key Takeaway

**JOMINGOS stores patient vital history over time, analyzes the TRENDS in that data, and alerts clinical staff BEFORE a patient reaches critical condition. This gives time for preventive intervention instead of emergency response.**

The system shows ALL calculations step-by-step so healthcare professionals can:
- ✅ Understand WHY an alert was triggered
- ✅ Review the clinical reasoning
- ✅ Trust the system's predictions
- ✅ Take informed clinical decisions
