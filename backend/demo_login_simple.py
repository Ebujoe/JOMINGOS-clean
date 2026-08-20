"""
Simple test to verify login works via API
"""
from django.test import Client
from django.test import TestCase
from accounts.models import User
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Jomingos.settings')
import django
django.setup()

# Create test client
client = Client()

# Test 1: Try to login
print("=" * 60)
print("TEST: Login with nurse/nurse123")
print("=" * 60)

response = client.post('/accounts/login/', {
    'username': 'nurse',
    'password': 'nurse123',
})

print(f"Status Code: {response.status_code}")
print(f"Redirect URL: {response.get('Location', 'No redirect')}")

# Check if user is authenticated
if response.status_code == 302:
    print("✓ Login form accepted - redirected")
    redirect_url = response['Location']
    
    # Follow the redirect
    follow_response = client.get(redirect_url)
    print(f"Redirect response status: {follow_response.status_code}")
else:
    print("✗ Login failed - form validation error")
    print(f"Response content: {response.content.decode()[:500]}")

# Test 2: Check if session is created
print(f"\nSession data: {client.session}")
