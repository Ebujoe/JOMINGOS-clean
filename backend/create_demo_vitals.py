#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Create demo vital signs that will trigger alerts
This script generates vitals with critical NEWS2 scores
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Jomingos.settings')
django.setup()

from django.contrib.auth import get_user_model
from vitals.models import VitalSigns
from patients.models import Patient
from datetime import timedelta
from django.utils import timezone

User = get_user_model()

print("\n" + "="*70)
print("Creating Demo Vital Signs for Testing")
print("="*70)

# Get or create test user
user, _ = User.objects.get_or_create(
    username='teststaff',
    defaults={'email': 'test@test.com', 'is_staff': True, 'is_active': True}
)
user.set_password('testpass123')
user.save()

# Get patients
patients = Patient.objects.all()[:3]
if not patients:
    print("[ERROR] No patients found in database!")
    sys.exit(1)

demo_vitals = [
    {
        'name': 'CRITICAL - Low Oxygen',
        'patient_idx': 0,
        'vitals': {
            'temperature': 36.5,
            'bp_systolic': 110,
            'bp_diastolic': 70,
            'heart_rate': 95,
            'respiratory_rate': 18,
            'oxygen_saturation': 90,  # CRITICAL - < 91%
            'blood_glucose': 6.0,
            'pain_score': 2,
            'notes': 'Demo critical alert - low oxygen saturation'
        },
        'expected_news2': 5  # spo2=3 + rest low
    },
    {
        'name': 'CRITICAL - High Heart Rate & Low Respiration',
        'patient_idx': 1,
        'vitals': {
            'temperature': 38.5,
            'bp_systolic': 105,
            'bp_diastolic': 68,
            'heart_rate': 135,  # CRITICAL - > 130
            'respiratory_rate': 7,   # CRITICAL - <= 8
            'oxygen_saturation': 96.0,
            'blood_glucose': 7.5,
            'pain_score': 1,
            'notes': 'Demo critical alert - tachycardia and bradypnea'
        },
        'expected_news2': 6  # hr=3 + rr=3 + temp=1
    },
    {
        'name': 'HIGH RISK - Elevated Blood Pressure & Respiration',
        'patient_idx': 2,
        'vitals': {
            'temperature': 37.5,
            'bp_systolic': 145,  # HIGH - > 110 but < 220
            'bp_diastolic': 90,
            'heart_rate': 105,   # Elevated
            'respiratory_rate': 22,  # Elevated
            'oxygen_saturation': 95.0,
            'blood_glucose': 8.0,
            'pain_score': 3,
            'notes': 'Demo high-risk alert - elevated vitals'
        },
        'expected_news2': 3  # bp=0 + rr=2 + hr=1
    },
]

print("\nCreating demo vitals with critical values...\n")

created_count = 0
for idx, demo in enumerate(demo_vitals):
    try:
        patient = patients[demo['patient_idx']]
        vital = VitalSigns.objects.create(
            patient=patient,
            recorded_by=user,
            **demo['vitals']
        )

        actual_news2 = vital.news2_total
        print(f"[{idx+1}] {demo['name']}")
        print(f"    Patient: {patient.first_name} {patient.last_name}")
        print(f"    NEWS2 Score: {actual_news2} (expected: {demo['expected_news2']})")
        print(f"    - Temperature: {vital.temperature}°C")
        print(f"    - BP: {vital.bp_systolic}/{vital.bp_diastolic}")
        print(f"    - HR: {vital.heart_rate} bpm")
        print(f"    - RR: {vital.respiratory_rate}")
        print(f"    - SpO2: {vital.oxygen_saturation}%")
        print(f"    Status: CREATED (signal should trigger alert if NEWS2 >= 5)")
        print()

        created_count += 1

    except Exception as e:
        print(f"[ERROR] Failed to create vital #{idx+1}: {e}")

print("="*70)
print(f"Created {created_count} demo vital signs")
print("="*70)
print("\nNext: Run test_complete_flow.py to verify alerts were created")
print("="*70 + "\n")
