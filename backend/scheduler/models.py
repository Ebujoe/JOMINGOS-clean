from django.db import models


class StaffAvailability(models.Model):
    DAYS = [
        ("Monday", "Monday"),
        ("Tuesday", "Tuesday"),
        ("Wednesday", "Wednesday"),
        ("Thursday", "Thursday"),
        ("Friday", "Friday"),
        ("Saturday", "Saturday"),
        ("Sunday", "Sunday"),
    ]

    SHIFTS = [
        ("Morning", "Morning"),
        ("Evening", "Evening"),
        ("Night", "Night"),
    ]

    staff = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="scheduler_availability",
        limit_choices_to={
            "role__in": ["nurse", "care_assistant"]
        },
        null=True,
        blank=True
    )

    day = models.CharField(
        max_length=20,
        choices=DAYS
    )

    shift = models.CharField(
        max_length=20,
        choices=SHIFTS
    )

    available = models.BooleanField(default=True)

    max_hours_per_week = models.PositiveIntegerField(default=40)

    def __str__(self):
        return (
            f"{self.staff.get_full_name() or self.staff.username}"
            f" - {self.day} - {self.shift}"
        )


class ShiftRequirement(models.Model):
    DAYS = StaffAvailability.DAYS
    SHIFTS = StaffAvailability.SHIFTS

    day = models.CharField(
        max_length=20,
        choices=DAYS
    )

    shift = models.CharField(
        max_length=20,
        choices=SHIFTS
    )

    nurses_required = models.PositiveIntegerField(default=1)

    care_assistants_required = models.PositiveIntegerField(default=2)

    def __str__(self):
        return f"{self.day} - {self.shift}"