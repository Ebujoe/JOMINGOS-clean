"""
Generate realistic test vital signs for multiple patients with diverse scenarios.
Creates 5 patients with different risk profiles and progressions:
1. Patient 1003: Deteriorating (original - stable to critical)
2. Patient 1004: Stable healthy (baseline normal vitals)
3. Patient 1005: Slow recovery (improving from respiratory illness)
4. Patient 1006: Rapid deterioration (acute condition developing fast)
5. Patient 1007: Elderly with fluctuations (minor variations around normal)
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

# Get or create staff user for recording
recording_user = User.objects.filter(is_staff=True).first()
if not recording_user:
    print("Creating admin user...")
    recording_user = User.objects.create_superuser('admin', 'admin@example.com', 'password')

print("\n" + "=" * 80)
print("MULTI-PATIENT TEST DATA GENERATION")
print("=" * 80)

# ============================================================================
# PATIENT 1: Deteriorating (Already exists - patient 1003)
# ============================================================================
print("\n[1/5] Patient 1003: DETERIORATING CASE (Stable -> Critical)")
print("-" * 80)

patient_1003 = Patient.objects.get(pk=1003)
base_time = timezone.now() - timedelta(days=3)

vitals_1003 = [
    {'temp': 36.8, 'hr': 72, 'rr': 15, 'spo2': 97.5, 'bp_sys': 120, 'bp_dia': 80, 'label': 'Day 1 AM - Normal'},
    {'temp': 36.9, 'hr': 75, 'rr': 16, 'spo2': 97.0, 'bp_sys': 122, 'bp_dia': 81, 'label': 'Day 1 PM - Normal'},
    {'temp': 37.1, 'hr': 78, 'rr': 17, 'spo2': 96.8, 'bp_sys': 125, 'bp_dia': 82, 'label': 'Day 2 AM - Slight elevation'},
    {'temp': 37.3, 'hr': 82, 'rr': 18, 'spo2': 96.5, 'bp_sys': 128, 'bp_dia': 83, 'label': 'Day 2 Noon - Warming'},
    {'temp': 37.5, 'hr': 88, 'rr': 19, 'spo2': 96.0, 'bp_sys': 132, 'bp_dia': 84, 'label': 'Day 2 PM - Escalating'},
    {'temp': 37.8, 'hr': 92, 'rr': 20, 'spo2': 95.5, 'bp_sys': 135, 'bp_dia': 85, 'label': 'Day 2 Evening - Notable change'},
    {'temp': 38.1, 'hr': 98, 'rr': 22, 'spo2': 95.0, 'bp_sys': 138, 'bp_dia': 86, 'label': 'Day 3 AM - Concerning'},
    {'temp': 38.3, 'hr': 102, 'rr': 23, 'spo2': 94.5, 'bp_sys': 140, 'bp_dia': 87, 'label': 'Day 3 Noon - Moderate'},
    {'temp': 38.5, 'hr': 108, 'rr': 25, 'spo2': 94.0, 'bp_sys': 142, 'bp_dia': 88, 'label': 'Day 3 PM - Worsening'},
    {'temp': 38.7, 'hr': 115, 'rr': 27, 'spo2': 93.5, 'bp_sys': 145, 'bp_dia': 89, 'label': 'Day 4 AM - Critical trending'},
    {'temp': 38.9, 'hr': 118, 'rr': 28, 'spo2': 92.8, 'bp_sys': 148, 'bp_dia': 90, 'label': 'Day 4 Late AM - High risk'},
]

created_1003 = 0
for i, vitals_data in enumerate(vitals_1003):
    recording_time = base_time + timedelta(hours=i * 7)
    VitalSigns.objects.create(
        patient=patient_1003,
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
    created_1003 += 1
    print(f"  [{i+1:2d}] {vitals_data['label']:35} | T:{vitals_data['temp']}C HR:{vitals_data['hr']:3d} RR:{vitals_data['rr']:2d} SpO2:{vitals_data['spo2']}%")

print(f"  Status: Created {created_1003} recordings")

# ============================================================================
# PATIENT 2: Stable Healthy
# ============================================================================
print("\n[2/5] Patient 1004: STABLE HEALTHY CASE (Normal vitals, no deterioration)")
print("-" * 80)

patient_1004 = Patient.objects.get(pk=1004)
base_time_1004 = timezone.now() - timedelta(days=3)

vitals_1004 = [
    {'temp': 37.0, 'hr': 68, 'rr': 14, 'spo2': 98.2, 'bp_sys': 118, 'bp_dia': 78, 'label': 'Day 1 AM - Baseline normal'},
    {'temp': 36.95, 'hr': 70, 'rr': 15, 'spo2': 98.0, 'bp_sys': 120, 'bp_dia': 79, 'label': 'Day 1 PM - Stable'},
    {'temp': 37.05, 'hr': 69, 'rr': 14, 'spo2': 98.1, 'bp_sys': 119, 'bp_dia': 78, 'label': 'Day 2 AM - Excellent'},
    {'temp': 37.1, 'hr': 71, 'rr': 15, 'spo2': 98.0, 'bp_sys': 121, 'bp_dia': 79, 'label': 'Day 2 Noon - All normal'},
    {'temp': 37.0, 'hr': 67, 'rr': 14, 'spo2': 98.3, 'bp_sys': 118, 'bp_dia': 77, 'label': 'Day 2 PM - Excellent'},
    {'temp': 37.05, 'hr': 70, 'rr': 15, 'spo2': 98.1, 'bp_sys': 120, 'bp_dia': 78, 'label': 'Day 2 Evening - Optimal'},
    {'temp': 36.95, 'hr': 68, 'rr': 14, 'spo2': 98.2, 'bp_sys': 119, 'bp_dia': 78, 'label': 'Day 3 AM - Perfect'},
    {'temp': 37.0, 'hr': 69, 'rr': 15, 'spo2': 98.0, 'bp_sys': 120, 'bp_dia': 79, 'label': 'Day 3 Noon - Stable'},
    {'temp': 37.1, 'hr': 71, 'rr': 14, 'spo2': 98.1, 'bp_sys': 121, 'bp_dia': 79, 'label': 'Day 3 PM - Great'},
    {'temp': 37.05, 'hr': 70, 'rr': 15, 'spo2': 98.2, 'bp_sys': 120, 'bp_dia': 78, 'label': 'Day 4 AM - Excellent'},
    {'temp': 36.98, 'hr': 68, 'rr': 14, 'spo2': 98.0, 'bp_sys': 119, 'bp_dia': 78, 'label': 'Day 4 Noon - All normal'},
]

created_1004 = 0
for i, vitals_data in enumerate(vitals_1004):
    recording_time = base_time_1004 + timedelta(hours=i * 7)
    VitalSigns.objects.create(
        patient=patient_1004,
        temperature=vitals_data['temp'],
        bp_systolic=int(vitals_data['bp_sys']),
        bp_diastolic=int(vitals_data['bp_dia']),
        heart_rate=int(vitals_data['hr']),
        respiratory_rate=int(vitals_data['rr']),
        oxygen_saturation=vitals_data['spo2'],
        blood_glucose=5.3,
        weight_kg=75.0,
        pain_score=0,
        recorded_at=recording_time,
        recorded_by=recording_user,
        notes=vitals_data['label']
    )
    created_1004 += 1
    print(f"  [{i+1:2d}] {vitals_data['label']:35} | T:{vitals_data['temp']}C HR:{vitals_data['hr']:3d} RR:{vitals_data['rr']:2d} SpO2:{vitals_data['spo2']}%")

print(f"  Status: Created {created_1004} recordings")

# ============================================================================
# PATIENT 3: Slow Recovery
# ============================================================================
print("\n[3/5] Patient 1005: SLOW RECOVERY CASE (Improving respiratory vitals)")
print("-" * 80)

patient_1005 = Patient.objects.get(pk=1005)
base_time_1005 = timezone.now() - timedelta(days=3)

vitals_1005 = [
    {'temp': 38.2, 'hr': 105, 'rr': 26, 'spo2': 93.0, 'bp_sys': 142, 'bp_dia': 88, 'label': 'Day 1 AM - Post-pneumonia'},
    {'temp': 38.1, 'hr': 102, 'rr': 25, 'spo2': 93.5, 'bp_sys': 140, 'bp_dia': 87, 'label': 'Day 1 PM - Slight improve'},
    {'temp': 37.95, 'hr': 100, 'rr': 24, 'spo2': 94.0, 'bp_sys': 138, 'bp_dia': 86, 'label': 'Day 2 AM - Improving'},
    {'temp': 37.8, 'hr': 96, 'rr': 23, 'spo2': 94.5, 'bp_sys': 135, 'bp_dia': 85, 'label': 'Day 2 Noon - Better trending'},
    {'temp': 37.65, 'hr': 92, 'rr': 22, 'spo2': 95.0, 'bp_sys': 132, 'bp_dia': 84, 'label': 'Day 2 PM - Good progress'},
    {'temp': 37.5, 'hr': 88, 'rr': 20, 'spo2': 95.5, 'bp_sys': 128, 'bp_dia': 82, 'label': 'Day 2 Evening - Recovering'},
    {'temp': 37.3, 'hr': 82, 'rr': 18, 'spo2': 96.0, 'bp_sys': 125, 'bp_dia': 81, 'label': 'Day 3 AM - Much better'},
    {'temp': 37.1, 'hr': 78, 'rr': 17, 'spo2': 96.5, 'bp_sys': 122, 'bp_dia': 79, 'label': 'Day 3 Noon - Nearly normal'},
    {'temp': 37.0, 'hr': 75, 'rr': 16, 'spo2': 96.8, 'bp_sys': 120, 'bp_dia': 78, 'label': 'Day 3 PM - Good recovery'},
    {'temp': 36.95, 'hr': 72, 'rr': 15, 'spo2': 97.2, 'bp_sys': 118, 'bp_dia': 76, 'label': 'Day 4 AM - Excellent progress'},
    {'temp': 36.9, 'hr': 70, 'rr': 15, 'spo2': 97.5, 'bp_sys': 116, 'bp_dia': 75, 'label': 'Day 4 Noon - Near baseline'},
]

created_1005 = 0
for i, vitals_data in enumerate(vitals_1005):
    recording_time = base_time_1005 + timedelta(hours=i * 7)
    VitalSigns.objects.create(
        patient=patient_1005,
        temperature=vitals_data['temp'],
        bp_systolic=int(vitals_data['bp_sys']),
        bp_diastolic=int(vitals_data['bp_dia']),
        heart_rate=int(vitals_data['hr']),
        respiratory_rate=int(vitals_data['rr']),
        oxygen_saturation=vitals_data['spo2'],
        blood_glucose=5.6,
        weight_kg=68.0,
        pain_score=2,
        recorded_at=recording_time,
        recorded_by=recording_user,
        notes=vitals_data['label']
    )
    created_1005 += 1
    print(f"  [{i+1:2d}] {vitals_data['label']:35} | T:{vitals_data['temp']}C HR:{vitals_data['hr']:3d} RR:{vitals_data['rr']:2d} SpO2:{vitals_data['spo2']}%")

print(f"  Status: Created {created_1005} recordings")

# ============================================================================
# PATIENT 4: Rapid Deterioration
# ============================================================================
print("\n[4/5] Patient 1006: RAPID DETERIORATION (Acute onset - Critical in 48h)")
print("-" * 80)

patient_1006 = Patient.objects.get(pk=1006)
base_time_1006 = timezone.now() - timedelta(days=2)

vitals_1006 = [
    {'temp': 37.1, 'hr': 76, 'rr': 16, 'spo2': 97.0, 'bp_sys': 122, 'bp_dia': 80, 'label': 'Day 1 AM - Appeared normal'},
    {'temp': 37.5, 'hr': 88, 'rr': 19, 'spo2': 96.0, 'bp_sys': 132, 'bp_dia': 84, 'label': 'Day 1 Noon - Sudden onset'},
    {'temp': 37.9, 'hr': 98, 'rr': 22, 'spo2': 95.0, 'bp_sys': 140, 'bp_dia': 87, 'label': 'Day 1 PM - Rapid change'},
    {'temp': 38.3, 'hr': 110, 'rr': 25, 'spo2': 93.5, 'bp_sys': 148, 'bp_dia': 90, 'label': 'Day 1 Evening - Escalating fast'},
    {'temp': 38.7, 'hr': 122, 'rr': 28, 'spo2': 92.0, 'bp_sys': 155, 'bp_dia': 93, 'label': 'Day 2 AM - Critical alert'},
    {'temp': 38.9, 'hr': 130, 'rr': 30, 'spo2': 91.0, 'bp_sys': 160, 'bp_dia': 95, 'label': 'Day 2 Noon - IMMEDIATE INTERVENTION'},
    {'temp': 38.95, 'hr': 135, 'rr': 31, 'spo2': 90.0, 'bp_sys': 162, 'bp_dia': 96, 'label': 'Day 2 PM - HIGH RISK STATUS'},
    {'temp': 39.0, 'hr': 138, 'rr': 32, 'spo2': 89.5, 'bp_sys': 165, 'bp_dia': 98, 'label': 'Day 2 Evening - CRITICAL'},
]

created_1006 = 0
for i, vitals_data in enumerate(vitals_1006):
    recording_time = base_time_1006 + timedelta(hours=i * 6)
    VitalSigns.objects.create(
        patient=patient_1006,
        temperature=vitals_data['temp'],
        bp_systolic=int(vitals_data['bp_sys']),
        bp_diastolic=int(vitals_data['bp_dia']),
        heart_rate=int(vitals_data['hr']),
        respiratory_rate=int(vitals_data['rr']),
        oxygen_saturation=vitals_data['spo2'],
        blood_glucose=7.2,
        weight_kg=72.0,
        pain_score=5,
        recorded_at=recording_time,
        recorded_by=recording_user,
        notes=vitals_data['label']
    )
    created_1006 += 1
    print(f"  [{i+1:2d}] {vitals_data['label']:35} | T:{vitals_data['temp']}C HR:{vitals_data['hr']:3d} RR:{vitals_data['rr']:2d} SpO2:{vitals_data['spo2']}%")

print(f"  Status: Created {created_1006} recordings")

# ============================================================================
# PATIENT 5: Elderly with Fluctuations
# ============================================================================
print("\n[5/5] Patient 1007: ELDERLY WITH FLUCTUATIONS (Minor variations, managed)")
print("-" * 80)

patient_1007 = Patient.objects.get(pk=1007)
base_time_1007 = timezone.now() - timedelta(days=3)

vitals_1007 = [
    {'temp': 37.1, 'hr': 72, 'rr': 16, 'spo2': 96.5, 'bp_sys': 135, 'bp_dia': 82, 'label': 'Day 1 AM - Morning baseline'},
    {'temp': 37.3, 'hr': 75, 'rr': 17, 'spo2': 96.2, 'bp_sys': 138, 'bp_dia': 83, 'label': 'Day 1 Afternoon - Slight increase'},
    {'temp': 37.2, 'hr': 73, 'rr': 16, 'spo2': 96.3, 'bp_sys': 136, 'bp_dia': 82, 'label': 'Day 1 Evening - Back to baseline'},
    {'temp': 37.0, 'hr': 70, 'rr': 15, 'spo2': 96.8, 'bp_sys': 133, 'bp_dia': 81, 'label': 'Day 2 AM - Slightly lower'},
    {'temp': 37.2, 'hr': 74, 'rr': 16, 'spo2': 96.5, 'bp_sys': 137, 'bp_dia': 83, 'label': 'Day 2 Noon - Up slightly'},
    {'temp': 37.25, 'hr': 76, 'rr': 17, 'spo2': 96.0, 'bp_sys': 139, 'bp_dia': 84, 'label': 'Day 2 PM - Activity related'},
    {'temp': 37.15, 'hr': 72, 'rr': 16, 'spo2': 96.4, 'bp_sys': 135, 'bp_dia': 82, 'label': 'Day 2 Evening - Normalized'},
    {'temp': 37.05, 'hr': 71, 'rr': 15, 'spo2': 96.7, 'bp_sys': 134, 'bp_dia': 81, 'label': 'Day 3 AM - Well controlled'},
    {'temp': 37.2, 'hr': 73, 'rr': 16, 'spo2': 96.3, 'bp_sys': 137, 'bp_dia': 83, 'label': 'Day 3 Noon - Midday fluctuation'},
    {'temp': 37.1, 'hr': 72, 'rr': 16, 'spo2': 96.5, 'bp_sys': 135, 'bp_dia': 82, 'label': 'Day 3 PM - Stable pattern'},
    {'temp': 37.15, 'hr': 74, 'rr': 16, 'spo2': 96.4, 'bp_sys': 136, 'bp_dia': 82, 'label': 'Day 4 AM - Routine normal'},
]

created_1007 = 0
for i, vitals_data in enumerate(vitals_1007):
    recording_time = base_time_1007 + timedelta(hours=i * 6.5)
    VitalSigns.objects.create(
        patient=patient_1007,
        temperature=vitals_data['temp'],
        bp_systolic=int(vitals_data['bp_sys']),
        bp_diastolic=int(vitals_data['bp_dia']),
        heart_rate=int(vitals_data['hr']),
        respiratory_rate=int(vitals_data['rr']),
        oxygen_saturation=vitals_data['spo2'],
        blood_glucose=6.2,
        weight_kg=65.0,
        pain_score=1,
        recorded_at=recording_time,
        recorded_by=recording_user,
        notes=vitals_data['label']
    )
    created_1007 += 1
    print(f"  [{i+1:2d}] {vitals_data['label']:35} | T:{vitals_data['temp']}C HR:{vitals_data['hr']:3d} RR:{vitals_data['rr']:2d} SpO2:{vitals_data['spo2']}%")

print(f"  Status: Created {created_1007} recordings")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

total = created_1003 + created_1004 + created_1005 + created_1006 + created_1007
print(f"\nSuccessfully created {total} vital recordings across 5 patients:")
print(f"  • Patient 1003 (Deteriorating):       {created_1003} recordings")
print(f"  • Patient 1004 (Stable):              {created_1004} recordings")
print(f"  • Patient 1005 (Recovering):          {created_1005} recordings")
print(f"  • Patient 1006 (Rapid Deterioration): {created_1006} recordings")
print(f"  • Patient 1007 (Elderly):             {created_1007} recordings")

print(f"\nNext steps:")
print("1. Navigate to: http://localhost:8000/vitals/1003/predictive/")
print("2. Use patient dropdown or prev/next buttons to view different patients")
print("3. Compare forecast confidence and recommendations across risk profiles")
print("4. Observe how the system handles:")
print("   - Stable patients (no critical alerts)")
print("   - Rapid deterioration (immediate intervention needed)")
print("   - Recovery patterns (improving trends)")
print("   - Elderly patients with managed fluctuations")

print("\n" + "=" * 80)
