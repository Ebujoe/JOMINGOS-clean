# ALERT SYSTEM - VISUAL FLOWCHARTS FOR UNDERSTANDING

**Use these flowcharts to explain your system to anyone**

---

## FLOWCHART 1: THE COMPLETE DATA FLOW

```
START: NURSE ENTERS VITAL SIGNS
│
├─ Input: Heart Rate = 140
├─ Input: Respiratory Rate = 28  
├─ Input: Oxygen = 88%
├─ Input: Blood Pressure = 160/100
└─ Input: Temperature = 38.5°C
│
↓ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
│  DATABASE SAVES DATA
│  Table: vitals_vitalsigns
└─▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
│
↓ ⚡⚡⚡ SIGNAL TRIGGERED (AUTOMATIC)
│  Django detects: New vital saved
│  Calls: auto_detect_deterioration()
│
↓  ML MODEL LOADS
│  File: deterioration_model.pkl
│  Status: Ready
│
↓ MODEL ANALYZES
│  Receives: {140, 28, 88, 160/100, 38.5}
│  Processes: Mathematical analysis
│  Returns: {"critical": True, "prob": 0.85}
│
↓  DECISION LOGIC
│  if result.is_critical == True:
│      └─> CREATE ALERT
│  else:
│      └─> DO NOTHING
│
│  [DECISION: CREATE ALERT] ✓
│
↓ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
│  ALERT SAVED TO DATABASE
│  Table: deterioration_alerts_alert
│  Status: "active"
│  Priority: "critical"
│  Patient: John Doe
│  Reason: "ML prediction: 85%"
└─▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
│
↓ EVERY 30 SECONDS...
│  Frontend Component: AlertDashboard.tsx
│  Triggers: useEffect hook
│  Action: fetchAlerts()
│
↓  API CALL
│  Request: GET /api/alerts/active_alerts/
│  Headers: {"Authorization": "Bearer TOKEN"}
│  To: http://localhost:8000/api
│
↓ ✅ BACKEND RESPONDS
│  Queries: DeteriorationAlert.objects.filter(status='active')
│  Returns: [
│    {
│      "id": 1,
│      "patient_name": "John Doe",
│      "priority": "critical",
│      "trigger_reason": "ML prediction: RED (85%)",
│      "triggered_at": "2026-06-27 14:30:00"
│    }
│  ]
│
↓ ⚛️  REACT STATE UPDATES
│  Hook: setAlerts(response)
│  State Change:
│    alerts = []
│    ↓
│    alerts = [{id: 1, patient_name: "John", ...}]
│
↓ 🎨 COMPONENT RE-RENDERS
│  Browser re-draws screen
│  Creates alert card with:
│    ├─ Red border
│    ├─ "CRITICAL" badge
│    ├─ Patient name
│    ├─ Alert reason
│    └─ "Acknowledge" button
│
↓ 👁️ STAFF SEES ALERT
│  Dashboard Display:
│  ┌──────────────────────────┐
│  │ 🚨 CRITICAL ALERT        │
│  │ Patient: John Doe        │
│  │ Reason: ML detected      │
│  │ Time: 14:30              │
│  │ [ACKNOWLEDGE ALERT] btn  │
│  └──────────────────────────┘
│
↓ 🖱️ STAFF CLICKS BUTTON
│  Action: acknowledgeAlert(alertId)
│  Triggers: API call
│
↓ 📤 API CALL
│  Request: POST /api/alerts/1/acknowledge/
│  Headers: {"Authorization": "Bearer TOKEN"}
│  To: http://localhost:8000/api
│
↓ 💾 BACKEND UPDATES
│  Alert record updated:
│    status: "active" → "acknowledged"
│    acknowledged_by: "StaffMember"
│    acknowledged_at: "2026-06-27 14:31:00"
│
↓ ✅ RESPONSE SENT
│  {"status": "acknowledged"}
│
↓ ⚛️  REACT STATE UPDATES
│  Hook: setAlerts(alerts.filter(a => a.id !== 1))
│  Alert removed from array
│
↓ 🎨 COMPONENT RE-RENDERS
│  Card is removed from screen
│
END: ALERT ACKNOWLEDGED
```

---

## FLOWCHART 2: ARCHITECTURE LAYERS

```
┌────────────────────────────────────────────────────────┐
│             LAYER 3: USER INTERFACE                    │
│         (What Staff Sees on Screen)                    │
├────────────────────────────────────────────────────────┤
│                                                         │
│   Browser (Chrome/Firefox)                            │
│   ↓                                                    │
│   React Application (AlertDashboard.tsx)              │
│   ├─ Fetch alerts                                      │
│   ├─ Display cards                                     │
│   ├─ Handle clicks                                     │
│   └─ Update screen                                     │
│                                                         │
│   Technology: JavaScript, React.js, CSS               │
│   Port: 3000                                           │
│   File: frontend/components/AlertDashboard.tsx        │
│                                                         │
└────────────┬──────────────────────────────────────────┘
             │
      HTTP Requests
      (REST API Calls)
             │
             ↓
┌────────────────────────────────────────────────────────┐
│           LAYER 2: API & BUSINESS LOGIC                │
│      (Server That Processes Requests)                  │
├────────────────────────────────────────────────────────┤
│                                                         │
│   Django REST Framework                               │
│   ├─ Receives requests from frontend                   │
│   ├─ Validates data                                    │
│   ├─ Checks authentication                             │
│   ├─ Queries database                                  │
│   ├─ Runs ML model                                     │
│   ├─ Returns JSON responses                            │
│   └─ Logs all actions                                  │
│                                                         │
│   API Endpoints:                                       │
│   ├─ GET /api/alerts/active_alerts/                   │
│   ├─ GET /api/alerts/critical_alerts/                 │
│   ├─ POST /api/alerts/{id}/acknowledge/               │
│   └─ POST /api/accounts/login/                        │
│                                                         │
│   Technology: Python, Django, Django REST Framework   │
│   Port: 8000                                           │
│   File: backend/deterioration_alerts/views_api.py    │
│                                                         │
└────────────┬──────────────────────────────────────────┘
             │
      Database Queries
      & ML Predictions
             │
             ↓
┌────────────────────────────────────────────────────────┐
│         LAYER 1: DATA & INTELLIGENCE                   │
│    (Database + Machine Learning Model)                 │
├────────────────────────────────────────────────────────┤
│                                                         │
│   SQLite Database                                      │
│   ├─ patients table                                    │
│   ├─ vitals table                                      │
│   ├─ alerts table                                      │
│   ├─ users table                                       │
│   └─ other tables                                      │
│                                                         │
│   File: backend/db.sqlite3                            │
│                                                         │
│   ┌──────────────────────────────────────────────────┐ │
│   │    ML Model (deterioration_model.pkl)            │ │
│   │                                                   │ │
│   │  Input: Vital Signs Data                        │ │
│   │    ├─ Heart Rate                                 │ │
│   │    ├─ Respiratory Rate                           │ │
│   │    ├─ Oxygen Saturation                          │ │
│   │    ├─ Blood Pressure                             │ │
│   │    └─ Temperature                                │ │
│   │                                                   │ │
│   │  Process: Mathematical Analysis                 │ │
│   │    ├─ Load pre-trained weights                   │ │
│   │    ├─ Pass data through network                  │ │
│   │    ├─ Compare to learned patterns                │ │
│   │    └─ Calculate confidence                       │ │
│   │                                                   │ │
│   │  Output: Prediction                             │ │
│   │    ├─ is_critical: True/False                    │ │
│   │    ├─ probability: 0.0 - 1.0                    │ │
│   │    ├─ alert_level: RED/AMBER/YELLOW/GREEN      │ │
│   │    └─ confidence: 0% - 100%                      │ │
│   │                                                   │ │
│   └──────────────────────────────────────────────────┘ │
│                                                         │
│   Technology: SQLite, Python, scikit-learn/TensorFlow  │
│   Signal Handler: backend/vitals/models.py            │
│                                                         │
└────────────────────────────────────────────────────────┘

Legend:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Layer 1 = Database + ML (Brain & Memory)
Layer 2 = API & Logic (Processing Engine)
Layer 3 = User Interface (What User Sees)
```

---

## FLOWCHART 3: DECISION MAKING PROCESS

```
                    VITAL SIGNS RECORDED
                            │
                            ↓
                    ┌───────────────┐
                    │ ML MODEL      │
                    │ ANALYZES DATA │
                    └───────────────┘
                            │
                            ↓
                ┌─────────────────────────┐
                │   CALCULATION RESULT    │
                │                         │
                │  is_critical: boolean   │
                │  probability: 0.0-1.0   │
                │  alert_level: string    │
                └─────────────────────────┘
                            │
                            ↓
                ┌─────────────────────────┐
                │   DECISION POINT        │
                │                         │
                │  if is_critical == True │
                └────────┬────────────────┘
                         │
                    ┌────┴────┐
                    │          │
               YES  │          │  NO
                    ↓          ↓
            ┌────────────┐  ┌──────────┐
            │  CREATE    │  │ NO ALERT │
            │  ALERT     │  │ CREATED  │
            └────┬───────┘  └──────────┘
                 │
                 ↓
        ┌─────────────────┐
        │ ALERT IN DB     │
        │ status=active   │
        └─────────────────┘
                 │
                 ↓
        ┌─────────────────┐
        │ AWAITING STAFF  │
        │ RESPONSE        │
        └─────────────────┘
                 │
                 ↓ (When staff clicks acknowledge)
        ┌─────────────────┐
        │ UPDATE STATUS   │
        │ "acknowledged"  │
        └─────────────────┘
                 │
                 ↓
        ┌─────────────────┐
        │ REMOVE FROM     │
        │ ACTIVE LIST     │
        └─────────────────┘
```

---

## FLOWCHART 4: AUTHENTICATION FLOW

```
STAFF LOGIN PROCESS
═══════════════════════════════════════════════════════

START: Staff opens application
│
↓ Goes to: http://localhost:3000/login
│
↓ Enters credentials:
│ ├─ Username: teststaff
│ └─ Password: testpass123
│
↓ Clicks: "Sign In" button
│
↓ Frontend sends API request:
│ POST /api/accounts/login/
│ {
│   "username": "teststaff",
│   "password": "testpass123"
│ }
│
↓ Backend (Django) receives request
│
↓ Checks database:
│ ├─ Does user exist? ✓ YES
│ ├─ Is password correct? ✓ YES
│ └─ Is user active? ✓ YES
│
↓ Backend generates JWT token
│ Token example:
│ eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.
│ eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9l...
│
↓ Backend sends response:
│ {
│   "access": "eyJhbGc...",
│   "refresh": "eyJhbGc...",
│   "user": {
│     "id": 1,
│     "username": "teststaff",
│     "email": "test@test.com"
│   }
│ }
│
↓ Frontend receives response
│
↓ Frontend stores token:
│ localStorage.setItem('access_token', token)
│
↓ Frontend redirects:
│ http://localhost:3000/dashboard
│
↓ Component mounts: <AlertDashboard />
│
↓ useEffect runs:
│ const token = localStorage.getItem('access_token')
│ ✓ Token found!
│
↓ Adds token to API request headers:
│ {
│   "Authorization": "Bearer eyJhbGc...",
│   "Content-Type": "application/json"
│ }
│
↓ Calls: GET /api/alerts/active_alerts/
│
↓ Backend receives request
│
↓ Backend checks token:
│ ├─ Is token valid? ✓ YES
│ ├─ Is token expired? ✗ NO (not expired)
│ └─ Is user still active? ✓ YES
│
↓ Backend queries database for alerts
│
↓ Backend returns alerts as JSON
│
↓ Frontend displays alerts
│ ┌─────────────────────────┐
│ │ Dashboard: All Clear!   │
│ │ or                      │
│ │ [CRITICAL ALERT CARD]   │
│ └─────────────────────────┘
│
END: Staff can now see alerts


AUTHENTICATION ON EVERY API CALL
═══════════════════════════════════════════════════════

Step 1: Staff clicks "Acknowledge Alert" button
         │
         ↓
Step 2: Frontend makes API request
         POST /api/alerts/1/acknowledge/
         {
           "Authorization": "Bearer TOKEN"  ← Token included
         }
         │
         ↓
Step 3: Backend receives request
         ├─ Extract token from header
         ├─ Verify token signature
         ├─ Check token not expired
         └─ Confirm user permissions
         │
         ↓
Step 4: If valid → Process request
         If invalid → Return 401 Unauthorized
         │
         ↓
Step 5: Return response to frontend


WHEN TOKEN EXPIRES
═══════════════════════════════════════════════════════

After 24 hours:
  Token expires
  ↓
Next API call:
  Backend returns: 401 Unauthorized
  ↓
Frontend catches error:
  User must login again
  ↓
Redirects to login page:
  http://localhost:3000/login
  ↓
User logs in again:
  Gets new token
  ↓
Can use system again
```

---

## FLOWCHART 5: ML MODEL PREDICTION PROCESS

```
ML MODEL PREDICTION DETAILED FLOW
═══════════════════════════════════════════════════════

INPUT: Raw Vital Signs
┌──────────────────────────────────┐
│ Heart Rate: 140 bpm              │  Normal Range: 60-100
│ Respiratory Rate: 28 /min        │  Normal Range: 12-20
│ Oxygen Saturation: 88%           │  Normal Range: 95-100%
│ Systolic BP: 160 mmHg            │  Normal Range: 90-120
│ Diastolic BP: 100 mmHg           │  Normal Range: 60-80
│ Temperature: 38.5°C              │  Normal Range: 36.5-37.5
│ Glucose: 180 mg/dL               │  Normal Range: 70-100
│ pH: 7.35                         │  Normal Range: 7.35-7.45
└──────────────────────────────────┘
         │
         ↓
PREPROCESSING LAYER
┌──────────────────────────────────┐
│ Normalize values (0-1 scale)     │
│ Handle missing data              │
│ Remove outliers                  │
│ Create feature vector            │
│                                  │
│ Result: [0.78, 0.89, 0.42, ...]│
└──────────────────────────────────┘
         │
         ↓
NEURAL NETWORK LAYERS
┌──────────────────────────────────┐
│ Layer 1: Input layer             │
│   Neurons: 10 (one per vital)    │
│   Activation: ReLU               │
│                                  │
│ Layer 2: Hidden layer            │
│   Neurons: 16                    │
│   Activation: ReLU               │
│                                  │
│ Layer 3: Hidden layer            │
│   Neurons: 8                     │
│   Activation: ReLU               │
│                                  │
│ Layer 4: Output layer            │
│   Neurons: 1                     │
│   Activation: Sigmoid (0-1)      │
└──────────────────────────────────┘
         │
         ↓
COMPUTATION
┌──────────────────────────────────┐
│ Input: [0.78, 0.89, 0.42, ...]   │
│         ↓                        │
│ Forward pass through network     │
│         ↓                        │
│ Weights: [learned from training] │
│ Biases: [learned from training]  │
│         ↓                        │
│ Mathematical operations:         │
│ y = sigmoid(Wx + b)              │
│         ↓                        │
│ Output: 0.85                     │
└──────────────────────────────────┘
         │
         ↓
PROBABILITY INTERPRETATION
┌──────────────────────────────────┐
│ Raw output: 0.85                 │
│                                  │
│ Interpretation:                  │
│ 0.0-0.3 = Stable (Low Risk)      │
│ 0.3-0.6 = Monitor (Medium Risk)  │
│ 0.6-0.8 = High Risk              │
│ 0.8-1.0 = Critical Risk          │
│                                  │
│ 0.85 falls in: CRITICAL (0.8-1.0)│
└──────────────────────────────────┘
         │
         ↓
CONFIDENCE CALCULATION
┌──────────────────────────────────┐
│ Probability: 0.85                │
│ Confidence: 85%                  │
│ Meaning: "85% confident this is  │
│          a critical case"        │
└──────────────────────────────────┘
         │
         ↓
OUTPUT: PREDICTION RESULT
┌──────────────────────────────────┐
│ {                                │
│   "is_critical": true,           │
│   "probability": 0.85,           │
│   "confidence": 85,              │
│   "alert_level": "CRITICAL",     │
│   "color": "RED",                │
│   "reason": "Multiple abnormal   │
│              vital readings"     │
│ }                                │
└──────────────────────────────────┘


WHAT THE MODEL LEARNED FROM TRAINING
═══════════════════════════════════════════════════════

The model was trained on historical data like:

Case 1: ✓ Patient deteriorated
├─ HR=140, RR=28, O2=88 → CRITICAL

Case 2: ✓ Patient deteriorated  
├─ HR=135, RR=26, O2=89 → CRITICAL

Case 3: ✓ Patient was stable
├─ HR=78, RR=16, O2=97 → STABLE

Case 4: ✓ Patient recovered
├─ HR=82, RR=18, O2=96 → STABLE

Case 5: ✓ Patient deteriorated rapidly
├─ HR=150, RR=32, O2=85 → CRITICAL

... (repeated 5,000+ times) ...

Result:
The model learned patterns:
├─ High HR + High RR + Low O2 = Critical
├─ High Fever + Low O2 + High HR = Critical  
├─ Normal HR + Normal RR + Normal O2 = Stable
└─ And hundreds of other patterns

Now when new vital signs come in:
├─ Model recognizes: "This looks like Cases 1, 2, 5"
├─ Model predicts: "CRITICAL with 85% confidence"
└─ Result: Creates alert
```

---

## FLOWCHART 6: SYSTEM COMPONENTS & HOW THEY INTERACT

```
┌─────────────────────────────────────────────────────────────────┐
│                  COMPLETE SYSTEM DIAGRAM                        │
└─────────────────────────────────────────────────────────────────┘

1. USER INTERACTION
   ┌─────────────────┐
   │ CARE HOME STAFF │
   │  (Uses laptop)  │
   └────────┬────────┘
            │
            │ Opens web browser
            │ Goes to http://localhost:3000
            ↓
   ┌──────────────────────────────────┐
   │  NEXT.JS APPLICATION (Frontend)  │
   │  ├─ Page: /dashboard             │
   │  ├─ Component: AlertDashboard    │
   │  ├─ State: alerts[], loading     │
   │  ├─ Effects: Fetch every 30s     │
   │  └─ Port: 3000                   │
   └────────────┬─────────────────────┘
                │
                │ HTTP Requests
                │ (REST API)
                ↓
2. MIDDLE TIER
   ┌──────────────────────────────────┐
   │    DJANGO REST API (Backend)     │
   │                                  │
   │  Routes:                         │
   │  ├─ /api/alerts/active_alerts/  │
   │  ├─ /api/alerts/critical_alerts/│
   │  ├─ /api/alerts/{id}/acknowledge
   │  └─ /api/accounts/login/        │
   │                                  │
   │  Features:                       │
   │  ├─ Authentication (JWT)         │
   │  ├─ Serialization (Python→JSON) │
   │  ├─ Query DB                     │
   │  └─ Load ML model                │
   │                                  │
   │  Port: 8000                      │
   └────────────┬─────────────────────┘
                │
                │ Database queries
                │ & Signal triggers
                ↓
3. DATA LAYER
   ┌──────────────────────────────────┐
   │     SQLITE DATABASE              │
   │                                  │
   │  Tables:                         │
   │  ├─ patients (who)               │
   │  ├─ vitals (vital signs)         │
   │  ├─ alerts (alerts created)      │
   │  ├─ users (staff accounts)       │
   │  └─ other supporting tables      │
   │                                  │
   │  Signals (Auto-triggers):        │
   │  When vitals saved               │
   │  → post_save signal fires        │
   │  → auto_detect_deterioration()   │
   │  → Run ML model                  │
   │  → Create alert if critical      │
   │                                  │
   │  File: db.sqlite3                │
   └────────────┬─────────────────────┘
                │
                │ Triggers ML
                ↓
4. ML INTELLIGENCE
   ┌──────────────────────────────────┐
   │    MACHINE LEARNING MODEL        │
   │                                  │
   │  Input: Vital signs data         │
   │  {HR, RR, O2, BP, TEMP, ...}     │
   │                                  │
   │  Process:                        │
   │  ├─ Load model weights           │
   │  ├─ Normalize inputs             │
   │  ├─ Forward pass (compute)       │
   │  ├─ Get probability score        │
   │  └─ Interpret result             │
   │                                  │
   │  Output:                         │
   │  {                               │
   │    critical: True/False,         │
   │    probability: 0.0-1.0,         │
   │    alert_level: RED/AMBER/...   │
   │  }                               │
   │                                  │
   │  File: deterioration_model.pkl   │
   └──────────────────────────────────┘


INTERACTION EXAMPLE: Staff Creates Alert
═══════════════════════════════════════════════════════

Staff Action: Creates vital with HIGH readings

↓ Django receives vital data
  vital = VitalSigns(patient=John, hr=140, ...)
  vital.save()

↓ post_save signal fires (automatic!)
  signal: "New vital saved for John"

↓ Signal calls function
  auto_detect_deterioration(instance=vital)

↓ Function loads ML model
  detector = get_detector()

↓ Function extracts vital data
  vital_dict = {
    'heart_rate': 140,
    'respiratory_rate': 28,
    'oxygen_saturation': 88,
    ...
  }

↓ Model predicts
  result = detector.predict(vital_dict)
  result = {
    'is_critical': True,
    'probability': 0.85,
    'alert_level': 'RED'
  }

↓ Check result
  if result['is_critical']:
      # Create alert
      alert = DeteriorationAlert.objects.create(
        patient=John,
        priority='critical',
        trigger_reason=f"ML prediction: {result['alert_level']}"
      )

↓ Alert created in database
  Table: deterioration_alerts_alert
  Status: "active"

↓ Frontend polls every 30 seconds
  GET /api/alerts/active_alerts/

↓ Backend returns alerts
  [{id: 1, patient_name: "John", priority: "critical", ...}]

↓ Frontend updates state
  setAlerts([{...}])

↓ React re-renders
  Shows RED alert card on dashboard

↓ Staff sees alert and responds
  Clicks "Acknowledge"

↓ Alert status updated
  status: "acknowledged"

↓ Card disappears from view
  ✓ Process complete!
```

---

## SUMMARY: Use These Flowcharts to Explain

**Print/Save these flowcharts. When someone asks:**

1. **"How does the system work?"**
   → Show: FLOWCHART 1 (Complete Data Flow)

2. **"What are the different parts?"**
   → Show: FLOWCHART 2 (Architecture Layers)

3. **"How does it decide to create an alert?"**
   → Show: FLOWCHART 3 (Decision Making)

4. **"How is security handled?"**
   → Show: FLOWCHART 4 (Authentication)

5. **"How does the ML model work?"**
   → Show: FLOWCHART 5 (ML Prediction)

6. **"How do all the parts connect?"**
   → Show: FLOWCHART 6 (System Components)
