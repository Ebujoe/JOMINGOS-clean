"""
Dashboard Views for Real-time Monitoring

Provides views for:
- Patient risk dashboard
- Alert history
- Risk timeline visualization
- Critical patients list
- Real-time status updates
"""

from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from datetime import timedelta
from django.utils import timezone

from patients.models import Patient
from vitals.models import RiskAssessment, VitalSigns
from deterioration_alerts.models import DeteriorationAlert
from vitals.monitoring import RealtimeMonitor
from vitals.utils.explainability import ExplainabilityEngine


@login_required
def risk_dashboard(request):
    """
    Main risk dashboard showing all monitored patients.

    Displays:
    - Critical patients list
    - Recent alerts
    - Patient status cards
    """
    # Get summary data
    summary = RealtimeMonitor.get_dashboard_summary()

    # Get all patients with recent risk assessments
    now = timezone.now()
    one_hour_ago = now - timedelta(hours=1)

    # Patients with recent assessments
    recent_assessments = RiskAssessment.objects.filter(
        assessed_at__gte=one_hour_ago
    ).select_related('patient').order_by('-assessed_at')[:50]

    # Build patient status list
    patient_status = {}
    for assessment in recent_assessments:
        patient_id = assessment.patient_id
        if patient_id not in patient_status:
            patient_status[patient_id] = {
                'patient': assessment.patient,
                'risk_level': assessment.risk_level,
                'combined_risk': assessment.combined_risk,
                'assessed_at': assessment.assessed_at,
                'explanation': assessment.explanation_text,
                'recommendation': assessment.recommendation,
            }

    # Get critical alerts from last 24 hours
    critical_alerts = DeteriorationAlert.objects.filter(
        priority__in=['high', 'critical'],
        triggered_at__gte=now - timedelta(hours=24),
        status='active'
    ).select_related('patient').order_by('-triggered_at')[:20]

    context = {
        'summary': summary,
        'patient_status': list(patient_status.values()),
        'critical_alerts': critical_alerts,
        'total_patients_monitored': len(patient_status),
    }

    return render(request, 'vitals/risk_dashboard.html', context)


@login_required
def patient_risk_detail(request, patient_id):
    """
    Detailed risk view for a specific patient.

    Shows:
    - Current risk assessment
    - Risk history timeline
    - Contributing factors
    - Clinical recommendations
    - Alert history
    """
    patient = get_object_or_404(Patient, id=patient_id)

    # Get latest assessment
    latest_assessment = RiskAssessment.objects.filter(
        patient=patient
    ).order_by('-assessed_at').first()

    if not latest_assessment:
        context = {'patient': patient, 'no_assessments': True}
        return render(request, 'vitals/patient_risk_detail.html', context)

    # Get assessment history (last 10)
    assessment_history = RiskAssessment.objects.filter(
        patient=patient
    ).order_by('-assessed_at')[:10]

    # Get alert history (last 20)
    alert_history = DeteriorationAlert.objects.filter(
        patient=patient
    ).order_by('-triggered_at')[:20]

    # Generate explanations
    engine = ExplainabilityEngine()
    explanations = engine.explain_assessment(latest_assessment)
    narrative = engine.generate_assessment_narrative(latest_assessment)

    # Get contributing factors with details
    factors = explanations['contributing_factors']

    # Get recent vital signs
    recent_vitals = VitalSigns.objects.filter(
        patient=patient
    ).order_by('-recorded_at')[:5]

    context = {
        'patient': patient,
        'latest_assessment': latest_assessment,
        'assessment_history': assessment_history,
        'alert_history': alert_history,
        'explanations': explanations,
        'narrative': narrative,
        'factors': factors,
        'next_actions': explanations['next_actions'],
        'recent_vitals': recent_vitals,
        'recommendation': explanations['recommendation'],
    }

    return render(request, 'vitals/patient_risk_detail.html', context)


@login_required
@require_http_methods(["GET"])
def alert_history(request):
    """
    Display alert history with filtering.

    Supports filters:
    - patient_id
    - priority (critical, high, medium, low)
    - status (active, acknowledged, resolved)
    - date range
    """
    # Get filter parameters
    patient_id = request.GET.get('patient_id')
    priority = request.GET.get('priority')
    status = request.GET.get('status', 'active')
    days = int(request.GET.get('days', 7))

    # Build query
    alerts = DeteriorationAlert.objects.all()

    if patient_id:
        alerts = alerts.filter(patient_id=patient_id)

    if priority:
        alerts = alerts.filter(priority=priority)

    if status:
        alerts = alerts.filter(status=status)

    # Date filter
    cutoff_date = timezone.now() - timedelta(days=days)
    alerts = alerts.filter(triggered_at__gte=cutoff_date)

    # Order and limit
    alerts = alerts.select_related('patient').order_by('-triggered_at')[:100]

    context = {
        'alerts': alerts,
        'alert_count': alerts.count(),
        'filters': {
            'patient_id': patient_id,
            'priority': priority,
            'status': status,
            'days': days,
        }
    }

    return render(request, 'vitals/alert_history.html', context)


@login_required
@require_http_methods(["GET"])
def critical_patients_list(request):
    """
    Display current critical patients requiring immediate attention.
    """
    critical_patients = RealtimeMonitor.get_critical_patients()

    # Fetch detailed info for each critical patient
    patient_details = []
    for patient_info in critical_patients:
        try:
            patient = Patient.objects.get(id=patient_info['patient_id'])
            latest_assessment = RiskAssessment.objects.filter(
                patient=patient
            ).order_by('-assessed_at').first()

            latest_alert = DeteriorationAlert.objects.filter(
                patient=patient,
                priority='critical',
                status='active'
            ).order_by('-triggered_at').first()

            patient_details.append({
                'patient': patient,
                'first_alert': patient_info['first_alert'],
                'last_update': patient_info['last_update'],
                'latest_assessment': latest_assessment,
                'latest_alert': latest_alert,
                'hours_critical': calculate_hours_critical(patient_info['first_alert']),
            })
        except Patient.DoesNotExist:
            pass

    context = {
        'critical_patients': patient_details,
        'total_critical': len(patient_details),
    }

    return render(request, 'vitals/critical_patients.html', context)


@login_required
@require_http_methods(["GET"])
def api_patient_risk_realtime(request, patient_id):
    """
    API endpoint for real-time patient risk status.

    Used by dashboard for live updates via polling/WebSocket.
    """
    patient = get_object_or_404(Patient, id=patient_id)

    # Get current risk status
    risk_status = RealtimeMonitor.get_patient_risk(patient_id)

    if not risk_status:
        # Fallback to latest assessment if not in cache
        latest = RiskAssessment.objects.filter(
            patient=patient
        ).order_by('-assessed_at').first()

        if latest:
            risk_status = {
                'patient_id': patient_id,
                'risk_level': latest.risk_level,
                'combined_risk': float(latest.combined_risk),
                'news2_score': latest.news2_total,
                'trend_score': latest.trend_score,
                'assessed_at': latest.assessed_at.isoformat(),
            }
        else:
            return JsonResponse({'error': 'No assessments'}, status=404)

    # Get recent alerts
    recent_alerts = DeteriorationAlert.objects.filter(
        patient=patient,
        triggered_at__gte=timezone.now() - timedelta(hours=1)
    ).values('id', 'priority', 'status', 'triggered_at').order_by('-triggered_at')

    response = {
        'patient_id': patient_id,
        'risk': risk_status,
        'recent_alerts': list(recent_alerts),
        'timestamp': timezone.now().isoformat(),
    }

    return JsonResponse(response)


@login_required
@require_http_methods(["GET"])
def api_alert_stream(request):
    """
    API endpoint for real-time alert stream.

    Returns recent alerts for dashboard feed.
    """
    limit = int(request.GET.get('limit', 20))
    alerts = RealtimeMonitor.get_alert_stream(limit)

    return JsonResponse({
        'alerts': alerts,
        'count': len(alerts),
        'timestamp': timezone.now().isoformat(),
    })


@login_required
@require_http_methods(["GET"])
def api_dashboard_summary(request):
    """
    API endpoint for dashboard summary data.

    Returns critical patients, alerts, and statistics.
    """
    summary = RealtimeMonitor.get_dashboard_summary()

    return JsonResponse({
        'summary': summary,
        'timestamp': timezone.now().isoformat(),
    })


# Helper functions

def calculate_hours_critical(first_alert_iso):
    """Calculate hours since patient became critical"""
    from datetime import datetime
    first_alert = datetime.fromisoformat(first_alert_iso.replace('Z', '+00:00'))
    now = timezone.now()
    delta = now - first_alert
    return int(delta.total_seconds() / 3600)
