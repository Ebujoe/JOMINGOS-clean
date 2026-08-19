from django.core.management.base import BaseCommand
from accounts.models import User


class Command(BaseCommand):
    help = "Create test nurses and care assistants in accounts.User"

    def handle(self, *args, **options):

        staff = [
            ("James", "Wilson", "james.wilson@example.com", "nurse"),
            ("Emma", "Taylor", "emma.taylor@example.com", "nurse"),
            ("David", "Brown", "david.brown@example.com", "nurse"),
            ("Sarah", "Clark", "sarah.clark@example.com", "nurse"),
            ("Priya", "Patel", "priya.patel@example.com", "nurse"),
            ("Daniel", "Evans", "daniel.evans@example.com", "nurse"),
            ("Sophie", "Martin", "sophie.martin@example.com", "nurse"),
            ("Michael", "Lewis", "michael.lewis@example.com", "nurse"),
            ("Olivia", "Harris", "olivia.harris@example.com", "nurse"),
            ("Thomas", "Walker", "thomas.walker@example.com", "nurse"),

            ("John", "Carter", "john.carter@example.com", "care_assistant"),
            ("Mary", "Johnson", "mary.johnson@example.com", "care_assistant"),
            ("Grace", "Hall", "grace.hall@example.com", "care_assistant"),
            ("Alex", "Turner", "alex.turner@example.com", "care_assistant"),
            ("Lucy", "White", "lucy.white@example.com", "care_assistant"),
            ("George", "King", "george.king@example.com", "care_assistant"),
            ("Amelia", "Green", "amelia.green@example.com", "care_assistant"),
            ("Henry", "Scott", "henry.scott@example.com", "care_assistant"),
            ("Sofia", "Adams", "sofia.adams@example.com", "care_assistant"),
            ("Jack", "Baker", "jack.baker@example.com", "care_assistant"),
        ]

        created_count = 0
        existing_count = 0

        for first_name, last_name, email, role in staff:

            username = f"{first_name}.{last_name}".lower()

            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "role": role,
                    "is_active": True,
                }
            )

            if created:
                user.set_password("Test1234!")
                user.save()
                created_count += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created: {user.get_full_name()} - {user.get_role_display()}"
                    )
                )
            else:
                existing_count += 1

                # Keep existing account but make sure role/data are correct
                user.first_name = first_name
                user.last_name = last_name
                user.email = email
                user.role = role
                user.is_active = True
                user.save()

                self.stdout.write(
                    self.style.WARNING(
                        f"Already exists, updated: {user.get_full_name()}"
                    )
                )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS("Staff import completed.")
        )
        self.stdout.write(f"Created: {created_count}")
        self.stdout.write(f"Existing/updated: {existing_count}")

        self.stdout.write(
            f"Active nurses: "
            f"{User.objects.filter(role='nurse', is_active=True).count()}"
        )

        self.stdout.write(
            f"Active care assistants: "
            f"{User.objects.filter(role='care_assistant', is_active=True).count()}"
        )