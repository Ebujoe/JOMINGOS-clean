from django.contrib import admin
from .models import (
    TrendAnalysis, DeteriorationAlert, AlertSuppressionRule,
    DeteriorationEventLog
)


@admin.register(TrendAnalysis)
class TrendAnalysisAdmin(admin.ModelAdmin):
    list_display = ('patient', 'window_size', 'severity', 'risk_score', 'analysed_at')
    list_filter = ('severity', 'window_size', 'analysed_at')
    search_fields = ('patient__first_name', 'patient__last_name')
    readonly_fields = ('analysed_at',)


@admin.register(DeteriorationAlert)
class DeteriorationAlertAdmin(admin.ModelAdmin):
    list_display = ('patient', 'alert_type', 'priority', 'status', 'triggered_at')
    list_filter = ('alert_type', 'priority', 'status', 'triggered_at', 'is_suppressed')
    search_fields = ('patient__first_name', 'patient__last_name')
    readonly_fields = ('triggered_at', 'acknowledged_at', 'resolved_at')


@admin.register(AlertSuppressionRule)
class AlertSuppressionRuleAdmin(admin.ModelAdmin):
    list_display = ('rule_type', 'is_active', 'created_at')
    list_filter = ('rule_type', 'is_active')


@admin.register(DeteriorationEventLog)
class DeteriorationEventLogAdmin(admin.ModelAdmin):
    list_display = ('patient', 'event_type', 'severity_at_event', 'logged_at')
    list_filter = ('event_type', 'severity_at_event', 'logged_at')
    search_fields = ('patient__first_name', 'patient__last_name')
    readonly_fields = ('data_snapshot', 'logged_at')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
