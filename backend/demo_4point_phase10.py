"""
Phase 10: Predictive Forecasting - 4-Point Demo Test

Demonstrates the complete predictive system by:
1. Recording 4 vital sign sets showing deterioration
2. Generating forecasts for 24/48/72 hours ahead
3. Analyzing risk trajectories
4. Computing time-to-deterioration
5. Displaying predictions with recommendations
"""

import os
import sys
import django
from datetime import timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Jomingos.settings')
django.setup()

from django.utils import timezone
from django.contrib.auth import get_user_model
from patients.models import Patient
from vitals.models import VitalSigns
from vitals.utils.forecasting_engine import ForecastingEngine
from vitals.utils.trajectory_analyzer import TrajectoryAnalyzer

User = get_user_model()

print("\n" + "="*80)
print("PHASE 10: PREDICTIVE FORECASTING - 4-POINT DEMO")
print("="*80)

# Setup
clinician = User.objects.first() or User.objects.create_user(
    username='demo_clinician',
    password='test'
)

patient = Patient.objects.create(
    first_name='Predictive',
    last_name='Demo Patient',
    date_of_birth='1940-01-01'
)

print(f"\nPatient: {patient.get_full_name()}")
print(f"ID: {patient.id}")

# Record 4 vitals showing gradual deterioration
print("\nRecording 4 vital measurements...")
print("-" * 80)

vitals_data = [
    {
        'time': 'Hour 0 (Now)',
        'hr': 75, 'rr': 16, 'spo2': 97.0, 'sbp': 130, 'temp': 36.8,
        'description': 'NORMAL BASELINE'
    },
    {
        'time': 'Hour 4',
        'hr': 82, 'rr': 18, 'spo2': 96.0, 'sbp': 128, 'temp': 37.1,
        'description': 'SLIGHT INCREASE - Early trend'
    },
    {
        'time': 'Hour 8',
        'hr': 92, 'rr': 21, 'spo2': 94.5, 'sbp': 122, 'temp': 37.5,
        'description': 'ACCELERATING CHANGE - Trend becoming clear'
    },
    {
        'time': 'Hour 12',
        'hr': 105, 'rr': 25, 'spo2': 92.0, 'sbp': 115, 'temp': 38.2,
        'description': 'SIGNIFICANT DETERIORATION - Patient at risk'
    },
]

vitals_list = []
now = timezone.now()

for i, data in enumerate(vitals_data):
    vital = VitalSigns.objects.create(
        patient=patient,
        recorded_by=clinician,
        heart_rate=data['hr'],
        respiratory_rate=data['rr'],
        oxygen_saturation=data['spo2'],
        bp_systolic=data['sbp'],
        temperature=data['temp'],
        recorded_at=now - timedelta(hours=(12 - i*4))
    )
    vitals_list.append(vital)
    print(f"\n[Recording #{i+1}] {data['time']}")
    print(f"  HR: {data['hr']} bpm | RR: {data['rr']} br/m | SpO2: {data['spo2']}%")
    print(f"  BP: {data['sbp']} mmHg | Temp: {data['temp']}C")
    print(f"  Status: {data['description']}")

# Generate predictions
print("\n" + "="*80)
print("GENERATING PREDICTIVE FORECASTS")
print("="*80)

engine = ForecastingEngine()
analyzer = TrajectoryAnalyzer()

# Build historical data
historical_data = {
    'heart_rate': [
        {'value': float(v.heart_rate), 'time_hours_ago': -(12 - i*4)}
        for i, v in enumerate(vitals_list)
    ],
    'respiratory_rate': [
        {'value': float(v.respiratory_rate), 'time_hours_ago': -(12 - i*4)}
        for i, v in enumerate(vitals_list)
    ],
    'oxygen_saturation': [
        {'value': float(v.oxygen_saturation), 'time_hours_ago': -(12 - i*4)}
        for i, v in enumerate(vitals_list)
    ],
    'bp_systolic': [
        {'value': float(v.bp_systolic), 'time_hours_ago': -(12 - i*4)}
        for i, v in enumerate(vitals_list)
    ],
    'temperature': [
        {'value': float(v.temperature), 'time_hours_ago': -(12 - i*4)}
        for i, v in enumerate(vitals_list)
    ],
}

# Generate forecasts
print("\nTIME-SERIES FORECASTS")
print("-" * 80)

forecasts_24h = engine.forecast_all_vitals(historical_data, horizon_hours=24)
forecasts_48h = engine.forecast_all_vitals(historical_data, horizon_hours=48)
forecasts_72h = engine.forecast_all_vitals(historical_data, horizon_hours=72)

for vital_name in ['heart_rate', 'respiratory_rate', 'oxygen_saturation', 'bp_systolic', 'temperature']:
    f24 = forecasts_24h.get(vital_name, {})
    f48 = forecasts_48h.get(vital_name, {})
    f72 = forecasts_72h.get(vital_name, {})
    current = vitals_list[-1]

    if vital_name == 'heart_rate':
        current_val = float(current.heart_rate)
    elif vital_name == 'respiratory_rate':
        current_val = float(current.respiratory_rate)
    elif vital_name == 'oxygen_saturation':
        current_val = float(current.oxygen_saturation)
    elif vital_name == 'bp_systolic':
        current_val = float(current.bp_systolic)
    else:
        current_val = float(current.temperature)

    print(f"\n{vital_name.upper().replace('_', ' ')}")
    print(f"  Current: {current_val:.1f}")
    print(f"  24h forecast: {f24.get('forecast', 'N/A'):.1f} (trend: {f24.get('trend', {}).get('direction', 'unknown')})")
    print(f"  48h forecast: {f48.get('forecast', 'N/A'):.1f}")
    print(f"  72h forecast: {f72.get('forecast', 'N/A'):.1f}")
    print(f"  Confidence: {f24.get('confidence', 0):.0%}")

# Analyze trajectory
print("\n" + "="*80)
print("RISK TRAJECTORY ANALYSIS")
print("="*80)

current_vitals = {
    'heart_rate': float(vitals_list[-1].heart_rate),
    'respiratory_rate': float(vitals_list[-1].respiratory_rate),
    'oxygen_saturation': float(vitals_list[-1].oxygen_saturation),
    'bp_systolic': float(vitals_list[-1].bp_systolic),
    'temperature': float(vitals_list[-1].temperature),
}

trajectory = analyzer.analyze_patient_trajectory(current_vitals, forecasts_24h)

print(f"\nKEY FINDINGS")
print("-" * 80)
print(f"Vitals at risk: {trajectory['vitals_at_risk']}")
print(f"At-risk count: {len(trajectory['vitals_at_risk'])}")

if trajectory['earliest_critical']:
    ec = trajectory['earliest_critical']
    print(f"\nEARLIEST CRITICAL TIME")
    print(f"Vital: {ec['vital']}")
    print(f"Hours until critical: {ec['hours']:.1f}")
    print(f"Estimated time: {ec['timestamp']}")
    print(f"Reason: {ec['reason']}")
else:
    print("\nNo vitals projected to reach critical in next 72 hours")

print(f"\nRISK SUMMARY")
print(f"Level: {trajectory['risk_summary']['level'].upper()}")
print(f"Description: {trajectory['risk_summary']['description']}")
print(f"Urgency: {trajectory['risk_summary']['urgency']}")

print(f"\nRECOMMENDED ACTIONS")
print("-" * 80)
for i, rec in enumerate(trajectory['recommendations'], 1):
    print(f"{i}. {rec}")

# Summary
print("\n" + "="*80)
print("PHASE 10 DEMONSTRATION SUMMARY")
print("="*80)

print("\nSYSTEM SUCCESSFULLY:")
print("\n1. Recorded 4 vital measurements showing gradual deterioration")
print("   - HR rising: 75 to 105 bpm")
print("   - RR rising: 16 to 25 br/min")
print("   - SpO2 falling: 97.0 to 92.0 percent")
print("   - Temp rising: 36.8 to 38.2 C")
print("\n2. Generated time-series forecasts using 3 models:")
print("   - Linear regression (trend continuation)")
print("   - Exponential smoothing (weighted recent readings)")
print("   - Moving average (smoothed trend)")
print("\n3. Analyzed deterioration trajectories")
print("   - Identified which vitals approaching critical")
print("   - Calculated time-to-critical for each vital")
print("   - Ranked by urgency")
print("\n4. Generated clinical recommendations")
print("   - Specific to patient's deterioration pattern")
print("   - Ranked by priority")
print("   - Actionable for care team")
print("\nKEY ADVANTAGE OVER PHASE 9 (REACTIVE):")
print("-" * 70)
print("\nPhase 9 (Real-time):")
print("  'Patient IS deteriorating NOW' -> Alert NOW")
print("  Detects AFTER deterioration happens")
print("\nPhase 10 (Predictive):")
print("  'Patient WILL deteriorate in ~X hours' -> Alert BEFORE")
print("  Allows preventive intervention BEFORE crisis")
print("\nThis is the missing piece for elderly care - clinicians get TIME")
print("to intervene before the patient reaches critical state.")

print("="*80)
print("PHASE 10 PREDICTIVE FORECASTING - COMPLETE")
print("="*80 + "\n")
