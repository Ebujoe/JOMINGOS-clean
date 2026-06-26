import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Jomingos.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

user, created = User.objects.get_or_create(
    username='teststaff',
    defaults={'email': 'test@test.com', 'is_staff': True}
)

user.set_password('testpass123')
user.save()

print(f"User: {user.username} (created={created})")
print(f"Email: {user.email}")
