from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Prefetch
from patients.models import Patient
from .models import VitalSigns
from .forms import VitalSignsForm


@login_required
def vitals_list(request):
    """Display all recent vitals with NEWS2 scores and related alerts"""
    # Get latest vital for each patient
    latest_vitals = VitalSigns.objects.select_related('patient', 'recorded_by').order_by('-recorded_at')[:50]

    vitals_data = []
    for vital in latest_vitals:
        alerts = vital.deterioration_alerts.all()
        vitals_data.append({
            'vital': vital,
            'alerts': alerts,
        })

    return render(request, 'vitals/vitals_dashboard.html', {'vitals_data': vitals_data})


@login_required
def add_vitals(request, patient_pk):
    patient = get_object_or_404(Patient, pk=patient_pk)
    form = VitalSignsForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        v = form.save(commit=False)
        v.patient = patient
        v.recorded_by = request.user
        v.save()
        messages.success(request, f'Vital signs recorded for {patient.get_full_name()}.')
        return redirect('patient_detail', pk=patient_pk)
    return render(request, 'vitals/vitals_form.html', {'form': form, 'patient': patient})


@login_required
def patient_vitals_list(request, patient_pk):
    patient = get_object_or_404(Patient, pk=patient_pk)
    vitals = VitalSigns.objects.filter(patient=patient).select_related('recorded_by')
    return render(request, 'vitals/vitals_list.html', {'patient': patient, 'vitals': vitals})


@login_required
def patient_vital_history(request, patient_pk):
    """
    COMPREHENSIVE PATIENT VITAL HISTORY VIEW

    Shows:
    - Complete vital history (past 20 recordings)
    - NEWS2 score breakdown for each recording
    - Rate of change calculations (trends)
    - Trend scoring and prediction reasoning
    - Alert history with detailed reasoning
    - Clinical interpretation
    """
    patient = get_object_or_404(Patient, pk=patient_pk)

    # Get last 20 vital recordings (provides trend history)
    vitals = VitalSigns.objects.filter(
        patient=patient
    ).select_related('recorded_by').order_by('-recorded_at')[:20]

    # Reverse to show chronological order (oldest first)
    vitals_list = list(reversed(vitals))

    # Build detailed history with calculations
    history_data = []

    for i, vital in enumerate(vitals_list):
        # Get related alerts
        alerts = vital.deterioration_alerts.all().order_by('-triggered_at')

        # Calculate rate of change if we have a previous reading
        roc_data = {
            'hr_roc': None,
            'rr_roc': None,
            'spo2_roc': None,
            'bp_roc': None,
            'temp_roc': None,
            'trend_score': 0,
            'trend_reasons': []
        }

        if i > 0:
            prev_vital = vitals_list[i - 1]
            # Assume 4-8 hours between readings (typical care home schedule)
            time_diff_hours = 4.0

            # Calculate rates of change per hour
            if vital.heart_rate and prev_vital.heart_rate:
                roc_data['hr_roc'] = (vital.heart_rate - prev_vital.heart_rate) / time_diff_hours
                if roc_data['hr_roc'] > 10:
                    roc_data['trend_score'] += 2
                    roc_data['trend_reasons'].append(f"HR rising {roc_data['hr_roc']:.2f} bpm/hour")

            if vital.respiratory_rate and prev_vital.respiratory_rate:
                roc_data['rr_roc'] = (vital.respiratory_rate - prev_vital.respiratory_rate) / time_diff_hours
                if roc_data['rr_roc'] > 5:
                    roc_data['trend_score'] += 2
                    roc_data['trend_reasons'].append(f"RR rising {roc_data['rr_roc']:.2f} br/hour")

            if vital.oxygen_saturation and prev_vital.oxygen_saturation:
                roc_data['spo2_roc'] = (vital.oxygen_saturation - prev_vital.oxygen_saturation) / time_diff_hours
                if roc_data['spo2_roc'] < -2:
                    roc_data['trend_score'] += 3
                    roc_data['trend_reasons'].append(f"🚨 SpO2 DROPPING {roc_data['spo2_roc']:.2f}%/hour (CRITICAL)")

            if vital.bp_systolic and prev_vital.bp_systolic:
                roc_data['bp_roc'] = (vital.bp_systolic - prev_vital.bp_systolic) / time_diff_hours
                if roc_data['bp_roc'] < -10:
                    roc_data['trend_score'] += 2
                    roc_data['trend_reasons'].append(f"BP dropping {roc_data['bp_roc']:.2f} mmHg/hour")

            if vital.temperature and prev_vital.temperature:
                roc_data['temp_roc'] = (vital.temperature - prev_vital.temperature) / time_diff_hours
                if abs(roc_data['temp_roc']) > 0.5:
                    roc_data['trend_score'] += 2
                    roc_data['trend_reasons'].append(f"Temp abnormal trend {roc_data['temp_roc']:.2f}°C/hour")

        # Prediction reasoning
        prediction_reasoning = {
            'news2_score': vital.news2_total,
            'news2_level': vital.news2_level,
            'trend_score': roc_data['trend_score'],
            'combined_risk': vital.news2_total + roc_data['trend_score'],
            'alert_triggered': alerts.exists(),
            'alert_priority': alerts.first().priority if alerts.exists() else 'NONE',
            'alert_reason': alerts.first().trigger_reason if alerts.exists() else 'No alert triggered',
            'reasoning_steps': []
        }

        # Build reasoning steps
        prediction_reasoning['reasoning_steps'].append(
            f"Step 1: Calculate NEWS2 Score = {vital.news2_total}"
        )
        prediction_reasoning['reasoning_steps'].append(
            f"  • HR Score: {vital.news2_hr_score} (HR={vital.heart_rate})"
        )
        prediction_reasoning['reasoning_steps'].append(
            f"  • RR Score: {vital.news2_respiratory_score} (RR={vital.respiratory_rate})"
        )
        prediction_reasoning['reasoning_steps'].append(
            f"  • SpO2 Score: {vital.news2_spo2_score} (SpO2={vital.oxygen_saturation}%)"
        )
        prediction_reasoning['reasoning_steps'].append(
            f"  • BP Score: {vital.news2_bp_score} (SBP={vital.bp_systolic})"
        )
        prediction_reasoning['reasoning_steps'].append(
            f"  • Temp Score: {vital.news2_temp_score} (Temp={vital.temperature}°C)"
        )

        prediction_reasoning['reasoning_steps'].append(f"\nStep 2: Analyze Trends (Rate of Change)")
        if roc_data['trend_reasons']:
            prediction_reasoning['reasoning_steps'].extend(roc_data['trend_reasons'])
        else:
            prediction_reasoning['reasoning_steps'].append("  • No significant trends detected")

        prediction_reasoning['reasoning_steps'].append(f"\nStep 3: Calculate Trend Score = {roc_data['trend_score']}")

        prediction_reasoning['reasoning_steps'].append(f"\nStep 4: Combined Risk = NEWS2 + Trends = {vital.news2_total} + {roc_data['trend_score']} = {prediction_reasoning['combined_risk']}")

        prediction_reasoning['reasoning_steps'].append(f"\nStep 5: Alert Decision Engine")
        if vital.news2_total >= 7:
            prediction_reasoning['reasoning_steps'].append(f"  ✓ NEWS2 >= 7 (CRITICAL) → ALERT TRIGGERED")
        elif vital.news2_total >= 5 and roc_data['trend_score'] > 0:
            prediction_reasoning['reasoning_steps'].append(f"  ✓ NEWS2 >= 5 AND Trends Present → ALERT TRIGGERED")
        elif roc_data['trend_score'] >= 5:
            prediction_reasoning['reasoning_steps'].append(f"  ✓ Trend Score >= 5 (Significant Deterioration) → ALERT TRIGGERED")
        else:
            prediction_reasoning['reasoning_steps'].append(f"  ✗ No alert criteria met → Routine monitoring")

        prediction_reasoning['reasoning_steps'].append(f"\nStep 6: Clinical Interpretation")
        if vital.news2_total >= 7:
            prediction_reasoning['reasoning_steps'].append("  🚨 CRITICAL: Immediate medical review required")
        elif vital.news2_total >= 5:
            prediction_reasoning['reasoning_steps'].append("  ⚠️ HIGH RISK: Escalate to senior staff, increased monitoring")
        else:
            prediction_reasoning['reasoning_steps'].append("  ✅ STABLE: Continue routine monitoring")

        history_data.append({
            'vital': vital,
            'sequence': i + 1,
            'alerts': alerts,
            'roc_data': roc_data,
            'prediction_reasoning': prediction_reasoning
        })

    context = {
        'patient': patient,
        'history_data': history_data,
        'total_recordings': VitalSigns.objects.filter(patient=patient).count(),
        'alert_count': patient.deterioration_alerts.count(),
    }

    return render(request, 'vitals/patient_vital_history.html', context)
