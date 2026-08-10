from django.shortcuts import render
from django.http import JsonResponse
from .models import VitalSigns
from patients.models import Patient


def vitals_test_dashboard(request):
    """Simple test dashboard showing all vitals"""
    vitals = VitalSigns.objects.all().select_related('patient').order_by('-recorded_at')

    context = {
        'vitals': vitals,
        'total_vitals': vitals.count(),
        'total_patients': Patient.objects.count(),
        'total_alerts': sum(v.deterioration_alerts.count() for v in vitals),
    }

    return render(request, 'vitals/test_dashboard.html', context)


def vitals_api(request):
    """JSON API for vitals data"""
    vitals = VitalSigns.objects.all().select_related('patient').order_by('-recorded_at')

    data = {
        'total': vitals.count(),
        'vitals': []
    }

    for v in vitals[:20]:
        alerts = v.deterioration_alerts.all()
        data['vitals'].append({
            'id': v.id,
            'patient': f"{v.patient.first_name} {v.patient.last_name}",
            'recorded_at': v.recorded_at.isoformat(),
            'heart_rate': v.heart_rate,
            'respiratory_rate': v.respiratory_rate,
            'oxygen_saturation': float(v.oxygen_saturation) if v.oxygen_saturation else None,
            'bp_systolic': v.bp_systolic,
            'bp_diastolic': v.bp_diastolic,
            'temperature': float(v.temperature) if v.temperature else None,
            'news2_total': v.news2_total,
            'news2_level': v.news2_level,
            'news2_scores': {
                'hr': v.news2_hr_score,
                'rr': v.news2_respiratory_score,
                'spo2': v.news2_spo2_score,
                'bp': v.news2_bp_score,
                'temp': v.news2_temp_score,
            },
            'alerts': [
                {
                    'priority': alert.priority,
                    'reason': alert.trigger_reason,
                    'triggered_at': alert.triggered_at.isoformat(),
                }
                for alert in alerts
            ]
        })

    return JsonResponse(data)
