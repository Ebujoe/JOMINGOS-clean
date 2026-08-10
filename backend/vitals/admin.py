from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Q
from .models import VitalSigns


@admin.register(VitalSigns)
class VitalSignsAdmin(admin.ModelAdmin):
    """
    Professional admin interface for Vital Signs with NEWS2 scoring
    and deterioration risk assessment.
    """

    list_display = (
        'patient_name',
        'recorded_at_display',
        'heart_rate_display',
        'respiratory_rate_display',
        'oxygen_saturation_display',
        'blood_pressure_display',
        'news2_score_display',
        'risk_level_display'
    )

    list_filter = (
        'recorded_at',
        'patient',
    )

    search_fields = ('patient__first_name', 'patient__last_name', 'patient__id')

    readonly_fields = (
        'recorded_at',
        'news2_display',
        'deterioration_status',
        'related_alerts',
    )

    fieldsets = (
        ('Patient Information', {
            'fields': ('patient', 'recorded_by', 'recorded_at')
        }),
        ('Vital Signs', {
            'fields': (
                'heart_rate',
                'respiratory_rate',
                'oxygen_saturation',
                'temperature',
                'blood_pressure_display',
                'blood_glucose',
                'weight_kg',
                'pain_score'
            ),
            'classes': ('wide',),
            'description': 'Record patient vital signs. NEWS2 score will be calculated automatically.'
        }),
        ('NEWS2 Assessment', {
            'fields': (
                'news2_display',
                'deterioration_status',
            ),
            'classes': ('collapse',),
            'description': 'National Early Warning Score 2 (NEWS2) assessment based on vital signs'
        }),
        ('Related Alerts & Notes', {
            'fields': (
                'related_alerts',
                'notes'
            ),
            'classes': ('wide',)
        }),
    )

    def patient_name(self, obj):
        return f"{obj.patient.first_name} {obj.patient.last_name}"
    patient_name.short_description = "Patient"
    patient_name.admin_order_field = 'patient'

    def recorded_at_display(self, obj):
        return obj.recorded_at.strftime('%d/%m/%Y %H:%M')
    recorded_at_display.short_description = "Recorded"
    recorded_at_display.admin_order_field = 'recorded_at'

    def heart_rate_display(self, obj):
        hr = obj.heart_rate
        if not hr:
            return "—"
        score = obj.news2_hr_score
        color = 'green' if score == 0 else 'orange' if score <= 1 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} bpm</span>',
            color, hr
        )
    heart_rate_display.short_description = "HR"

    def respiratory_rate_display(self, obj):
        rr = obj.respiratory_rate
        if not rr:
            return "—"
        score = obj.news2_respiratory_score
        color = 'green' if score == 0 else 'orange' if score <= 1 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} br/m</span>',
            color, rr
        )
    respiratory_rate_display.short_description = "RR"

    def oxygen_saturation_display(self, obj):
        spo2 = obj.oxygen_saturation
        if not spo2:
            return "—"
        score = obj.news2_spo2_score
        color = 'green' if score == 0 else 'orange' if score <= 1 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}%</span>',
            color, spo2
        )
    oxygen_saturation_display.short_description = "SpO2"

    def blood_pressure_display(self, obj):
        if not obj.bp_systolic:
            return "—"
        score = obj.news2_bp_score
        color = 'green' if score == 0 else 'orange' if score <= 1 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}/{}</span>',
            color, obj.bp_systolic, obj.bp_diastolic
        )
    blood_pressure_display.short_description = "BP"

    def news2_score_display(self, obj):
        score = obj.news2_total
        if score <= 4:
            color = '#10b981'  # green
            level = 'LOW'
        elif score <= 6:
            color = '#f59e0b'  # orange
            level = 'MEDIUM'
        else:
            color = '#ef4444'  # red
            level = 'HIGH'

        return format_html(
            '<span style="background-color: {}; color: white; padding: 6px 12px; border-radius: 6px; font-weight: bold; font-size: 12px;">{} - {}</span>',
            color, score, level
        )
    news2_score_display.short_description = "NEWS2 Score"
    news2_score_display.admin_order_field = 'news2_total'

    def risk_level_display(self, obj):
        level = obj.news2_level
        if level == 'low':
            emoji = '✓'
            color = '#10b981'
        elif level == 'medium':
            emoji = '⚡'
            color = '#f59e0b'
        else:
            emoji = '🚨'
            color = '#ef4444'

        return format_html(
            '<span style="color: {}; font-size: 18px; font-weight: bold;">{} {}</span>',
            color, emoji, level.upper()
        )
    risk_level_display.short_description = "Risk"

    def news2_display(self, obj):
        """Display detailed NEWS2 breakdown"""
        components = [
            ('Heart Rate Score', obj.news2_hr_score, f"{obj.heart_rate or '-'} bpm"),
            ('Respiratory Rate Score', obj.news2_respiratory_score, f"{obj.respiratory_rate or '-'} br/m"),
            ('SpO2 Score', obj.news2_spo2_score, f"{obj.oxygen_saturation or '-'}%"),
            ('Temperature Score', obj.news2_temp_score, f"{obj.temperature or '-'}°C"),
            ('BP Score', obj.news2_bp_score, f"{obj.bp_systolic or '-'}/{obj.bp_diastolic or '-'} mmHg"),
        ]

        html = '<table style="width: 100%; border-collapse: collapse;">'
        html += '<tr style="background: #f3f4f6; font-weight: bold; text-align: left; border-bottom: 2px solid #d1d5db;">'
        html += '<td style="padding: 10px;">Component</td>'
        html += '<td style="padding: 10px;">Score</td>'
        html += '<td style="padding: 10px;">Value</td>'
        html += '</tr>'

        total = 0
        for component, score, value in components:
            total += score
            score_color = 'green' if score == 0 else 'orange' if score <= 2 else 'red'
            html += f'<tr style="border-bottom: 1px solid #e5e7eb;"><td style="padding: 10px;">{component}</td>'
            html += f'<td style="padding: 10px; color: {score_color}; font-weight: bold; font-size: 18px;">{score}</td>'
            html += f'<td style="padding: 10px;">{value}</td></tr>'

        # Total row
        total_color = '#10b981' if total <= 4 else '#f59e0b' if total <= 6 else '#ef4444'
        html += f'<tr style="background: {total_color}; color: white; font-weight: bold;">'
        html += f'<td style="padding: 12px;">TOTAL NEWS2 SCORE</td>'
        html += f'<td style="padding: 12px; font-size: 24px;">{total}</td>'
        html += f'<td style="padding: 12px;"></td></tr>'
        html += '</table>'

        return format_html(html)
    news2_display.short_description = "NEWS2 Breakdown"

    def deterioration_status(self, obj):
        """Show deterioration status and risk assessment"""
        score = obj.news2_total

        if score <= 4:
            status = "✓ LOW RISK"
            description = "Patient is stable. Continue routine monitoring."
            bg_color = "#d1fae5"
            text_color = "#065f46"
        elif score <= 6:
            status = "⚠️ MEDIUM RISK"
            description = "Patient showing some abnormal vitals. Increase monitoring frequency."
            bg_color = "#fef3c7"
            text_color = "#78350f"
        else:
            status = "🚨 HIGH RISK / CRITICAL"
            description = "Patient deteriorating. Immediate clinical review required. Alert generated."
            bg_color = "#fee2e2"
            text_color = "#7f1d1d"

        html = f'''
        <div style="background: {bg_color}; color: {text_color}; padding: 16px; border-radius: 8px; border-left: 4px solid {text_color}; margin: 10px 0;">
            <strong style="font-size: 18px;">{status}</strong>
            <p style="margin: 8px 0 0 0; font-size: 14px;">{description}</p>
        </div>
        '''
        return format_html(html)
    deterioration_status.short_description = "Deterioration Status"

    def related_alerts(self, obj):
        """Show alerts triggered by these vitals"""
        alerts = obj.deterioration_alerts.all()

        if not alerts:
            return format_html(
                '<span style="color: #10b981; font-weight: bold;">✓ No alerts triggered</span>'
            )

        html = '<div>'
        for alert in alerts:
            priority_colors = {
                'critical': '#ef4444',
                'high': '#f97316',
                'medium': '#eab308',
                'low': '#10b981'
            }
            color = priority_colors.get(alert.priority, '#666')

            html += f'''
            <div style="background: #f3f4f6; padding: 12px; margin: 8px 0; border-left: 4px solid {color}; border-radius: 4px;">
                <strong style="color: {color}; text-transform: uppercase; font-size: 12px;">{alert.priority}</strong>
                <p style="margin: 4px 0; font-weight: 600;">{alert.alert_type.replace('_', ' ').title()}</p>
                <p style="margin: 4px 0; font-size: 13px;">{alert.trigger_reason}</p>
                <small style="color: #666;">Status: <strong>{alert.status}</strong> • Triggered: {alert.triggered_at.strftime('%d/%m %H:%M')}</small>
            </div>
            '''
        html += '</div>'

        return format_html(html)
    related_alerts.short_description = "Related Alerts"

    def has_add_permission(self, request):
        return True

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    ordering = ['-recorded_at']
