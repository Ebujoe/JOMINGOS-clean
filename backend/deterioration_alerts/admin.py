from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    TrendAnalysis, DeteriorationAlert, AlertSuppressionRule,
    DeteriorationEventLog
)


@admin.register(TrendAnalysis)
class TrendAnalysisAdmin(admin.ModelAdmin):
    list_display = ('patient', 'severity_badge', 'risk_score_display', 'window_size', 'analysed_at')
    list_filter = ('severity', 'window_size', 'analysed_at')
    search_fields = ('patient__first_name', 'patient__last_name')
    readonly_fields = ('analysed_at',)

    def severity_badge(self, obj):
        colors = {
            'stable': '#10b981',
            'improving': '#3b82f6',
            'declining': '#f59e0b',
            'critical': '#ef4444'
        }
        color = colors.get(obj.severity, '#666')
        return format_html(
            '<span style="background: {}; color: white; padding: 6px 12px; border-radius: 6px; font-weight: bold; font-size: 12px;">{}</span>',
            color, obj.severity.upper()
        )
    severity_badge.short_description = "Severity"

    def risk_score_display(self, obj):
        return format_html(
            '<strong style="font-size: 16px; color: #ef4444;">{}%</strong>',
            obj.risk_score
        )
    risk_score_display.short_description = "Risk Score"


@admin.register(DeteriorationAlert)
class DeteriorationAlertAdmin(admin.ModelAdmin):
    list_display = ('patient_name', 'priority_badge', 'alert_type', 'status_badge', 'triggered_at')
    list_filter = ('alert_type', 'priority', 'status', 'triggered_at', 'is_suppressed')
    search_fields = ('patient__first_name', 'patient__last_name')
    readonly_fields = ('triggered_at', 'acknowledged_at', 'resolved_at', 'alert_details', 'related_vital_link')

    fieldsets = (
        ('Alert Information', {
            'fields': ('patient', 'alert_type', 'priority', 'status', 'is_suppressed')
        }),
        ('Trigger Details', {
            'fields': ('trigger_reason', 'trigger_value', 'related_vital_link', 'related_trend')
        }),
        ('Timeline', {
            'fields': ('triggered_at', 'acknowledged_by', 'acknowledged_at', 'resolved_at')
        }),
        ('Research & Analysis', {
            'fields': ('alert_details',),
            'classes': ('wide',)
        }),
    )

    def patient_name(self, obj):
        return f"{obj.patient.first_name} {obj.patient.last_name}"
    patient_name.short_description = "Patient"

    def priority_badge(self, obj):
        colors = {
            'critical': '#ef4444',
            'high': '#f97316',
            'medium': '#eab308',
            'low': '#10b981'
        }
        color = colors.get(obj.priority, '#666')
        return format_html(
            '<span style="background: {}; color: white; padding: 6px 12px; border-radius: 6px; font-weight: bold; font-size: 12px;">{}</span>',
            color, obj.priority.upper()
        )
    priority_badge.short_description = "Priority"

    def status_badge(self, obj):
        colors = {
            'active': '#ef4444',
            'acknowledged': '#f59e0b',
            'resolved': '#10b981',
            'suppressed': '#6b7280'
        }
        color = colors.get(obj.status, '#666')
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 10px; border-radius: 4px; font-size: 11px;">{}</span>',
            color, obj.status.upper()
        )
    status_badge.short_description = "Status"

    def related_vital_link(self, obj):
        """Link to related vital signs"""
        if obj.related_vital:
            vital = obj.related_vital
            news2 = vital.news2_total
            url = reverse('admin:vitals_vitalsigns_change', args=[vital.id])
            return format_html(
                '<a href="{}" style="text-decoration: none; color: #2563eb; font-weight: 600;">View Vitals (NEWS2: {})</a>',
                url, news2
            )
        return "—"
    related_vital_link.short_description = "Related Vitals"

    def alert_details(self, obj):
        """Show detailed alert logic explanation"""
        vital = obj.related_vital

        if not vital:
            return "No related vital data"

        html = '''
        <div style="background: #f9fafb; padding: 16px; border-radius: 8px; border: 1px solid #e5e7eb;">
            <h3 style="margin-top: 0;">Alert Trigger Logic</h3>
            <p><strong>Research-Based Deterioration Detection:</strong></p>
            <p style="font-size: 14px; line-height: 1.6; color: #374151;">
                This alert was triggered by the ML-based deterioration detection system analyzing:
            </p>
            <table style="width: 100%; border-collapse: collapse; margin: 12px 0;">
                <tr style="background: #f3f4f6; border-bottom: 1px solid #e5e7eb;">
                    <td style="padding: 10px; font-weight: 600;">Vital Parameter</td>
                    <td style="padding: 10px; font-weight: 600;">Value</td>
                    <td style="padding: 10px; font-weight: 600;">NEWS2 Score</td>
                    <td style="padding: 10px; font-weight: 600;">Risk Level</td>
                </tr>
        '''

        # Heart Rate
        hr_color = 'green' if vital.news2_hr_score == 0 else 'orange' if vital.news2_hr_score <= 1 else 'red'
        html += f'''
                <tr style="border-bottom: 1px solid #e5e7eb;">
                    <td style="padding: 10px;">Heart Rate</td>
                    <td style="padding: 10px;"><strong>{vital.heart_rate or '-'} bpm</strong></td>
                    <td style="padding: 10px; color: {hr_color}; font-weight: bold;">{vital.news2_hr_score}</td>
                    <td style="padding: 10px;">
        '''
        if vital.news2_hr_score == 0:
            html += '<span style="color: green;">Normal</span>'
        elif vital.news2_hr_score <= 1:
            html += '<span style="color: orange;">Elevated</span>'
        else:
            html += '<span style="color: red;">Critical</span>'
        html += '</td></tr>'

        # Respiratory Rate
        rr_color = 'green' if vital.news2_respiratory_score == 0 else 'orange' if vital.news2_respiratory_score <= 1 else 'red'
        html += f'''
                <tr style="border-bottom: 1px solid #e5e7eb;">
                    <td style="padding: 10px;">Respiratory Rate</td>
                    <td style="padding: 10px;"><strong>{vital.respiratory_rate or '-'} br/m</strong></td>
                    <td style="padding: 10px; color: {rr_color}; font-weight: bold;">{vital.news2_respiratory_score}</td>
                    <td style="padding: 10px;">
        '''
        if vital.news2_respiratory_score == 0:
            html += '<span style="color: green;">Normal</span>'
        elif vital.news2_respiratory_score <= 1:
            html += '<span style="color: orange;">Elevated</span>'
        else:
            html += '<span style="color: red;">Critical</span>'
        html += '</td></tr>'

        # SpO2
        spo2_color = 'green' if vital.news2_spo2_score == 0 else 'orange' if vital.news2_spo2_score <= 1 else 'red'
        html += f'''
                <tr style="border-bottom: 1px solid #e5e7eb;">
                    <td style="padding: 10px;">Blood Oxygen (SpO2)</td>
                    <td style="padding: 10px;"><strong>{vital.oxygen_saturation or '-'}%</strong></td>
                    <td style="padding: 10px; color: {spo2_color}; font-weight: bold;">{vital.news2_spo2_score}</td>
                    <td style="padding: 10px;">
        '''
        if vital.news2_spo2_score == 0:
            html += '<span style="color: green;">Normal</span>'
        elif vital.news2_spo2_score <= 1:
            html += '<span style="color: orange;">Elevated</span>'
        else:
            html += '<span style="color: red;">Critical</span>'
        html += '</td></tr>'

        # Temperature
        temp_color = 'green' if vital.news2_temp_score == 0 else 'orange' if vital.news2_temp_score <= 1 else 'red'
        html += f'''
                <tr style="border-bottom: 1px solid #e5e7eb;">
                    <td style="padding: 10px;">Temperature</td>
                    <td style="padding: 10px;"><strong>{vital.temperature or '-'}°C</strong></td>
                    <td style="padding: 10px; color: {temp_color}; font-weight: bold;">{vital.news2_temp_score}</td>
                    <td style="padding: 10px;">
        '''
        if vital.news2_temp_score == 0:
            html += '<span style="color: green;">Normal</span>'
        elif vital.news2_temp_score <= 1:
            html += '<span style="color: orange;">Elevated</span>'
        else:
            html += '<span style="color: red;">Critical</span>'
        html += '</td></tr>'

        # Blood Pressure
        bp_color = 'green' if vital.news2_bp_score == 0 else 'orange' if vital.news2_bp_score <= 1 else 'red'
        html += f'''
                <tr style="background: #f3f4f6; font-weight: bold;">
                    <td style="padding: 10px;">Blood Pressure</td>
                    <td style="padding: 10px;">{vital.bp_systolic or '-'}/{vital.bp_diastolic or '-'} mmHg</td>
                    <td style="padding: 10px; color: {bp_color};">{vital.news2_bp_score}</td>
                    <td style="padding: 10px;">
        '''
        if vital.news2_bp_score == 0:
            html += '<span style="color: green;">Normal</span>'
        elif vital.news2_bp_score <= 1:
            html += '<span style="color: orange;">Elevated</span>'
        else:
            html += '<span style="color: red;">Critical</span>'
        html += '</td></tr>'

        # Total NEWS2
        total_news2 = vital.news2_total
        total_color = '#10b981' if total_news2 <= 4 else '#f59e0b' if total_news2 <= 6 else '#ef4444'
        html += f'''
                <tr style="background: {total_color}; color: white; font-weight: bold;">
                    <td style="padding: 12px; font-size: 14px;">TOTAL NEWS2 SCORE</td>
                    <td style="padding: 12px;"></td>
                    <td style="padding: 12px; font-size: 18px;">{total_news2}</td>
                    <td style="padding: 12px;">
        '''
        if total_news2 <= 4:
            html += 'LOW RISK'
        elif total_news2 <= 6:
            html += 'MEDIUM RISK'
        else:
            html += 'HIGH RISK'
        html += '</td></tr></table>'

        html += f'''
            <p style="margin-top: 12px; padding-top: 12px; border-top: 1px solid #e5e7eb; font-size: 14px; color: #374151;">
                <strong>Alert Trigger Reason:</strong> {obj.trigger_reason}
            </p>
            <p style="font-size: 13px; color: #666; margin: 8px 0;">
                <strong>Recorded By:</strong> {vital.recorded_by.get_full_name() or vital.recorded_by.username}<br/>
                <strong>Recorded At:</strong> {vital.recorded_at.strftime('%d/%m/%Y %H:%M:%S')}
            </p>
        </div>
        '''

        return format_html(html)
    alert_details.short_description = "Research-Based Deterioration Logic"


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
