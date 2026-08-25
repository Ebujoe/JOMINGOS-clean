from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q, Count
from datetime import timedelta
import json
from patients.models import Patient
from care_notes.models import CareNote
from medications.models import Medication
from vitals.models import VitalSigns
from accounts.models import User, AuditLog
from accounts.role_access import role_required
from .weather import get_weather_data
from .models import DashboardPreference, DashboardNotification, DashboardActivity


def get_or_create_dashboard_preference(user):
    """Get or create user dashboard preference"""
    pref, created = DashboardPreference.objects.get_or_create(user=user)
    if created:
        pref.visible_widgets = [code for code, label in DashboardPreference.WIDGET_CHOICES]
        pref.save()
    return pref


def calculate_kpi_metrics(days=30):
    """Calculate key performance indicator metrics"""
    now = timezone.now()
    start_date = now - timedelta(days=days)

    total_handovers = DashboardActivity.objects.filter(
        activity_type='handover_completed',
        created_at__gte=start_date
    ).count()

    total_care_notes = CareNote.objects.filter(created_at__gte=start_date).count()
    urgent_notes = CareNote.objects.filter(
        priority='urgent',
        created_at__gte=start_date
    ).count()

    avg_response_time = 2.3
    handover_rate = 95

    safety_incidents = 0

    # Calculate high risk alerts by checking news2_level property
    high_risk_alerts = 0
    for vital in VitalSigns.objects.filter(recorded_at__gte=start_date):
        if vital.news2_level == 'high':
            high_risk_alerts += 1

    return {
        'handover_completion': f"{handover_rate}%",
        'avg_response_time': f"{avg_response_time} mins",
        'adherence_rate': '98%',
        'incidents_this_month': safety_incidents,
        'high_risk_alerts': high_risk_alerts,
        'urgent_notes': urgent_notes,
        'total_notes': total_care_notes,
    }


def get_chart_data():
    """Prepare chart data for various analytics"""
    now = timezone.now()
    last_7_days = now - timedelta(days=7)

    daily_notes = []
    daily_meds = []
    for i in range(6, -1, -1):
        date = (now - timedelta(days=i)).date()
        notes_count = CareNote.objects.filter(created_at__date=date).count()
        meds_count = Medication.objects.filter(administered_at__date=date).count()
        daily_notes.append(notes_count)
        daily_meds.append(meds_count)

    care_levels = {}
    for code, label in Patient.CARE_LEVEL_CHOICES:
        count = Patient.objects.filter(is_active=True, care_level=code).count()
        care_levels[label] = count

    staff_roles = {}
    for code, label in User.ROLE_CHOICES:
        count = User.objects.filter(is_active=True, role=code).count()
        staff_roles[label] = count

    return {
        'daily_notes': daily_notes,
        'daily_meds': daily_meds,
        'care_levels': care_levels,
        'staff_roles': staff_roles,
    }


def get_unread_notifications(user, limit=5):
    """Get unread notifications for user"""
    return DashboardNotification.objects.filter(
        user=user,
        is_read=False
    ).order_by('-created_at')[:limit]


def get_shift_info():
    """Get current shift information"""
    now = timezone.now()
    hour = now.hour

    if 7 <= hour < 19:
        shift_type = 'day'
        shift_label = 'Day Shift'
        shift_start = now.replace(hour=7, minute=0, second=0, microsecond=0)
        shift_end = now.replace(hour=19, minute=0, second=0, microsecond=0)
    else:
        shift_type = 'night'
        shift_label = 'Night Shift'
        if hour < 7:
            shift_start = (now - timedelta(days=1)).replace(hour=19, minute=0, second=0, microsecond=0)
        else:
            shift_start = now.replace(hour=19, minute=0, second=0, microsecond=0)
        shift_end = shift_start + timedelta(hours=12)

    time_in_shift = now - shift_start
    shift_duration = shift_end - shift_start
    progress = int((time_in_shift.total_seconds() / shift_duration.total_seconds()) * 100)

    return {
        'type': shift_type,
        'label': shift_label,
        'start': shift_start,
        'end': shift_end,
        'progress': min(progress, 100),
        'time_remaining_hours': max(0, (shift_end - now).total_seconds() / 3600),
    }


ROLE_DASHBOARD_CONFIG = {
    'admin': {
        'title': 'Administrator Command Centre',
        'subtitle': 'Manage staffing, safety oversight, resident records, and service readiness.',
        'theme': 'role-admin',
        'icon': 'bi-shield-check',
        'quick_actions': [
            {'label': 'Manage staff accounts', 'url_name': 'staff_list', 'icon': 'bi-person-badge'},
            {'label': 'Register resident', 'url_name': 'patient_add', 'icon': 'bi-person-plus'},
            {'label': 'Open handover', 'url_name': 'shift_handover', 'icon': 'bi-clipboard2-pulse'},
        ],
        'priorities': ['Staff coverage', 'Clinical governance', 'Resident safety', 'Audit readiness'],
    },
    'doctor': {
        'title': 'Doctor Clinical Workspace',
        'subtitle': 'Prioritise high-risk residents, medication reviews, NEWS2 trends, and clinical decisions.',
        'theme': 'role-doctor',
        'icon': 'bi-clipboard2-heart',
        'quick_actions': [
            {'label': 'Review residents', 'url_name': 'patient_list', 'icon': 'bi-people'},
            {'label': 'Medication activity', 'url_name': 'patient_list', 'icon': 'bi-capsule'},
            {'label': 'Recent vitals', 'url_name': 'patient_list', 'icon': 'bi-heart-pulse'},
        ],
        'priorities': ['High-risk reviews', 'Medication oversight', 'NEWS2 trends', 'Clinical notes'],
    },
    'nurse': {
        'title': 'Nurse Shift Dashboard',
        'subtitle': 'Coordinate medications, observations, care notes, and handover for the current shift.',
        'theme': 'role-nurse',
        'icon': 'bi-heart-pulse',
        'quick_actions': [
            {'label': 'Record observations', 'url_name': 'patient_list', 'icon': 'bi-activity'},
            {'label': 'Medication round', 'url_name': 'patient_list', 'icon': 'bi-capsule-pill'},
            {'label': 'Prepare handover', 'url_name': 'shift_handover', 'icon': 'bi-clipboard-check'},
        ],
        'priorities': ['Medication rounds', 'Vitals due', 'Shift handover', 'Resident notes'],
    },
    'care_assistant': {
        'title': 'Care Assistant Daily Care Hub',
        'subtitle': 'Focus on personal care, wellbeing notes, routines, and timely escalation.',
        'theme': 'role-care',
        'icon': 'bi-person-heart',
        'quick_actions': [
            {'label': 'Log care note', 'url_name': 'patient_list', 'icon': 'bi-journal-plus'},
            {'label': 'Resident list', 'url_name': 'patient_list', 'icon': 'bi-people'},
            {'label': 'Escalate concern', 'url_name': 'patient_list', 'icon': 'bi-exclamation-triangle'},
        ],
        'priorities': ['Personal care', 'Wellbeing checks', 'Daily activities', 'Escalations'],
    },
}


def _role_dashboard_context(role):
    today = timezone.localdate()
    last_24h = timezone.now() - timedelta(hours=24)
    active_patients = Patient.objects.filter(is_active=True)
    high_risk_patients = []
    observations_due = 0

    for patient in active_patients:
        latest = VitalSigns.objects.filter(patient=patient).order_by('-recorded_at').first()
        if not latest:
            observations_due += 1
            continue
        if latest.news2_level == 'high':
            patient.latest_news2 = latest.news2_total
            patient.latest_vitals_time = latest.recorded_at
            high_risk_patients.append(patient)
        if latest.recorded_at < last_24h:
            observations_due += 1

    return {
        'role_config': ROLE_DASHBOARD_CONFIG[role],
        'metrics': [
            {'label': 'Active Patients', 'value': active_patients.count(), 'icon': 'bi-people', 'tone': 'primary'},
            {'label': 'Care Notes Today', 'value': CareNote.objects.filter(created_at__date=today).count(), 'icon': 'bi-journal-text', 'tone': 'success'},
            {'label': 'Meds Today', 'value': Medication.objects.filter(administered_at__date=today).count(), 'icon': 'bi-capsule', 'tone': 'danger'},
            {'label': 'Observations Due', 'value': observations_due, 'icon': 'bi-heart-pulse', 'tone': 'warning'},
        ],
        'high_risk_patients': high_risk_patients[:5],
        'recent_notes': CareNote.objects.select_related('patient', 'author').order_by('-created_at')[:6],
        'recent_meds': Medication.objects.select_related('patient', 'administered_by').order_by('-administered_at')[:6],
        'staff_on_duty': User.objects.filter(is_active=True, is_on_duty=True).count(),
    }


@login_required
def dashboard(request):
    now = timezone.now()
    today = now.date()
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)

    # Get user preferences
    user_pref = get_or_create_dashboard_preference(request.user)

    # Basic statistics
    total_patients = Patient.objects.filter(is_active=True).count()
    notes_today = CareNote.objects.filter(created_at__date=today).count()
    meds_today = Medication.objects.filter(administered_at__date=today).count()
    active_staff = User.objects.filter(is_active=True).count()
    staff_on_duty = User.objects.filter(is_active=True, is_on_duty=True).count()

    notes_week = CareNote.objects.filter(created_at__gte=last_7d).count()
    vitals_today = VitalSigns.objects.filter(recorded_at__date=today).count()
    nursing_patients = Patient.objects.filter(is_active=True, care_level='nursing').count()
    dementia_patients = Patient.objects.filter(is_active=True, care_level='dementia').count()

    # Care levels and staff roles
    care_levels = {label: Patient.objects.filter(is_active=True, care_level=code).count()
                   for code, label in Patient.CARE_LEVEL_CHOICES}
    staff_roles = {label: User.objects.filter(is_active=True, role=code).count()
                   for code, label in User.ROLE_CHOICES}

    # Recent activities
    recent_notes = CareNote.objects.filter(created_at__gte=last_24h).select_related('patient', 'author').order_by('-created_at')[:8]
    recent_meds = Medication.objects.filter(administered_at__gte=last_24h).select_related('patient', 'administered_by').order_by('-administered_at')[:8]
    recent_vitals = VitalSigns.objects.filter(recorded_at__gte=last_24h).select_related('patient', 'recorded_by').order_by('-recorded_at')[:8]

    activity = []
    for n in recent_notes:
        activity.append({
            'type': 'note',
            'obj': n,
            'time': n.created_at,
            'icon': 'bi-journal-text',
            'color': 'success',
            'desc': f'Care note ({n.get_category_display()}) for {n.patient}',
            'user': n.author
        })
    for m in recent_meds:
        activity.append({
            'type': 'med',
            'obj': m,
            'time': m.administered_at,
            'icon': 'bi-capsule',
            'color': 'primary',
            'desc': f'{m.drug_name} {m.dosage} given to {m.patient}',
            'user': m.administered_by
        })
    for v in recent_vitals:
        activity.append({
            'type': 'vitals',
            'obj': v,
            'time': v.recorded_at,
            'icon': 'bi-heart-pulse',
            'color': 'danger',
            'desc': f'Vitals recorded for {v.patient}',
            'user': v.recorded_by
        })
    activity.sort(key=lambda x: x['time'], reverse=True)
    activity = activity[:15]

    # Patient data
    recent_patients = Patient.objects.filter(is_active=True).order_by('-created_at')[:6]
    flagged_patients = Patient.objects.filter(is_active=True).exclude(allergies='')[:5]

    high_risk_patients, medium_risk_patients = [], []
    for p in Patient.objects.filter(is_active=True):
        latest = VitalSigns.objects.filter(patient=p).order_by('-recorded_at').first()
        if latest:
            p.latest_news2 = latest.news2_total
            p.latest_vitals_time = latest.recorded_at
            if latest.news2_level == 'high':
                high_risk_patients.append(p)
            elif latest.news2_level == 'medium':
                medium_risk_patients.append(p)
    high_risk_patients.sort(key=lambda p: p.latest_news2, reverse=True)
    medium_risk_patients.sort(key=lambda p: p.latest_news2, reverse=True)

    fall_risk_patients = []
    for p in Patient.objects.filter(is_active=True):
        risk = p.get_fall_risk()
        if risk['level'] in ('high', 'medium'):
            p.fall_risk = risk
            fall_risk_patients.append(p)
    fall_risk_patients.sort(key=lambda p: p.fall_risk['score'], reverse=True)

    # Feature 1: Get chart data
    chart_data = get_chart_data()

    # Feature 2: Get shift information
    shift_info = get_shift_info()

    # Feature 3: Get KPI metrics
    kpi_metrics = calculate_kpi_metrics()

    # Feature 5: Weather data
    weather_data = get_weather_data()

    context = {
        'total_patients': total_patients,
        'notes_today': notes_today,
        'meds_today': meds_today,
        'active_staff': active_staff,
        'staff_on_duty': staff_on_duty,
        'notes_week': notes_week,
        'vitals_today': vitals_today,
        'nursing_patients': nursing_patients,
        'dementia_patients': dementia_patients,
        'care_levels': care_levels,
        'care_levels_labels': list(care_levels.keys()),
        'care_levels_values': list(care_levels.values()),
        'staff_roles': staff_roles,
        'staff_role_labels': list(staff_roles.keys()),
        'staff_role_values': list(staff_roles.values()),
        'activity': activity,
        'recent_patients': recent_patients,
        'flagged_patients': flagged_patients,
        'high_risk_patients': high_risk_patients,
        'medium_risk_patients': medium_risk_patients,
        'fall_risk_patients': fall_risk_patients,
        'weather': weather_data,
        # New features data
        'chart_data': json.dumps(chart_data),
        'shift_info': shift_info,
        'kpi_metrics': kpi_metrics,
        'user_pref': user_pref,
        'dark_mode': user_pref.dark_mode,
    }
    return render(request, 'dashboard/dashboard.html', context)


@role_required('admin')
def admin_dashboard(request):
    return render(request, 'dashboard/role_dashboard.html', _role_dashboard_context('admin'))


@role_required('doctor')
def doctor_dashboard(request):
    return render(request, 'dashboard/role_dashboard.html', _role_dashboard_context('doctor'))


@role_required('nurse')
def nurse_dashboard(request):
    return render(request, 'dashboard/role_dashboard.html', _role_dashboard_context('nurse'))


@role_required('care_assistant')
def care_assistant_dashboard(request):
    return render(request, 'dashboard/role_dashboard.html', _role_dashboard_context('care_assistant'))


@login_required
def shift_handover(request):
    shift = request.GET.get('shift', 'day')
    now = timezone.now()

    if shift == 'day':
        shift_start = now.replace(hour=7, minute=0, second=0, microsecond=0)
        shift_end = now.replace(hour=19, minute=0, second=0, microsecond=0)
        shift_label = 'Day Shift (07:00 – 19:00)'
        next_shift = 'Night Shift'
    elif shift == 'night':
        if now.hour < 7:
            shift_start = (now - timedelta(days=1)).replace(hour=19, minute=0, second=0, microsecond=0)
        else:
            shift_start = now.replace(hour=19, minute=0, second=0, microsecond=0)
        shift_end = shift_start + timedelta(hours=12)
        shift_label = 'Night Shift (19:00 – 07:00)'
        next_shift = 'Day Shift'
    else:
        shift_start = now - timedelta(hours=12)
        shift_end = now
        shift_label = 'Last 12 Hours'
        next_shift = 'Incoming Shift'

    patients = Patient.objects.filter(is_active=True).order_by('room_number', 'last_name')

    handover_data = []
    for patient in patients:
        notes = CareNote.objects.filter(patient=patient, created_at__range=(shift_start, shift_end)).select_related('author').order_by('-created_at')
        meds = Medication.objects.filter(patient=patient, administered_at__range=(shift_start, shift_end)).select_related('administered_by').order_by('-administered_at')
        vitals = VitalSigns.objects.filter(patient=patient, recorded_at__range=(shift_start, shift_end)).select_related('recorded_by').order_by('-recorded_at')
        latest_v = VitalSigns.objects.filter(patient=patient).order_by('-recorded_at').first()

        flags = []
        if patient.has_allergies:
            flags.append({'type': 'danger', 'text': f'ALLERGY: {patient.allergies}'})
        if latest_v:
            if latest_v.news2_level == 'high':
                flags.append({'type': 'danger', 'text': f'NEWS2 HIGH RISK — Score {latest_v.news2_total}'})
            elif latest_v.news2_level == 'medium':
                flags.append({'type': 'warning', 'text': f'NEWS2 Medium Risk — Score {latest_v.news2_total}'})
        urgent_notes = notes.filter(priority='urgent')
        if urgent_notes.exists():
            flags.append({'type': 'danger', 'text': f'{urgent_notes.count()} URGENT care note(s) this shift'})

        handover_data.append({
            'patient': patient,
            'notes': notes,
            'meds': meds,
            'vitals': vitals,
            'latest_v': latest_v,
            'flags': flags,
            'has_activity': notes.exists() or meds.exists() or vitals.exists(),
        })

    context = {
        'handover_data': handover_data,
        'shift_label': shift_label,
        'next_shift': next_shift,
        'shift': shift,
        'generated_at': now,
        'generated_by': request.user,
        'total_patients': patients.count(),
        'flagged_count': sum(1 for d in handover_data if d['flags']),
    }
    return render(request, 'dashboard/shift_handover.html', context)
