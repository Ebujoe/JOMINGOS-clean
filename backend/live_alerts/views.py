from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone

from patients.models import Patient
from .models import FallAlert


@login_required
def live_alert_form(request, patient_pk):
    """
    Renders the Live Alerts page: the room camera panel + the alert log below it.
    """
    patient = get_object_or_404(Patient, pk=patient_pk)
    alerts = FallAlert.objects.filter(patient=patient).select_related('acknowledged_by')
    return render(request, 'live_alerts/live_alert_form.html', {'patient': patient, 'alerts': alerts})


@login_required
@require_POST
def live_alert_log(request, patient_pk):
    """
    Receives a snapshot + label from the browser the moment the pose model
    (running client-side via TensorFlow.js) detects a fall, and logs it.

    Unlike voice_transcribe_medication, there's no server-side AI call here —
    the detection decision was already made in the browser. This view just persists it.
    """
    patient = get_object_or_404(Patient, pk=patient_pk)
    snapshot = request.FILES.get('snapshot')
    label_raw = request.POST.get('label', '')

    if not snapshot:
        return JsonResponse({'error': 'No snapshot received'}, status=400)

    if 'fall' in label_raw.lower():
        label = 'fallen'
    else:
        return JsonResponse({'error': f'Unrecognized label: {label_raw}'}, status=400)

    if snapshot.size > 5 * 1024 * 1024:  # 5MB limit
        return JsonResponse({'error': 'Snapshot too large. Max 5MB.'}, status=400)

    confidence = request.POST.get('confidence')

    alert = FallAlert.objects.create(
        patient=patient,
        snapshot=snapshot,
        label=label,
        confidence=confidence or None,
        detected_at=timezone.now(),
    )

    return JsonResponse({
        'alert': {
            'id': alert.id,
            'label': alert.get_label_display(),
            'snapshot_url': alert.snapshot.url,
            'detected_at': alert.detected_at.strftime('%d %b %Y, %H:%M'),
        }
    })

@login_required
@require_POST
def acknowledge_alert(request, patient_pk, alert_pk):
    """
    Staff marks an alert as reviewed, so it stops showing as 'new' in the log.
    """
    patient = get_object_or_404(Patient, pk=patient_pk)
    alert = get_object_or_404(FallAlert, pk=alert_pk, patient=patient)

    alert.status = 'acknowledged'
    alert.acknowledged_by = request.user
    alert.acknowledged_at = timezone.now()
    alert.save()

    messages.success(request, 'Alert acknowledged.')
    return redirect('live_alert_form', patient_pk=patient_pk)

@login_required
@require_POST
def delete_alert(request, patient_pk, alert_pk):
    """
    Staff deletes a fall alert they judge to be a false positive / not useful.
    """
    patient = get_object_or_404(Patient, pk=patient_pk)
    alert = get_object_or_404(FallAlert, pk=alert_pk, patient=patient)
    alert.snapshot.delete(save=False)  # remove the image file from storage too
    alert.delete()
    return JsonResponse({'deleted': True, 'alert_id': alert_pk})