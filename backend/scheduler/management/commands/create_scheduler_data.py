from django.core.management.base import BaseCommand

from accounts.models import User
from scheduler.models import StaffAvailability, ShiftRequirement


class Command(BaseCommand):
    help = "Create scheduler availability using real staff accounts"

    def handle(self, *args, **options):

        days = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]

        shifts = [
            "Morning",
            "Evening",
            "Night",
        ]

        # Remove old scheduler availability only
        StaffAvailability.objects.all().delete()
        ShiftRequirement.objects.all().delete()

        nurses = User.objects.filter(
            role="nurse",
            is_active=True
        )

        care_assistants = User.objects.filter(
            role="care_assistant",
            is_active=True
        )

        staff_members = list(nurses) + list(care_assistants)

        if not staff_members:
            self.stdout.write(
                self.style.ERROR(
                    "No active nurses or care assistants found."
                )
            )
            return

        # --------------------------------------
        # CREATE AVAILABILITY
        # --------------------------------------
        for staff_index, staff in enumerate(staff_members):

            for day_index, day in enumerate(days):

                for shift_index, shift in enumerate(shifts):

                    # Creates slightly different availability patterns
                    available = (
                        staff_index
                        + day_index
                        + shift_index
                    ) % 4 != 0

                    StaffAvailability.objects.create(
                        staff=staff,
                        day=day,
                        shift=shift,
                        available=available,
                        max_hours_per_week=40,
                    )

        # --------------------------------------
        # SHIFT REQUIREMENTS
        # --------------------------------------
        for day in days:

            for shift in shifts:

                if shift == "Morning":
                    nurses_required = 2
                    care_required = 3

                elif shift == "Evening":
                    nurses_required = 2
                    care_required = 3

                else:
                    nurses_required = 1
                    care_required = 2

                ShiftRequirement.objects.create(
                    day=day,
                    shift=shift,
                    nurses_required=nurses_required,
                    care_assistants_required=care_required,
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Scheduler data created using real staff accounts."
            )
        )

        self.stdout.write(
            f"Nurses found: {nurses.count()}"
        )

        self.stdout.write(
            f"Care assistants found: {care_assistants.count()}"
        )

        self.stdout.write(
            f"Availability records: "
            f"{StaffAvailability.objects.count()}"
        )

        self.stdout.write(
            f"Shift requirements: "
            f"{ShiftRequirement.objects.count()}"
        )