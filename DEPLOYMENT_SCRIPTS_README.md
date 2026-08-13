# Deployment Scripts for Vital Signs Forecasting System

Complete orchestration tooling for deploying the vital signs forecasting system across care home units. Supports phased rollout from Wave 1 pilot (4 patients) through Wave 2 expansion (50-100 patients, 3-4 units) to full organizational deployment.

**Status:** Production-ready | **Last Updated:** 2026-08-13

---

## Quick Start

### Prerequisites

- Django 3.2+
- Python 3.8+
- PostgreSQL 12+
- Database migrations applied (`python manage.py migrate`)
- Patient and vital signs data loaded

### Health Check (Always Do This First)

```bash
python manage.py health_check
```

Expected output: `[OK] READY FOR PRODUCTION DEPLOYMENT` with 90+ health score.

---

## Deployment Scripts Overview

### 1. Health Check CLI (`health_check.py`)

**Quick system status verification** — No side effects, read-only.

```bash
# Basic check
python manage.py health_check

# Machine-readable JSON output
python manage.py health_check --json

# Wave 1 pilot status only
python manage.py health_check --wave1

# Wave 2 expansion readiness
python manage.py health_check --wave2
```

**Output:**
- Health score (0-100)
- Component status breakdown
- Critical failures and warnings
- Deployment readiness assessment

**Health Score Thresholds:**
- `90+`: HEALTHY — Ready for production
- `70-89`: DEGRADED — Proceed with caution
- `50-69`: CRITICAL — Address issues first
- `<50`: OFFLINE — System down

**Example:**
```
[OK] Status: HEALTHY
Health Score: 100/100
[OK] Database Connectivity — PostgreSQL responding
[OK] Wave 1 Pilot Patients — 4/4 pilot patients found
[OK] READY FOR PRODUCTION DEPLOYMENT
```

---

### 2. Wave 1 Pilot Activation (`activate_wave1_pilot.py`)

**Deploy the pilot with 4 high-confidence patients.** Creates initial forecasts, trains models, and arms monitoring.

```bash
# Production deployment
python manage.py activate_wave1_pilot

# Simulate without making changes
python manage.py activate_wave1_pilot --dry-run

# Skip model training (reuse existing models)
python manage.py activate_wave1_pilot --skip-training

# Export JSON report
python manage.py activate_wave1_pilot --report
```

**What it does:**
1. ✓ Verifies system readiness (database, models, alerts)
2. ✓ Loads 4 pilot patients (Richard Anderson, James Brown, Michael Brown, James Wilson)
3. ✓ Trains 32 forecasting models (8 vital types × 4 patients)
4. ✓ Generates 28 initial 24-hour forecasts
5. ✓ Initializes monitoring dashboard
6. ✓ Arms alert system with response SLA
7. ✓ Creates immutable audit trail
8. ✓ Verifies all systems operational

**Pilot Patients (High Confidence 84-93%):**
- Richard Anderson (93% confidence)
- James Brown (92% confidence)
- Michael Brown (90% confidence)
- James Wilson (84% confidence)

**Example Output:**
```
WAVE 1 PILOT ACTIVATION & DEPLOYMENT
======================================================================
STEP 1: SYSTEM READINESS CHECK
  [OK] All system checks passed

STEP 2: PILOT PATIENT VERIFICATION
  [OK] Richard Anderson (291 vitals, 93% conf)
  [OK] James Brown (241 vitals, 92% conf)
  [OK] Michael Brown (260 vitals, 90% conf)
  [OK] James Wilson (45 vitals, 84% conf)

[... 7 more steps ...]

Status: [OK] ACTIVATION COMPLETE
Pilot Patients: 4/4
Models Trained: 32
Forecasts Generated: 28
Alerts Armed: 4
[OK] Wave 1 pilot is ready for live operations
Decision Point: 2026-08-27
```

**Timeline:**
- Go-live: 2026-08-13
- Monitoring period: 14 days
- Success criteria review: 2026-08-27
- Decision: GO/NO-GO to Wave 2

---

### 3. Wave 2 Expansion Activation (`activate_wave2_expansion.py`)

**Scale from 4 to 50-100 patients across 3-4 units.** Supports phased unit-by-unit activation.

```bash
# Deploy all units (Unit 1 carryover + Units 2-4)
python manage.py activate_wave2_expansion

# Activate specific unit
python manage.py activate_wave2_expansion --unit=2
python manage.py activate_wave2_expansion --unit=3
python manage.py activate_wave2_expansion --unit=4

# Simulate without making changes
python manage.py activate_wave2_expansion --dry-run

# Skip model training
python manage.py activate_wave2_expansion --skip-training

# Export comprehensive report
python manage.py activate_wave2_expansion --report
```

**What it does:**
1. ✓ Verifies Wave 1 success criteria (accuracy ≥80%, safety ≥85/100)
2. ✓ Validates infrastructure scaling (database, network, alerts at 4x load)
3. ✓ Loads 50-100 patients across 3-4 units
4. ✓ Stratifies by confidence level (HIGH/MED-HIGH/MEDIUM/MED-LOW)
5. ✓ Trains 80+ models across all vital types
6. ✓ Generates 150+ forecasts for entire cohort
7. ✓ Configures unit-specific dashboards
8. ✓ Sets confidence-aware alert thresholds
9. ✓ Verifies operational readiness
10. ✓ Creates Wave 2 deployment audit trail

**Unit Deployment Plan:**

| Unit | Patients | Confidence Levels | Staffing | Training |
|------|----------|-------------------|----------|----------|
| Unit 1 | 4 | HIGH (90%+) | Existing | N/A |
| Unit 2 | 15-20 | MED-HIGH (80-85%), MEDIUM (70-80%) | 4 nurses + charge | 4 hours |
| Unit 3 | 15-20 | MED-HIGH (80-85%), MEDIUM (70-80%) | 3 nurses + coordinator | 4 hours |
| Unit 4 | 15-20 | MEDIUM (70-80%), MED-LOW (60-70%) | TBD | 4 hours |

**Patient Stratification:**

```
Wave 2 Confidence Distribution:
  HIGH (85%+):        8 patients — Standard monitoring
  MED-HIGH (80-85%): 12 patients — Standard monitoring
  MEDIUM (70-80%):   19 patients — Manual review recommended
  MED-LOW (60-70%):  10 patients — Mandatory manual review
```

**Alert Configuration by Confidence:**

```
HIGH (85%+):
  - Channels: Dashboard + Email
  - Response SLA: 5 minutes
  - Escalation: Level 2

MED-HIGH (80-85%):
  - Channels: Dashboard + Email
  - Response SLA: 10 minutes
  - Escalation: Level 2

MEDIUM (70-80%):
  - Channels: Dashboard only
  - Response SLA: 15 minutes
  - Note: Manual review recommended

MED-LOW (60-70%):
  - Channels: Dashboard only
  - Response SLA: 20 minutes
  - Note: Mandatory manual review before action
```

**Example Output:**
```
WAVE 2 EXPANSION ACTIVATION & DEPLOYMENT
======================================================================
STEP 2: PATIENT COHORT LOADING & STRATIFICATION
  [OK] Unit 1 (carryover): 4 HIGH confidence patients
  [OK] Unit2: 15 patients loaded (confidence: 70-85%)
  [OK] Unit3: 15 patients loaded (confidence: 68-82%)
  [OK] Unit4: 15 patients loaded (confidence: 60-80%)

Status: [OK] ACTIVATION COMPLETE
Units Activated: Unit1, Unit2, Unit3, Unit4
Total Patients: 49
  HIGH (85%+): 8
  MED-HIGH (80-85%): 12
  MEDIUM (70-80%): 19
  MED-LOW (60-70%): 10
Models Trained: 80
Forecasts Generated: 154
Dashboards Configured: 4
Alert Thresholds Set: 49
[OK] Wave 2 expansion ready for go-live 2026-08-28
```

**Phased Rollout Example:**

```bash
# Day 1: Unit 2 activation (15 patients)
python manage.py activate_wave2_expansion --unit=2
# Result: 19 patients total (Unit 1 + Unit 2)

# Day 2: Monitor Unit 2, verify stability
python manage.py health_check --wave2

# Day 3: Unit 3 activation (15 patients)
python manage.py activate_wave2_expansion --unit=3
# Result: 34 patients total (Units 1-3)

# Day 5: Unit 4 activation (15 patients, optional)
python manage.py activate_wave2_expansion --unit=4
# Result: 49 patients total (all units)
```

**Timeline:**
- Go-live: 2026-08-28
- Monitoring period: 14 days (Aug 28 - Sep 10)
- Daily metrics review
- Success criteria review: 2026-09-10
- Decision: GO/NO-GO to Wave 3

---

## Usage Patterns

### Pre-Deployment Checklist

```bash
# 1. Verify system health
python manage.py health_check
# Expected: 90+ score, all critical systems [OK]

# 2. Verify patient data
python manage.py manage.py wave1_pilot_monitoring --date=2026-08-13
# Expected: All 4 patients present with sufficient vital signs

# 3. Run dry-run activation
python manage.py activate_wave1_pilot --dry-run
# Expected: All steps simulate without errors
```

### Deployment Sequence (Wave 1)

```bash
# 1. Final health check
python manage.py health_check --wave1
# Required: Score ≥90, all systems [OK]

# 2. Deploy with production mode
python manage.py activate_wave1_pilot
# Creates database records, arms monitoring

# 3. Verify deployment
python manage.py health_check --wave1
# Expected: Still 100/100 score

# 4. Generate deployment report
python manage.py activate_wave1_pilot --report
# Produces: wave1_activation_report_YYYYMMDD_HHMMSS.json
```

### Deployment Sequence (Wave 2 - Phased)

```bash
# Pre-deployment
python manage.py health_check --wave2
# Required: Score ≥70

# Day 1: Unit 2
python manage.py activate_wave2_expansion --unit=2 --dry-run
python manage.py activate_wave2_expansion --unit=2
python manage.py activate_wave2_expansion --unit=2 --report

# Day 2: Monitoring & verification
python manage.py health_check --wave2
python manage.py wave1_pilot_monitoring          # Unit 1 status

# Day 3: Unit 3
python manage.py activate_wave2_expansion --unit=3
python manage.py activate_wave2_expansion --unit=3 --report

# Day 5: Unit 4 (if Unit 2-3 stable)
python manage.py activate_wave2_expansion --unit=4
python manage.py activate_wave2_expansion --unit=4 --report
```

---

## Options Reference

### Common Flags

| Flag | Purpose | Example |
|------|---------|---------|
| `--dry-run` | Simulate without persisting changes | `activate_wave1_pilot --dry-run` |
| `--skip-training` | Skip model training, reuse existing | `activate_wave2_expansion --skip-training` |
| `--report` | Export JSON report | `activate_wave1_pilot --report` |
| `--json` | Output as JSON (health_check only) | `health_check --json` |
| `--unit=N` | Target specific unit (Wave 2 only) | `activate_wave2_expansion --unit=2` |
| `--wave1` | Check Wave 1 status only | `health_check --wave1` |
| `--wave2` | Check Wave 2 readiness only | `health_check --wave2` |

---

## Success Criteria & Gates

### Wave 1 Success (Go/No-Go Decision 2026-08-27)

**GO Criteria (all required):**
- ✓ System uptime: >99%
- ✓ Forecast accuracy: ≥80% within 95% PI
- ✓ Safety score: ≥85/100
- ✓ Zero patient safety incidents
- ✓ Clinician satisfaction: ≥80%
- ✓ Operational procedures: Tested and working

**CONDITIONAL GO:**
- ⚠ Uptime 95-99% (acceptable with monitoring)
- ⚠ Accuracy 75-80% (acceptable with threshold adjustments)
- ⚠ Safety score 75-85/100 (acceptable range)

**NO-GO Criteria (stop and iterate):**
- ✗ Uptime <95%
- ✗ Accuracy <75%
- ✗ Safety score <75/100
- ✗ Any patient safety incident
- ✗ Clinician satisfaction <60%

### Wave 2 Success (Go/No-Go Decision 2026-09-10)

**GO Criteria (all required):**
- ✓ All 4 units achieving ≥99% uptime
- ✓ Accuracy ≥80% across all confidence levels
- ✓ Safety score ≥85/100
- ✓ Zero patient safety incidents
- ✓ ≥80% clinician satisfaction in all units
- ✓ Operational procedures stable

**Action:** Proceed to Wave 3 planning (full organization)

**CONDITIONAL GO:**
- ⚠ Units 1-3 stable, Unit 4 problematic
- ⚠ Accuracy 75-80%
- ⚠ Safety score 75-85/100

**Action:** Continue Wave 2, retry Unit 4 or pause; re-assess in 1 week

**NO-GO Criteria:**
- ✗ Accuracy <75% across units
- ✗ Safety score <75/100
- ✗ Patient safety incident occurred
- ✗ Operational procedures failing

**Action:** Return to Wave 1 scope, identify root cause, iterate

---

## Monitoring & Verification

### Daily Monitoring (Wave 1 & 2)

```bash
# Morning check (before 08:00)
python manage.py health_check

# 24-hour metrics review (20:00)
python manage.py wave1_pilot_monitoring

# Check Wave 2 status (if deployed)
python manage.py health_check --wave2
```

### Weekly Review

```bash
# Friday 18:00: Comprehensive review
python manage.py health_check --json > health_report_$(date +%Y%m%d).json
python manage.py activate_wave2_expansion --report  # if Wave 2 active
```

### Alert Configuration Verification

```bash
# Verify alert thresholds are set per confidence level
python manage.py health_check --json | grep -i alert

# Expected: 4 alert thresholds configured (1 per unit)
# For Wave 2: 49 alert thresholds set (1 per patient)
```

---

## Troubleshooting

### Health Check Shows CRITICAL Score

```bash
# 1. Check specific component
python manage.py health_check --json

# 2. Identify critical failures (look for "status": false)
# 3. Address the failed component

# Example: Database connectivity
# - Verify PostgreSQL is running
# - Check connection string in settings
# - Verify network access
```

### Model Training Fails

```bash
# 1. Verify patient has sufficient data
python manage.py manage.py wave1_pilot_monitoring

# Expected: Each patient has 10+ vital signs

# 2. Run with --skip-training
python manage.py activate_wave1_pilot --skip-training

# 3. Check logs for specific error
tail -f logs/django.log | grep -i "model training"
```

### Forecast Generation Issues

```bash
# 1. Verify vital signs data exists
python manage.py health_check

# Expected: "Recent Vital Signs (24h)" shows [OK]

# 2. Check alert system
python manage.py health_check --json | grep -i alert

# 3. Manually verify forecast creation
python manage.py validate_forecasts
```

### Unit-Specific Activation Fails

```bash
# 1. Run unit health check
python manage.py health_check --wave2

# 2. Run dry-run first
python manage.py activate_wave2_expansion --unit=2 --dry-run

# 3. Check for patient loading issues
# - Verify unit patients exist in database
# - Confirm vital signs data present
# - Check confidence scores assigned
```

---

## Safety & Rollback

### Safety First

All activation scripts are **read-safe** when used with `--dry-run`:

```bash
# Always simulate first
python manage.py activate_wave1_pilot --dry-run

# Review output, then deploy
python manage.py activate_wave1_pilot
```

### Idempotency

Activation scripts can be **run multiple times safely**:
- Database constraints prevent duplicate forecasts
- Existing models are reused if `--skip-training` is used
- No data is deleted or overwritten

### Rollback Procedure

If deployment fails:

```bash
# 1. Stop all patient monitoring
# - Set forecasting to manual-only mode
# - Disable automated alerts
# - Notify clinical team

# 2. Identify root cause
python manage.py health_check --json > health_report.json
tail -f logs/django.log

# 3. Fix underlying issue
# - Database query performance?
# - Missing vital signs?
# - Model training error?

# 4. Test fix with dry-run
python manage.py activate_wave1_pilot --dry-run

# 5. Resume deployment
python manage.py activate_wave1_pilot
```

---

## Data Retention & Cleanup

### Archive Strategy

Wave 2 plan includes **1-year rolling retention**:
- Daily backups scheduled
- Recovery time: <4 hours
- Retention: 365 days
- Archive after: Manual export

```bash
# Backup current deployment state
python manage.py dumpdata vitals.PatientForecast > forecasts_backup_$(date +%Y%m%d).json
python manage.py dumpdata vitals.VitalSigns > vitals_backup_$(date +%Y%m%d).json
```

---

## Audit Trail

All deployments create immutable audit trails:

```json
{
  "deployment_id": "WAVE1-PILOT-001",
  "timestamp": "2026-08-13T09:00:00Z",
  "patients": [1, 2, 3, 4],
  "action": "activate_wave1_pilot",
  "status": "production",
  "operator": "system",
  "checksum": "SHA256-audit-trail-secured"
}
```

Find audit entries in logs:
```bash
grep -r "deployment_id" logs/
```

---

## Performance Expectations

### Wave 1 (4 patients)
- Activation time: 2-5 minutes
- Model training: 1-2 minutes
- Forecast generation: <1 minute
- Total readiness: <10 minutes

### Wave 2 (50-100 patients)
- Activation time: 10-15 minutes (full) or 3-5 minutes per unit
- Model training: 5-10 minutes
- Forecast generation: 2-3 minutes
- Total readiness: <30 minutes

---

## Getting Help

### Check Script Help

```bash
python manage.py activate_wave1_pilot --help
python manage.py activate_wave2_expansion --help
python manage.py health_check --help
```

### Review Deployment Documentation

- **Wave 1 Plan:** [WAVE1_PILOT_DEPLOYMENT_PLAN.md](./WAVE1_PILOT_DEPLOYMENT_PLAN.md)
- **Wave 2 Plan:** [WAVE2_EXPANSION_PLAN.md](./WAVE2_EXPANSION_PLAN.md)
- **Project Dashboard:** [PROJECT_STATUS_DASHBOARD.html](./PROJECT_STATUS_DASHBOARD.html)

### Monitor Logs

```bash
# Real-time log streaming
tail -f logs/django.log | grep -E "(health|activation|forecast|alert)"

# Search for errors
grep -i "error\|fail\|critical" logs/django.log

# Count deployment steps
grep -c "STEP" logs/django.log
```

---

## Summary

| Script | Purpose | Patients | Scope | Status |
|--------|---------|----------|-------|--------|
| `health_check` | Quick status verification | N/A | All | ✅ Ready |
| `activate_wave1_pilot` | Deploy pilot | 4 | 1 unit | ✅ Go-live 2026-08-13 |
| `activate_wave2_expansion` | Scale to 50-100 | 50-100 | 3-4 units | ✅ Ready for 2026-08-28 |

**Next Steps:**
1. Run `health_check` to verify system readiness
2. Deploy Wave 1 with `activate_wave1_pilot`
3. Monitor for 14 days (Aug 13-27)
4. Review success criteria
5. Deploy Wave 2 with `activate_wave2_expansion`
6. Scale to Wave 3 (full organization)

---

**Version:** 1.0 | **Last Updated:** 2026-08-13 | **Status:** Production Ready
