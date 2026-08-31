from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Patient
from .forms import PatientForm
from care_notes.models import CareNote
from medications.models import Medication
from vitals.models import VitalSigns


@login_required
def patient_list(request):
    query = request.GET.get('q', '')
    care_level = request.GET.get('care_level', '')
    status = request.GET.get('status', 'active')

    patients = Patient.objects.all()
    if status == 'active':
        patients = patients.filter(is_active=True)
    elif status == 'archived':
        patients = patients.filter(is_active=False)

    if query:
        patients = patients.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(nhs_number__icontains=query) |
            Q(room_number__icontains=query)
        )
    if care_level:
        patients = patients.filter(care_level=care_level)

    paginator = Paginator(patients, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'patients/patient_list.html', {
        'page_obj': page_obj,
        'query': query,
        'care_level': care_level,
        'status': status,
        'care_level_choices': Patient.CARE_LEVEL_CHOICES,
        'total_count': patients.count(),
    })


@login_required
def patient_detail(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    recent_notes = CareNote.objects.filter(patient=patient).select_related('author')[:5]
    recent_meds = Medication.objects.filter(patient=patient).select_related('administered_by')[:5]
    recent_vitals = VitalSigns.objects.filter(patient=patient).select_related('recorded_by')[:5]
    latest_vitals = VitalSigns.objects.filter(patient=patient).order_by('-recorded_at').first()
    from vitals.models import RiskAssessment
    latest_assessment = RiskAssessment.objects.filter(patient=patient).order_by('-created_at').first()

    # Risk trend chart data: the actual research metric (NEWS2 + trend + multi-parameter
    # combined_risk) over successive readings, not just the raw vitals other charts show.
    import json
    risk_history_qs = RiskAssessment.objects.filter(patient=patient).order_by('assessed_at')[:30]
    risk_trend_data = json.dumps({
        'labels': [ra.assessed_at.strftime('%d %b %H:%M') for ra in risk_history_qs],
        'news2': [ra.news2_total for ra in risk_history_qs],
        'combined': [ra.combined_risk for ra in risk_history_qs],
    })

    # Build timeline (combined, sorted)
    timeline = []
    for note in CareNote.objects.filter(patient=patient).select_related('author')[:15]:
        timeline.append({'type': 'note', 'obj': note, 'time': note.created_at, 'icon': 'bi-journal-text', 'color': 'success'})
    for med in Medication.objects.filter(patient=patient).select_related('administered_by')[:15]:
        timeline.append({'type': 'medication', 'obj': med, 'time': med.administered_at, 'icon': 'bi-capsule', 'color': 'primary'})
    for v in VitalSigns.objects.filter(patient=patient).select_related('recorded_by')[:15]:
        timeline.append({'type': 'vitals', 'obj': v, 'time': v.recorded_at, 'icon': 'bi-heart-pulse', 'color': 'danger'})
    timeline.sort(key=lambda x: x['time'], reverse=True)
    timeline = timeline[:20]

    return render(request, 'patients/patient_detail.html', {
        'patient': patient,
        'recent_notes': recent_notes,
        'recent_meds': recent_meds,
        'recent_vitals': recent_vitals,
        'latest_vitals': latest_vitals,
        'latest_assessment': latest_assessment,
        'risk_trend_data': risk_trend_data,
        'risk_history_count': risk_history_qs.count(),
        'timeline': timeline,
    })


@login_required
def patient_add(request):
    if request.user.role not in ('admin', 'nurse'):
        messages.error(request, 'You do not have permission to add patients.')
        return redirect('patient_list')
    form = PatientForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        patient = form.save(commit=False)
        patient.created_by = request.user
        patient.save()
        messages.success(request, f'Patient {patient.get_full_name()} has been registered.')
        return redirect('patient_detail', pk=patient.pk)
    return render(request, 'patients/patient_form.html', {'form': form, 'action': 'Register New'})


@login_required
def patient_edit(request, pk):
    if request.user.role not in ('admin', 'nurse'):
        messages.error(request, 'You do not have permission to edit patients.')
        return redirect('patient_list')
    patient = get_object_or_404(Patient, pk=pk)
    form = PatientForm(request.POST or None, request.FILES or None, instance=patient)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Patient record updated for {patient.get_full_name()}.')
        return redirect('patient_detail', pk=patient.pk)
    return render(request, 'patients/patient_form.html', {'form': form, 'action': 'Edit', 'patient': patient})


@login_required
def patient_archive(request, pk):
    if not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('patient_list')
    patient = get_object_or_404(Patient, pk=pk)
    patient.is_active = False
    patient.save()
    messages.warning(request, f'{patient.get_full_name()} has been archived.')
    return redirect('patient_list')
