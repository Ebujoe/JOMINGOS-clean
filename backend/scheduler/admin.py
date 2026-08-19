from django.contrib import admin
from .models import StaffAvailability, ShiftRequirement


@admin.register(StaffAvailability)
class StaffAvailabilityAdmin(admin.ModelAdmin):
    list_display = (
        "staff",
        "get_role",
        "day",
        "shift",
        "available",
        "max_hours_per_week",
    )

    list_filter = (
        "staff__role",
        "day",
        "shift",
        "available",
    )

    search_fields = (
        "staff__first_name",
        "staff__last_name",
        "staff__username",
    )

    @admin.display(description="Role")
    def get_role(self, obj):
        return obj.staff.get_role_display()


@admin.register(ShiftRequirement)
class ShiftRequirementAdmin(admin.ModelAdmin):
    list_display = (
        "day",
        "shift",
        "nurses_required",
        "care_assistants_required",
    )

    list_filter = (
        "day",
        "shift",
    )