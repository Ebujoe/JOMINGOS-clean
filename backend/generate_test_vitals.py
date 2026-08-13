"""
Generate realistic test vital signs showing progression over time.
This creates 10-14 vital recordings for a patient over 3-4 days,
showing progressive deterioration for testing the comprehensive dashboard.
"""

import os
import django
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Jomingos.settings')
django.setup()

from django.utils import timezone
from accounts.models import User
from patients.models import Patient
from vitals.models import VitalSigns

# Get or create patient
patient = Patient.objects.get(pk=1003)  # Predictive Demo Patient
recording_user = User.objects.filter(is_staff=True).first() or User.objects.first()

if not recording_user:
    print("No staff user found. Creating admin user...")
    recording_user = User.objects.create_superuser('admin', 'admin@example.com', 'password')

# Start time: 3 days ago
base_time = timezone.now() - timedelta(days=3)

# Realistic progression: healthy → slight elevation → moderate → concerning
vital_progressions = [
    # Day 1: Normal baseline
    {'temp': 36.8, 'hr': 72, 'rr': 15, 'spo2': 97.5, 'bp_sys': 120, 'bp_dia': 80, 'label': 'Day 1 AM - Normal'},
    {'temp': 36.9, 'hr': 75, 'rr': 16, 'spo2': 97.0, 'bp_sys': 122, 'bp_dia': 81, 'label': 'Day 1 PM - Normal'},

    # Day 2: Slight elevation starting
    {'temp': 37.1, 'hr': 78, 'rr': 17, 'spo2': 96.8, 'bp_sys': 125, 'bp_dia': 82, 'label': 'Day 2 AM - Slight elevation'},
    {'temp': 37.3, 'hr': 82, 'rr': 18, 'spo2': 96.5, 'bp_sys': 128, 'bp_dia': 83, 'label': 'Day 2 Noon - Warming'},
    {'temp': 37.5, 'hr': 88, 'rr': 19, 'spo2': 96.0, 'bp_sys': 132, 'bp_dia': 84, 'label': 'Day 2 PM - Escalating'},
    {'temp': 37.8, 'hr': 92, 'rr': 20, 'spo2': 95.5, 'bp_sys': 135, 'bp_dia': 85, 'label': 'Day 2 Evening - Notable change'},

    # Day 3: Moderate deterioration
    {'temp': 38.1, 'hr': 98, 'rr': 22, 'spo2': 95.0, 'bp_sys': 138, 'bp_dia': 86, 'label': 'Day 3 AM - Concerning'},
    {'temp': 38.3, 'hr': 102, 'rr': 23, 'spo2': 94.5, 'bp_sys': 140, 'bp_dia': 87, 'label': 'Day 3 Noon - Moderate'},
    {'temp': 38.5, 'hr': 108, 'rr': 25, 'spo2': 94.0, 'bp_sys': 142, 'bp_dia': 88, 'label': 'Day 3 PM - Worsening'},

    # Day 4: Significant deterioration
    {'temp': 38.7, 'hr': 115, 'rr': 27, 'spo2': 93.5, 'bp_sys': 145, 'bp_dia': 89, 'label': 'Day 4 AM - Critical trending'},
    {'temp': 38.9, 'hr': 118, 'rr': 28, 'spo2': 92.8, 'bp_sys': 148, 'bp_dia': 90, 'label': 'Day 4 Late AM - High risk'},
]

print(f"\n{'='*70}")
print(f"Generating {len(vital_progressions)} test vital signs for Patient {patient.id}")
print(f"Patient: {patient.get_full_name()}")
print(f"{'='*70}\n")

created_count = 0
for i, vitals_data in enumerate(vital_progressions):
    # Calculate time for this recording (every 6-8 hours)
    recording_time = base_time + timedelta(hours=i * 7)

    vital = VitalSigns.objects.create(
        patient=patient,
        temperature=vitals_data['temp'],
        bp_systolic=int(vitals_data['bp_sys']),
        bp_diastolic=int(vitals_data['bp_dia']),
        heart_rate=int(vitals_data['hr']),
        respiratory_rate=int(vitals_data['rr']),
        oxygen_saturation=vitals_data['spo2'],
        blood_glucose=5.5,
        weight_kg=70.0,
        pain_score=0,
        recorded_at=recording_time,
        recorded_by=recording_user,
        notes=vitals_data['label']
    )

    created_count += 1

    print(f"[OK] Recording {i+1:2d}: {vital.recorded_at.strftime('%d/%m %H:%M')} | "
          f"T:{vital.temperature}C  HR:{vital.heart_rate} RR:{vital.respiratory_rate} "
          f"SpO2:{vital.oxygen_saturation}% | {vitals_data['label']}")

print(f"\n{'='*70}")
print(f"SUCCESS: Created {created_count} vital sign recordings!")
print(f"{'='*70}\n")

print("Next steps:")
print("1. Navigate to: http://localhost:8000/vitals/1003/predictive/")
print("2. View the comprehensive dashboard with multi-horizon forecasts")
print("3. See the timeline of vital sign progression over the 4 days")
print("4. Check forecasts for 24h, 7d, 30d, and 365d ahead\n")
