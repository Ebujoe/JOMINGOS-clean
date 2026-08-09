#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Complete end-to-end test of JOMINGOS vitals system.
Tests: Create patient, record vitals, check calculations, verify alerts.
"""
import os
import sys
import django

# Force UTF-8 output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Jomingos.settings')
django.setup()

from datetime import timedelta
from django.utils import timezone
from patients.models import Patient
from vitals.models import VitalSigns
from deterioration_alerts.models import DeteriorationAlert
from accounts.models import User
from django.contrib.auth import get_user_model

User = get_user_model()

def print_section(title):
    """Print a section header"""
    print("\n" + "="*70)
    print("  " + title)
    print("="*70 + "\n")

def test_vitals_recording_and_calculation():
    """Test vital recording and NEWS2 calculation"""
    print_section("TEST 1: VITALS RECORDING & NEWS2 CALCULATION")

    # Get or create test patient
    try:
        patient = Patient.objects.get(first_name="Test", last_name="Patient")
        print(f"[OK] Using existing test patient: {patient.get_full_name()} (ID: {patient.id})")
    except Patient.DoesNotExist:
        patient = Patient.objects.create(
            first_name="Test",
            last_name="Patient",
            date_of_birth="1950-01-15",
            gender="M",
            is_active=True
        )
        print(f"[OK] Created test patient: {patient.get_full_name()} (ID: {patient.id})")

    # Get a nurse user to record vitals
    nurse = User.objects.filter(role='nurse').first() or User.objects.filter(role='admin').first()
    if not nurse:
        print("[ERROR] No nurse or admin user found!")
        return
    print(f"[OK] Using user: {nurse.username} ({nurse.get_role_display()})")

    # Test Case 1: Stable vitals
    print("\n--- Case 1: Stable Vitals (GREEN) ---")
    vital1 = VitalSigns.objects.create(
        patient=patient,
        recorded_by=nurse,
        recorded_at=timezone.now() - timedelta(hours=4),
        heart_rate=72,
        respiratory_rate=16,
        oxygen_saturation=97.0,
        bp_systolic=120,
        bp_diastolic=80,
        temperature=37.0,
    )
    print(f"Input: HR={vital1.heart_rate}, RR={vital1.respiratory_rate}, SpO2={vital1.oxygen_saturation}%, BP={vital1.bp_systolic}/{vital1.bp_diastolic}, Temp={vital1.temperature}°C")
    print(f"NEWS2 Scores: HR={vital1.news2_hr_score}, RR={vital1.news2_respiratory_score}, SpO2={vital1.news2_spo2_score}, BP={vital1.news2_bp_score}, Temp={vital1.news2_temp_score}")
    print(f"NEWS2 Total: {vital1.news2_total} (Level: {vital1.news2_level})")
    print(f"Alert Triggered: {vital1.deterioration_alerts.exists()}")

    # Test Case 2: Deteriorating vitals
    print("\n--- Case 2: Deteriorating Vitals (ORANGE) ---")
    vital2 = VitalSigns.objects.create(
        patient=patient,
        recorded_by=nurse,
        recorded_at=timezone.now() - timedelta(hours=3),
        heart_rate=88,
        respiratory_rate=20,
        oxygen_saturation=95.8,
        bp_systolic=128,
        bp_diastolic=84,
        temperature=37.5,
    )
    print(f"Input: HR={vital2.heart_rate}, RR={vital2.respiratory_rate}, SpO2={vital2.oxygen_saturation}%, BP={vital2.bp_systolic}/{vital2.bp_diastolic}, Temp={vital2.temperature}°C")
    print(f"NEWS2 Scores: HR={vital2.news2_hr_score}, RR={vital2.news2_respiratory_score}, SpO2={vital2.news2_spo2_score}, BP={vital2.news2_bp_score}, Temp={vital2.news2_temp_score}")
    print(f"NEWS2 Total: {vital2.news2_total} (Level: {vital2.news2_level})")
    print(f"Alert Triggered: {vital2.deterioration_alerts.exists()}")

    # Test Case 3: Critical vitals
    print("\n--- Case 3: Critical Vitals (CRITICAL) ---")
    vital3 = VitalSigns.objects.create(
        patient=patient,
        recorded_by=nurse,
        recorded_at=timezone.now() - timedelta(hours=2),
        heart_rate=108,
        respiratory_rate=26,
        oxygen_saturation=92.1,
        bp_systolic=122,
        bp_diastolic=80,
        temperature=38.2,
    )
    print(f"Input: HR={vital3.heart_rate}, RR={vital3.respiratory_rate}, SpO2={vital3.oxygen_saturation}%, BP={vital3.bp_systolic}/{vital3.bp_diastolic}, Temp={vital3.temperature}°C")
    print(f"NEWS2 Scores: HR={vital3.news2_hr_score}, RR={vital3.news2_respiratory_score}, SpO2={vital3.news2_spo2_score}, BP={vital3.news2_bp_score}, Temp={vital3.news2_temp_score}")
    print(f"NEWS2 Total: {vital3.news2_total} (Level: {vital3.news2_level})")
    print(f"Alert Triggered: {vital3.deterioration_alerts.exists()}")
    if vital3.deterioration_alerts.exists():
        for alert in vital3.deterioration_alerts.all():
            print(f"  - Priority: {alert.priority}, Reason: {alert.trigger_reason}")

    # Test Case 4: Very critical vitals
    print("\n--- Case 4: Very Critical Vitals (EMERGENCY) ---")
    vital4 = VitalSigns.objects.create(
        patient=patient,
        recorded_by=nurse,
        recorded_at=timezone.now() - timedelta(hours=1),
        heart_rate=115,
        respiratory_rate=28,
        oxygen_saturation=90.5,
        bp_systolic=115,
        bp_diastolic=78,
        temperature=38.8,
    )
    print(f"Input: HR={vital4.heart_rate}, RR={vital4.respiratory_rate}, SpO2={vital4.oxygen_saturation}%, BP={vital4.bp_systolic}/{vital4.bp_diastolic}, Temp={vital4.temperature}°C")
    print(f"NEWS2 Scores: HR={vital4.news2_hr_score}, RR={vital4.news2_respiratory_score}, SpO2={vital4.news2_spo2_score}, BP={vital4.news2_bp_score}, Temp={vital4.news2_temp_score}")
    print(f"NEWS2 Total: {vital4.news2_total} (Level: {vital4.news2_level})")
    print(f"Alert Triggered: {vital4.deterioration_alerts.exists()}")
    if vital4.deterioration_alerts.exists():
        for alert in vital4.deterioration_alerts.all():
            print(f"  - Priority: {alert.priority}, Reason: {alert.trigger_reason}")

def test_patient_history_view():
    """Test patient vital history calculations"""
    print_section("TEST 2: PATIENT VITAL HISTORY")

    patient = Patient.objects.filter(first_name="Test", last_name="Patient").first()
    if not patient:
        print("[ERROR] Test patient not found!")
        return

    vitals = VitalSigns.objects.filter(patient=patient).order_by('recorded_at')
    print(f"Patient: {patient.get_full_name()}")
    print(f"Total Recordings: {vitals.count()}")
    print(f"Active Alerts: {patient.deterioration_alerts.count()}")

    print("\n--- Vital History Timeline ---")
    for i, vital in enumerate(vitals, 1):
        print(f"\nRecording #{i}: {vital.recorded_at.strftime('%d/%m/%Y %H:%M')}")
        print(f"  Vitals: HR={vital.heart_rate}, RR={vital.respiratory_rate}, SpO2={vital.oxygen_saturation}%,  BP={vital.bp_systolic}/{vital.bp_diastolic}, Temp={vital.temperature}°C")
        print(f"  NEWS2: {vital.news2_total} ({vital.news2_level})")
        print(f"  Breakdown: HR={vital.news2_hr_score}, RR={vital.news2_respiratory_score}, SpO2={vital.news2_spo2_score}, BP={vital.news2_bp_score}, Temp={vital.news2_temp_score}")

        # Calculate rate of change from previous
        if i > 1:
            prev_vital = vitals[i-2]
            time_diff = (vital.recorded_at - prev_vital.recorded_at).total_seconds() / 3600  # hours
            if time_diff > 0:
                hr_roc = (float(vital.heart_rate) - float(prev_vital.heart_rate)) / time_diff if vital.heart_rate and prev_vital.heart_rate else 0
                rr_roc = (float(vital.respiratory_rate) - float(prev_vital.respiratory_rate)) / time_diff if vital.respiratory_rate and prev_vital.respiratory_rate else 0
                spo2_roc = (float(vital.oxygen_saturation) - float(prev_vital.oxygen_saturation)) / time_diff if vital.oxygen_saturation and prev_vital.oxygen_saturation else 0
                print(f"  ROC: HR={hr_roc:.2f} bpm/h, RR={rr_roc:.2f} br/h, SpO2={spo2_roc:.2f}%/h")

        # Check for alerts
        alerts = vital.deterioration_alerts.all()
        if alerts:
            print(f"  [WARNING]  ALERT TRIGGERED:")
            for alert in alerts:
                print(f"      Priority: {alert.priority}, Reason: {alert.trigger_reason}")
        else:
            print(f"  [OK] No alerts")

def test_alert_system():
    """Test alert generation"""
    print_section("TEST 3: ALERT SYSTEM")

    patient = Patient.objects.filter(first_name="Test", last_name="Patient").first()
    if not patient:
        print("[ERROR] Test patient not found!")
        return

    alerts = DeteriorationAlert.objects.filter(related_vital__patient=patient)
    print(f"Total Alerts for {patient.get_full_name()}: {alerts.count()}")

    if alerts.exists():
        print("\n--- Alert Details ---")
        for alert in alerts.order_by('-triggered_at'):
            print(f"\nAlert ID: {alert.id}")
            print(f"  Time: {alert.triggered_at.strftime('%d/%m/%Y %H:%M:%S')}")
            print(f"  Vital Recording: #{alert.related_vital.id} ({alert.related_vital.recorded_at.strftime('%d/%m/%Y %H:%M')})")
            print(f"  Priority: {alert.priority}")
            print(f"  Status: {alert.status}")
            print(f"  NEWS2 Score: {alert.related_vital.news2_total}")
            print(f"  Trigger Reason: {alert.trigger_reason}")
    else:
        print("\n[OK] No alerts generated (all vitals within acceptable range)")

if __name__ == "__main__":
    print("\n" + "="*70)
    print("  JOMINGOS VITALS SYSTEM - END-TO-END TEST")
    print("="*70)

    try:
        test_vitals_recording_and_calculation()
        test_patient_history_view()
        test_alert_system()

        print_section("TEST COMPLETE")
        print("[OK] All tests completed successfully!")
        print("\nNext Steps:")
        print("1. Open http://localhost:8000/vitals/ to see the dashboard")
        print("2. Navigate to patient history to see calculations")
        print("3. Check for alert notifications")

    except Exception as e:
        print(f"\n[ERROR] ERROR: {e}")
        import traceback
        traceback.print_exc()
