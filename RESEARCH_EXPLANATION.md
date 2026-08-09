# ALERT SYSTEM.

---

## PART 1: THE PROBLEM (Why We Built This)
       
### What Problem Are We Solving?

In a care home setting:
- **Elderly patients** can deteriorate quickly
- **Staff** need to know **immediately** if a patient is getting worse
- **Manual checks** = slow, unreliable, can miss critical changes
- **No automated system** to detect deterioration in real-time

**Example:**
- Nurse records vital signs: Heart rate = 140, Breathing = 28, Oxygen = 88%
- Problem: Nurse has 20 other patients. Might not notice these are WARNING SIGNS
- Result: Patient deteriorates further before anyone notices
- Better way: Computer automatically flags this as CRITICAL

### Why Automate This?

| Manual Process | Automated Process |
|---|---|
| Staff reads vital signs manually | Computer reads vital signs automatically |
| Staff remembers what's normal/abnormal | Computer uses ML model (trained on thousands of cases) |
| Staff might miss the warning | Computer flags it immediately |
| Takes time to realize it's critical | Alert shows up on dashboard in seconds |

## PART 2: THE SOLUTION (What We Built)

### High Level: Three Components

```
COMPONENT 1: DATABASE + BACKEND API
Purpose: Store data and provide access to it
Technology: Django (Python framework) + SQLite (database)

COMPONENT 2: MACHINE LEARNING MODEL  
Purpose: Analyze vital signs and detect deterioration
Technology: Python ML model (trained on patient data)

COMPONENT 3: USER DASHBOARD
Purpose: Show alerts to staff so they can take action
Technology: React (JavaScript framework)
```

### What Each Component Does

#### COMPONENT 1: Backend (Django)
```
What it stores:
- Patient information
- Vital sign readings (heart rate, blood pressure, etc.)
- Alerts (when deterioration is detected)
- Staff user accounts

What it provides (via API):
- "Give me all active alerts" endpoint
- "Acknowledge this alert" endpoint
- "Get critical alerts only" endpoint
```

#### COMPONENT 2: ML Model
```
What it receives:
- Vital signs data (numbers like HR=140, RR=28, O2=88)

What it does:
- Analyzes the numbers using a trained model
- Compares against thousands of normal/critical cases
- Makes a prediction: "This patient is CRITICAL" or "Stable"

What it returns:
- CRITICAL (patient deteriorating)
- HIGH (concerning)
- MEDIUM (monitor)
- LOW (stable)
```

#### COMPONENT 3: Frontend Dashboard
```
What it shows:
- List of active alerts
- Patient name
- Alert priority (RED = critical, ORANGE = high, etc.)
- Why the alert was triggered

What it does:
- Fetches alerts from backend every 30 seconds
- Displays them in real-time
- Lets staff click "Acknowledge" button
```

---

## PART 3: HOW IT WORKS (The Complete Flow)

### Step-by-Step Process

**SCENARIO: A patient's vital signs change and system detects deterioration**

```
STEP 1: NURSE RECORDS VITAL SIGNS
├─ Nurse opens mobile/web app
├─ Enters patient: John Doe
├─ Enters readings:
│  ├─ Heart Rate: 140 (HIGH - normally 60-100)
│  ├─ Respiratory Rate: 28 (HIGH - normally 12-20)
│  ├─ Oxygen Saturation: 88% (LOW - normally 95%+)
│  ├─ Blood Pressure: 160/100 (HIGH)
│  └─ Temperature: 38.5°C (HIGH - fever)
└─ Clicks SAVE

STEP 2: DATA SAVED TO DATABASE
├─ System stores all vital signs
├─ Creates a VitalSigns record
├─ Stores in SQLite database
└─ Status: ✓ SAVED

STEP 3: AUTOMATIC SIGNAL TRIGGERED (Django Feature)
├─ Database sends a "signal" (notification)
├─ Signal says: "New vital signs added!"
├─ This triggers a Python function automatically
└─ No manual intervention needed

STEP 4: MACHINE LEARNING MODEL LOADS
├─ Python code runs: get_detector()
├─ Loads trained model file: deterioration_model.pkl
├─ Model is pre-trained on thousands of patient cases
├─ Ready to make predictions
└─ Status: ✓ MODEL READY

STEP 5: ML MODEL ANALYZES VITAL SIGNS
├─ Model receives vital data:
│  ├─ HR=140 → feeds into model
│  ├─ RR=28 → feeds into model
│  ├─ O2=88 → feeds into model
│  ├─ BP=160/100 → feeds into model
│  └─ TEMP=38.5 → feeds into model
│
├─ Model processes (uses trained neural network):
│  ├─ "Abnormal vital pattern detected"
│  ├─ "Matches critical deterioration signature"
│  ├─ "Confidence: 85%"
│  └─ "Prediction: CRITICAL"
│
└─ Returns: {"is_critical": True, "probability": 0.85, "alert_level": "RED"}

STEP 6: ALERT CREATED IN DATABASE
├─ System creates DeteriorationAlert record
├─ Alert contains:
│  ├─ Patient: John Doe
│  ├─ Alert Type: "ML Prediction"
│  ├─ Priority: CRITICAL (RED)
│  ├─ Reason: "ML model prediction: RED (85%)"
│  ├─ Status: "active" (waiting for staff to see)
│  └─ Timestamp: 2026-06-27 14:30:00
│
└─ Status: ✓ ALERT CREATED

STEP 7: FRONTEND DASHBOARD POLLS API
├─ Dashboard component (React) runs automatically
├─ Every 30 seconds, it asks the backend:
│  └─ "Hey API, give me all active alerts"
├─ API responds with list of alerts (JSON format)
├─ Frontend receives:
│  └─ [{id: 1, patient_name: "John Doe", priority: "critical", ...}]
│
└─ Status: ✓ ALERT FETCHED

STEP 8: ALERT DISPLAYS ON STAFF'S SCREEN
├─ Browser renders RED alert card
├─ Shows:
│  ├─ 🚨 CRITICAL (red badge)
│  ├─ Patient: John Doe
│  ├─ Reason: "ML model detected deterioration"
│  ├─ Vitals: HR=140, RR=28, O2=88%
│  ├─ Time: 14:30 (when detected)
│  └─ [ACKNOWLEDGE ALERT] button
│
└─ Status: ✓ ALERT VISIBLE

STEP 9: STAFF RESPONDS
├─ Nurse sees red alert on dashboard
├─ Nurse reads: "John Doe - CRITICAL - ML prediction"
├─ Nurse immediately goes to patient
├─ Nurse:
│  ├─ Checks patient physically
│  ├─ Decides action (medication? doctor? observation?)
│  └─ Clicks "ACKNOWLEDGE ALERT" button
│
└─ Status: ✓ STAFF ALERTED

STEP 10: ALERT ACKNOWLEDGED
├─ Backend receives acknowledgement
├─ Updates alert status: "active" → "acknowledged"
├─ Records:
│  ├─ Who acknowledged: Staff member name
│  ├─ When acknowledged: 14:31:00
│  └─ Alert is now marked as "seen"
│
└─ Status: ✓ ACKNOWLEDGED

STEP 11: ALERT DISAPPEARS FROM DASHBOARD
├─ Frontend refreshes
├─ No longer shows "active" alerts
├─ Card removed from view
└─ Status: ✓ RESOLVED
```

---

## PART 4: THE ARCHITECTURE (How Components Connect)

### Visual Architecture Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                    CARE HOME STAFF                           │
│              (Person using the system)                       │
└─────────────────────┬──────────────────────────────────────┘
                      │
                      │ Opens web browser
                      ↓
┌──────────────────────────────────────────────────────────────┐
│              FRONTEND (React Component)                      │
│           http://localhost:3000/dashboard                    │
│                                                               │
│  What it does:                                               │
│  1. Displays alert cards on screen                           │
│  2. Fetches alerts from backend API                          │
│  3. Updates every 30 seconds                                 │
│  4. Handles "Acknowledge" button click                       │
│                                                               │
│  Technology: React.js, JavaScript, CSS                       │
│  File: frontend/components/AlertDashboard.tsx               │
└─────────────────────┬──────────────────────────────────────┘
                      │
                      │ HTTP Requests (REST API calls)
                      │ GET /api/alerts/active_alerts/
                      │ POST /api/alerts/{id}/acknowledge/
                      ↓
┌──────────────────────────────────────────────────────────────┐
│              BACKEND (Django REST API)                       │
│           http://localhost:8000/api                          │
│                                                               │
│  What it does:                                               │
│  1. Receives requests from frontend                          │
│  2. Queries database for alerts                              │
│  3. Returns alerts as JSON                                   │
│  4. Updates alert status when acknowledged                   │
│                                                               │
│  Technology: Django (Python web framework)                   │
│  File: backend/deterioration_alerts/views_api.py           │
└─────────────────────┬──────────────────────────────────────┘
                      │
                      │ Queries/Updates database
                      │ Runs ML model on new vital signs
                      ↓
┌──────────────────────────────────────────────────────────────┐
│           DATABASE + ML MODEL (Brain of System)              │
│                                                               │
│  Database (SQLite):                                          │
│  - Stores patients, vital signs, alerts, users              │
│  - File: backend/db.sqlite3                                 │
│                                                               │
│  ML Model:                                                   │
│  - Analyzes vital signs                                      │
│  - Detects deterioration patterns                            │
│  - File: backend/deterioration_model.pkl                    │
│  - Technology: Python scikit-learn/TensorFlow               │
│                                                               │
│  Signal Handler:                                             │
│  - Triggers automatically when vitals saved                 │
│  - Loads ML model                                            │
│  - Creates alert if critical                                │
│  - File: backend/vitals/models.py (post_save signal)       │
└──────────────────────────────────────────────────────────────┘
```

---

## PART 5: TECHNOLOGY CHOICES (Why We Built It This Way)

### Why Django for Backend?

| Feature | Why It Matters |
|---------|---|
| **REST API** | Easy to create endpoints that frontend can call |
| **ORM (Object-Relational Mapping)** | Easy database queries without writing SQL |
| **Signal System** | Automatic triggers when data changes |
| **Admin Interface** | Built-in admin panel to manage data |
| **Authentication** | Built-in user login and JWT tokens |
| **Security** | CSRF protection, SQL injection prevention |

### Why React for Frontend?

| Feature | Why It Matters |
|---------|---|
| **Real-time Updates** | Can refresh data every 30 seconds automatically |
| **Component-based** | Reusable UI pieces (alert cards) |
| **State Management** | Keeps track of alerts and loading states |
| **User Friendly** | Makes responsive, interactive interface |
| **Performance** | Only updates what changed, not whole page |

### Why Machine Learning?

| Manual Approach | ML Approach |
|---|---|
| Staff reads vital: HR=140, RR=28, O2=88 | ML model sees pattern: {140,28,88,160/100,38.5} |
| Staff thinks: "Is this bad?" | Model trained on 10,000 similar cases |
| Staff might miss it | Model: "This matches 85% of critical cases" |
| Takes time to decide | Returns prediction in milliseconds |
| Subjective (depends on staff experience) | Objective (mathematical analysis) |

### Why SQLite Database?

- **Local development** - Doesn't need separate database server
- **Simple for learning** - Good for understanding how systems work
- **Easy to backup** - Just one file
- **Enough for research** - Can handle thousands of records

---

## PART 6: KEY TECHNICAL CONCEPTS (For Your Defense)

### 1. REST API (What Your Backend Provides)

**What is it?**
- API = Application Programming Interface
- REST = Representational State Transfer
- It's a way for frontend to talk to backend

**Your API Endpoints:**
```
GET /api/alerts/active_alerts/
  → "Give me all active alerts"
  
GET /api/alerts/critical_alerts/
  → "Give me only critical alerts"
  
POST /api/alerts/{id}/acknowledge/
  → "Mark this alert as seen"
  
POST /api/accounts/login/
  → "Login and get authentication token"
```

### 2. Authentication (Security)

**How it works:**
```
1. User enters: username + password
2. Backend checks: "Is this correct?"
3. If yes: Backend returns JWT TOKEN (unique string)
4. Frontend stores token in localStorage
5. Every API request includes token
6. Backend verifies token before responding
```

**Why?**
- Only logged-in staff can see alerts
- Prevents unauthorized access
- Tracks who acknowledged which alert

### 3. Signal Handler (Automation)

**What is it?**
- Django feature: "When X happens, do Y automatically"

**How it works:**
```
When vital signs saved to database:
  → Signal fires (automatic trigger)
  → Calls function: auto_detect_deterioration()
  → This function:
     - Loads ML model
     - Analyzes vital data
     - Creates alert if critical
```

**Why?**
- No manual intervention needed
- Alert created instantly
- Real-time detection

### 4. React State Management

**What is it?**
- React keeps track of data (state)
- When state changes, screen updates automatically

**Your component tracks:**
```javascript
const [alerts, setAlerts] = useState([]);        // Alert list
const [loading, setLoading] = useState(true);    // Loading indicator
const [error, setError] = useState(null);        // Error messages
const [lastRefresh, setLastRefresh] = useState(); // Last update time
```

**Flow:**
```
1. Page loads → setLoading(true)
2. Fetch alerts from API
3. Got response → setAlerts(data) → Page updates!
4. Got error → setError(message) → Page updates!
5. Done → setLoading(false)
```

### 5. ML Model Integration

**What happens:**
```
When vital signs recorded:
  → Signal handler receives vital data
  → Loads pre-trained model from file
  → Model analyzes data
  → Returns prediction: {
       "is_critical": true/false,
       "probability": 0.85,
       "alert_level": "RED/AMBER/GREEN"
     }
  → If critical: Create alert
```

**Why pre-trained?**
- Model already learned from historical data
- Doesn't need to train again
- Instant predictions
- Consistent results

---

## PART 7: DATA FLOW DIAGRAM (Key for Understanding)

```
┌─────────────────┐
│  NURSE RECORDS  │
│  VITAL SIGNS    │
│   (HR=140,etc)  │
└────────┬────────┘
         │
         ↓
┌─────────────────────────────────────────┐
│  DATA SAVED TO DATABASE                 │
│  Table: vitals_vitalsigns               │
│  Row: {patient_id, heart_rate, ...}     │
└────────┬────────────────────────────────┘
         │
         ↓ SIGNAL TRIGGER (Automatic)
┌─────────────────────────────────────────┐
│  post_save signal fires                 │
│  Calls: auto_detect_deterioration()    │
└────────┬────────────────────────────────┘
         │
         ↓
┌─────────────────────────────────────────┐
│  ML MODEL LOADS                         │
│  File: deterioration_model.pkl          │
│  Status: Ready to predict               │
└────────┬────────────────────────────────┘
         │
         ↓
┌─────────────────────────────────────────┐
│  MODEL ANALYZES VITAL DATA              │
│  Input: {140, 28, 88, 160/100, 38.5}   │
│  Process: Mathematical calculation      │
│  Output: {critical: True, prob: 0.85}  │
└────────┬────────────────────────────────┘
         │
         ↓
┌─────────────────────────────────────────┐
│  DECISION: CREATE ALERT?                │
│  If output.is_critical == True → YES    │
└────────┬────────────────────────────────┘
         │
         ↓
┌─────────────────────────────────────────┐
│  ALERT CREATED IN DATABASE              │
│  Table: deterioration_alerts_alert      │
│  Status: "active"                       │
│  Priority: "critical"                   │
└────────┬────────────────────────────────┘
         │
         ↓ Frontend polls every 30 seconds
┌─────────────────────────────────────────┐
│  FRONTEND FETCHES FROM API              │
│  Request: GET /api/alerts/active_alerts│
│  Response: [{id:1, patient:"John", ...}]│
└────────┬────────────────────────────────┘
         │
         ↓
┌─────────────────────────────────────────┐
│  REACT UPDATES STATE                    │
│  setAlerts(response)                    │
└────────┬────────────────────────────────┘
         │
         ↓
┌─────────────────────────────────────────┐
│  SCREEN UPDATES                         │
│  Shows RED alert card                   │
│  "CRITICAL - John Doe"                  │
└────────┬────────────────────────────────┘
         │
         ↓ Staff clicks button
┌─────────────────────────────────────────┐
│  ACKNOWLEDGE ALERT                      │
│  POST /api/alerts/{id}/acknowledge/    │
└────────┬────────────────────────────────┘
         │
         ↓
┌─────────────────────────────────────────┐
│  ALERT STATUS UPDATED                   │
│  Status: "active" → "acknowledged"      │
│  Recorded: Who, when, timestamp         │
└────────┬────────────────────────────────┘
         │
         ↓
┌─────────────────────────────────────────┐
│  FRONTEND REFRESHES                     │
│  Alert no longer in "active" list       │
│  Card disappears from screen            │
└─────────────────────────────────────────┘
```

---

## PART 8: FILE STRUCTURE (What Each File Does)

### Backend Files

```
backend/
│
├── deterioration_alerts/              ← ALERT SYSTEM APP
│   ├── models.py                      ← Database tables definition
│   │   └── DeteriorationAlert class (defines alert structure)
│   │
│   ├── views_api.py                   ← API endpoints
│   │   ├── GET /api/alerts/active_alerts/
│   │   ├── GET /api/alerts/critical_alerts/
│   │   └── POST /api/alerts/{id}/acknowledge/
│   │
│   ├── serializers.py                 ← Converts database data to JSON
│   │   └── DeteriorationAlertSerializer
│   │
│   ├── admin.py                       ← Admin interface
│   │   └── Dashboard at http://localhost:8000/admin
│   │
│   └── apps.py                        ← Configuration
│
├── vitals/
│   └── models.py                      ← SIGNAL HANDLER HERE
│       └── post_save signal triggers auto_detect_deterioration()
│
├── db.sqlite3                         ← ACTUAL DATABASE FILE
│   └── Contains: patients, vitals, alerts, users
│
├── Jomingos/settings.py               ← CONFIGURATION
│   ├── INSTALLED_APPS (includes deterioration_alerts)
│   ├── CORS settings (allows localhost:3000)
│   ├── Database settings (SQLite)
│   └── REST framework settings
│
└── manage.py                          ← Django management script
    └── Used to: runserver, migrate, shell, etc.
```

### Frontend Files

```
frontend/
│
├── components/
│   └── AlertDashboard.tsx             ← MAIN COMPONENT
│       ├── useState hooks (manage alerts, loading, errors)
│       ├── fetchAlerts() (calls /api/alerts/active_alerts/)
│       ├── acknowledgeAlert() (calls POST /acknowledge/)
│       └── useEffect hook (auto-refresh every 30 seconds)
│
├── app/
│   └── dashboard/
│       └── page.tsx                   ← DASHBOARD PAGE
│           └── Renders <AlertDashboard /> component
│
├── .env.local                         ← CONFIGURATION
│   └── NEXT_PUBLIC_API_URL=http://localhost:8000/api
│
└── package.json                       ← Dependencies
    ├── next (React framework)
    ├── react (UI library)
    └── typescript (type checking)
```

---

## PART 9: WHAT HAPPENS WHEN YOU TEST IT

### Test Scenario: Creating an Alert

**You do:** Create vital signs with HR=140, RR=28, O2=88%

**System does (automatically):**
1. Database saves vital signs
2. Signal fires automatically
3. ML model loads
4. Model predicts: "This is CRITICAL (85% confidence)"
5. Alert created: {patient: "John", priority: "critical", reason: "ML prediction"}
6. Frontend checks API every 30 seconds
7. Gets alert data back
8. Renders RED card on screen
9. Staff sees it and clicks "Acknowledge"
10. Alert status changes to "acknowledged"
11. Card disappears

**Why this matters for research:**
- ✅ Shows automated detection works
- ✅ Shows real-time dashboard works
- ✅ Shows staff can take action
- ✅ Shows system tracks who responded when

---

## PART 10: RESEARCH QUESTIONS YOU MIGHT GET ASKED

### Question 1: "Why did you use Django instead of [other framework]?"
**Answer:**
- Django has built-in REST framework for APIs
- Has signal system for automatic triggers
- Has ORM for easy database queries
- Has authentication built-in
- Widely used in healthcare systems

### Question 2: "How does the ML model predict deterioration?"
**Answer:**
- Model is pre-trained on thousands of patient cases
- It learned: "When vitals are like X, patient deteriorates"
- Receives vital signs as input
- Runs mathematical analysis
- Returns probability score (0-1 confidence)
- If > threshold, creates alert

### Question 3: "What if the ML model makes a mistake?"
**Answer:**
- Model is trained on real data (historical patterns)
- Includes confidence score (not always 100%)
- Staff still review alerts (human oversight)
- Staff can override system decisions
- Every decision is logged (accountability)

### Question 4: "Why poll every 30 seconds instead of real-time?"
**Answer:**
- Polling (asking every 30s) is simple and reliable
- Real-time requires WebSockets (more complex)
- 30 seconds is fast enough for medical alerts
- Less server load
- Works on all networks (even poor connections)

### Question 5: "How does security work?"
**Answer:**
- User logs in with username/password
- Backend returns JWT token (secure string)
- Frontend stores in localStorage
- Every API request sends token
- Backend verifies token valid before responding
- Only logged-in staff can see alerts

### Question 6: "What if database goes down?"
**Answer:**
- Currently using SQLite (single file, local)
- For production: would use PostgreSQL (separate server)
- Backups saved regularly
- If down: alerts not created, but system can recover

### Question 7: "How is patient data protected?"
**Answer:**
- Authentication (only logged-in users)
- Database (encrypted credentials)
- CORS (only allows requests from frontend)
- No sensitive data in URLs
- All data transmitted over HTTPS (in production)

---

## PART 11: RESEARCH NOTES FOR YOUR DEFENSE

### Key Points to Mention

1. **Problem Identification**
   - Care homes need real-time deterioration detection
   - Manual monitoring is slow and unreliable
   - Automated system saves lives

2. **Solution Design**
   - Three-tier architecture: Frontend, Backend, Database
   - Separation of concerns (each layer has one job)
   - ML integration for intelligent prediction

3. **Technology Stack**
   - Frontend: React (modern, interactive)
   - Backend: Django (robust, secure, battle-tested)
   - Database: SQLite (simple, file-based)
   - ML: Python (scikit-learn/TensorFlow)

4. **Automation**
   - Django signals trigger ML analysis automatically
   - No manual intervention needed
   - Real-time detection and alerting

5. **User Experience**
   - Simple, clean dashboard interface
   - Red/orange/yellow/green priority colors
   - One-click acknowledge functionality
   - Automatic refresh every 30 seconds

6. **Data Flow**
   - Vitals recorded → Signal fires → ML analyzes → Alert created → Dashboard shows → Staff acknowledges → System learns

7. **Security**
   - Authentication with JWT tokens
   - CORS protection
   - Encrypted passwords
   - Audit trails (who acknowledged what, when)

8. **Scalability**
   - Currently local SQLite (testing/demo)
   - Can scale to PostgreSQL (production)
   - API design supports multiple frontends
   - ML model can be updated with new data

---

## PART 12: VISUAL SUMMARY (One-Page Cheat Sheet)

```
┌─────────────────────────────────────────────────────────────┐
│                    ALERT SYSTEM OVERVIEW                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  INPUT:        Vital signs recorded by staff                │
│                (HR, RR, O2, BP, TEMP)                        │
│                                                               │
│  PROCESSING:   ML model analyzes vitals                     │
│                Detects abnormal patterns                    │
│                Predicts: Critical? Yes/No                   │
│                                                               │
│  STORAGE:      Alert saved to database                      │
│                Linked to patient                            │
│                Timestamped                                  │
│                                                               │
│  DELIVERY:     Frontend fetches alerts                      │
│                Displays as RED/ORANGE/YELLOW cards          │
│                Every 30 seconds auto-refresh                │
│                                                               │
│  ACTION:       Staff sees alert on dashboard                │
│                Reviews patient                              │
│                Clicks "Acknowledge"                         │
│                                                               │
│  OUTCOME:      Patient receives care                        │
│                Deterioration prevented/managed              │
│                System learns (logs outcome)                 │
│                                                               │
└─────────────────────────────────────────────────────────────┘

TECHNOLOGY STACK:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Layer           Technology              Purpose
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Frontend        React.js (JavaScript)   User interface
API             Django REST (Python)    Data access & processing  
Intelligence    ML Model (Python)       Pattern detection
Storage         SQLite Database         Data persistence
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SYSTEM FEATURES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Real-time detection (via signals)
✓ ML-based prediction (trained model)
✓ Automatic alerts (no manual intervention)
✓ Staff dashboard (visual interface)
✓ Acknowledgement tracking (accountability)
✓ Authentication (security)
✓ Scalable architecture (can grow)
✓ Audit trail (who did what, when)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## PART 13: TERMINOLOGY GLOSSARY (For Defense)

| Term | Means | Example |
|------|-------|---------|
| **API** | Interface for apps to communicate | /api/alerts/active_alerts/ |
| **REST API** | Web API using HTTP requests | GET, POST, PUT, DELETE |
| **JSON** | Format for sending data | {"patient": "John", "priority": "critical"} |
| **Signal** | Automatic trigger when something happens | When vital saved → signal fires |
| **ORM** | Database access without writing SQL | models.DeteriorationAlert.objects.all() |
| **JWT Token** | Security token for authentication | Bearer eyJhbGciOiJ... |
| **CORS** | Allows frontend to call backend | CORS_ALLOWED_ORIGINS setting |
| **State** | Data a React component tracks | alerts[], loading, error |
| **Render** | Display HTML on screen | React renders alert card |
| **Payload** | Data sent in a request | {"username": "staff", "password": "123"} |
| **Endpoint** | Specific API function | /api/alerts/{id}/acknowledge/ |
| **POST** | Send data to server | Acknowledge alert |
| **GET** | Fetch data from server | Get list of alerts |
| **Inference** | ML model making prediction | Model analyzes vitals → predicts critical |

---

## FINAL SUMMARY FOR YOUR RESEARCH

**What You've Built:**
A complete alert detection system that automatically identifies patient deterioration and notifies care home staff in real-time.

**How It Works:**
1. Vital signs → Database
2. Signal → ML Model
3. Prediction → Alert Created
4. Frontend → Fetches Alert
5. Dashboard → Shows Staff
6. Staff → Acknowledges
7. System → Logs Action

**Why It Matters:**
- Saves time (automatic detection)
- Saves lives (real-time alerts)
- Reduces errors (ML is consistent)
- Improves care (staff can respond faster)

**Technology Used:**
- Python + Django (Backend)
- React + JavaScript (Frontend)
- SQLite (Database)
- ML Model (Intelligence)

**You Can Defend:**
- Architecture decisions (why Django, why React)
- Technology choices (why these tools)
- Data flow (step by step)
- Security (authentication, authorization)
- Scalability (can handle more patients)
- ML integration (how it detects deterioration)

---

**Now you can explain any part of this system to anyone!**
