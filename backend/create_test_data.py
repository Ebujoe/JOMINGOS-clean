#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Create test patients with vital signs data for dashboard testing.

This will:
1. Create 5 test patients
2. Add 50 vital sign measurements for each patient
3. Make them visible in the dashboard
"""

import os
import sys
import django
from datetime import datetime, timedelta
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Jomingos.settings')
django.setup()

from django.contrib.auth import get_user_model
from patients.models import Patient
from vitals.models import VitalSigns

User = get_user_model()

print("\n" + "="*70)
print("CREATING TEST DATA FOR DASHBOARD")
print("="*70)

# Create or get test user
print("\n[STEP 1] Creating test user...")
try:
    user = User.objects.get(username='testuser')
    print("✓ Test user already exists")
except User.DoesNotExist:
    user = User.objects.create_user(
        username='testuser',
        email='test@test.com',
        password='testpass123',
        first_name='Test',
        last_name='User',
        is_staff=True,
        is_active=True
    )
    print("✓ Created test user: testuser / testpass123")

# Create test patients
print("\n[STEP 2] Creating test patients...")

patients_data = [
    {
        'first_name': 'Richard',
        'last_name': 'Anderson',
        'date_of_birth': '1945-03-15',
        'room_number': '101'
    },
    {
        'first_name': 'Sarah',
        'last_name': 'Smith',
        'date_of_birth': '1950-07-22',
        'room_number': '102'
    },
    {
        'first_name': 'James',
        'last_name': 'Wilson',
        'date_of_birth': '1948-11-08',
        'room_number': '103'
    },
    {
        'first_name': 'Michael',
        'last_name': 'Brown',
        'date_of_birth': '1952-05-19',
        'room_number': '104'
    },
    {
        'first_name': 'Patricia',
        'last_name': 'Johnson',
        'date_of_birth': '1947-09-30',
        'room_number': '105'
    }
]

patients = []
for data in patients_data:
    patient, created = Patient.objects.get_or_create(
        first_name=data['first_name'],
        last_name=data['last_name'],
        defaults={
            'date_of_birth': data['date_of_birth'],
            'room_number': data['room_number'],
            'is_active': True
        }
    )
    patients.append(patient)
    status = "Created" if created else "Already exists"
    print(f"✓ {patient.get_full_name()} ({data['room_number']}) - {status}")

# Add vital signs data
print("\n[STEP 3] Adding vital signs data...")

for patient in patients:
    # Delete existing vitals for clean slate
    VitalSigns.objects.filter(patient=patient).delete()

    print(f"\n  {patient.get_full_name()}:")

    # Create 50 measurements over last 7 days
    base_time = datetime.now() - timedelta(days=7)

    for i in range(50):
        timestamp = base_time + timedelta(hours=i*3.36)  # Spread over 7 days

        # Generate realistic vital signs
        heart_rate = random.randint(68, 85)
        respiratory_rate = random.randint(14, 20)
        oxygen = round(random.uniform(95, 99), 1)
        temp = round(random.uniform(36.2, 37.2), 1)
        bp_sys = random.randint(115, 135)
        bp_dia = random.randint(70, 85)

        # Create vital signs record (all in one record)
        VitalSigns.objects.create(
            patient=patient,
            heart_rate=heart_rate,
            respiratory_rate=respiratory_rate,
            oxygen_saturation=oxygen,
            temperature=temp,
            bp_systolic=bp_sys,
            bp_diastolic=bp_dia,
            recorded_at=timestamp,
            recorded_by=user
        )

    vital_count = VitalSigns.objects.filter(patient=patient).count()
    print(f"    ✓ Added {vital_count} vital sign records")

print("\n" + "="*70)
print("TEST DATA CREATED SUCCESSFULLY")
print("="*70)

print("\nNow you can:")
print("1. Start Django: python manage.py runserver")
print("2. Open: http://localhost:8000")
print("3. Log in with: testuser / testpass123")
print("4. Go to Vitals Dashboard")
print("5. See patients with vital signs and FALL DETECTION TOGGLE!")

print("\nPatients created:")
for patient in patients:
    vital_count = VitalSigns.objects.filter(patient=patient).count()
    print(f"  ✓ {patient.get_full_name()} - {vital_count} vital measurements")

print("\n" + "="*70 + "\n")
