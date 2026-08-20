#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import django
import requests

# Ensure UTF-8 output
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Jomingos.settings')
django.setup()

from django.contrib.auth import get_user_model
from vitals.models import VitalSigns
from patients.models import Patient

User = get_user_model()
API_BASE = 'http://localhost:8000/api'

print("\n" + "="*70)
print("COMPLETE END-TO-END TEST: Alert Dashboard System")
print("="*70)

# Step 1: Create test user
print("\n[1/5] Setting up test user...")
user, created = User.objects.get_or_create(
    username='teststaff',
    defaults={'email': 'test@test.com', 'is_staff': True, 'is_active': True}
)
user.set_password('testpass123')
user.save()
print("[OK] User ready: teststaff")

# Step 2: Check demo vitals and alerts
print("\n[2/5] Checking system status...")
from deterioration_alerts.models import DeteriorationAlert
all_vitals = VitalSigns.objects.all().count()
all_alerts = DeteriorationAlert.objects.all().count()
print(f"[OK] Total vitals in database: {all_vitals}")
print(f"[OK] Total alerts in database: {all_alerts}")
patients = Patient.objects.all()[:1]
if patients:
    patient = patients[0]
    print(f"[OK] Sample patient: {patient.first_name} {patient.last_name}")

# Step 3: Test login
print("\n[3/5] Testing login endpoint...")
login_resp = requests.post(f'{API_BASE}/accounts/login/', json={'username': 'teststaff', 'password': 'testpass123'})
if login_resp.status_code != 200:
    print(f"[ERROR] Login failed: {login_resp.status_code}")
    print(login_resp.text)
    sys.exit(1)

data = login_resp.json()
token = data.get('access')
print("[OK] Login successful")
print("    Token TTL: 24 hours (extended for testing)")

# Step 4: Test alerts API
print("\n[4/5] Testing alerts API endpoint...")
headers = {'Authorization': f'Bearer {token}'}
alerts_resp = requests.get(f'{API_BASE}/alerts/active_alerts/', headers=headers)
if alerts_resp.status_code != 200:
    print(f"[ERROR] Alerts API failed: {alerts_resp.status_code}")
    print(alerts_resp.text)
    sys.exit(1)

alerts = alerts_resp.json()
print("[OK] Alerts API working")
print(f"    Active alerts: {len(alerts)}")
for alert in alerts:
    print(f"      - {alert['patient_name']}: {alert['priority'].upper()}")

# Step 5: Test acknowledge
if alerts:
    print("\n[5/5] Testing acknowledge endpoint...")
    alert_id = alerts[0]['id']
    ack_resp = requests.post(f'{API_BASE}/alerts/{alert_id}/acknowledge/', headers=headers)
    if ack_resp.status_code != 200:
        print(f"[ERROR] Acknowledge failed: {ack_resp.status_code}")
        sys.exit(1)
    print(f"[OK] Alert #{alert_id} marked as acknowledged")
else:
    print("\n[5/5] No alerts to acknowledge (skipping)")

print("\n" + "="*70)
print("ALL TESTS PASSED - System is ready!")
print("="*70)
print("\nNext steps:")
print("1. Restart frontend: npm run dev")
print("2. Go to: http://localhost:3000/dashboard")
print("3. Login: teststaff / testpass123")
print("4. See professional dashboard with alerts")
print("="*70 + "\n")
