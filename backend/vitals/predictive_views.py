"""
Phase 10: Predictive Forecasting Dashboard Views

Displays predictive forecasts, risk trajectories, and recommendations
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

from patients.models import Patient
from vitals.models import VitalSigns, PredictiveRiskAssessment
from vitals.utils.forecasting_engine import ForecastingEngine
from vitals.utils.trajectory_analyzer import TrajectoryAnalyzer


@login_required
def predictive_dashboard(request):
    """
    Main predictive forecasting dashboard.

    Shows:
    - All patients with recent predictions
    - Risk levels and urgency
    - Time-to-critical for at-risk patients
    - Recommendations
    """
    # Get latest predictions for all patients (last 24 hours)
    latest_predictions = PredictiveRiskAssessment.objects.filter(
        created_at__gte=timezone.now() - timedelta(hours=24)
    ).select_related('patient').order_by('-prediction_timestamp')

    # Group by patient, keeping only latest
    predictions_by_patient = {}
    for pred in latest_predictions:
        if pred.patient_id not in predictions_by_patient:
            predictions_by_patient[pred.patient_id] = pred

    # Sort by urgency
    urgency_order = {'immediate': 0, 'urgent': 1, 'elevated': 2, 'monitor': 3, 'routine': 4}
    patients_data = sorted(
        predictions_by_patient.values(),
        key=lambda p: urgency_order.get(p.urgency_level, 5)
    )

    # Separate at-risk from stable
    at_risk = [p for p in patients_data if p.is_critical_risk or p.trajectory_level in ['critical_within_24h', 'rapid_deterioration']]
    stable = [p for p in patients_data if p not in at_risk]

    context = {
        'at_risk_predictions': at_risk,
        'stable_predictions': stable,
        'total_patients': len(patients_data),
        'at_risk_count': len(at_risk),
        'immediate_count': len([p for p in at_risk if p.urgency_level == 'immediate']),
    }

    return render(request, 'vitals/predictive_dashboard.html', context)


@login_required
def patient_predictive_detail(request, patient_pk):
    """
    Detailed predictive forecast for a single patient.

    Shows:
    - Current vitals
    - Forecasted vitals (24/48/72h)
    - Risk trajectory
    - Recommendations
    - Historical comparison
    """
    patient = get_object_or_404(Patient, pk=patient_pk)

    # Get latest prediction
    latest_prediction = PredictiveRiskAssessment.objects.filter(
        patient=patient
    ).order_by('-prediction_timestamp').first()

    # Get prediction history (last 7 days)
    prediction_history = PredictiveRiskAssessment.objects.filter(
        patient=patient,
        created_at__gte=timezone.now() - timedelta(days=7)
    ).order_by('-prediction_timestamp')[:10]

    # Get latest vitals
    latest_vital = VitalSigns.objects.filter(
        patient=patient
    ).order_by('-recorded_at').first()

    # If no prediction exists, generate one
    if not latest_prediction and latest_vital:
        vitals = VitalSigns.objects.filter(
            patient=patient
        ).order_by('-recorded_at')[:10]

        if vitals.count() >= 3:
            # Build historical data
            historical_data = {
                'heart_rate': [],
                'respiratory_rate': [],
                'oxygen_saturation': [],
                'bp_systolic': [],
                'temperature': [],
            }

            now = timezone.now()
            for vital in reversed(vitals):
                hours_ago = (now - vital.recorded_at).total_seconds() / 3600

                if vital.heart_rate:
                    historical_data['heart_rate'].append({
                        'value': float(vital.heart_rate),
                        'time_hours_ago': -hours_ago
                    })
                if vital.respiratory_rate:
                    historical_data['respiratory_rate'].append({
                        'value': float(vital.respiratory_rate),
                        'time_hours_ago': -hours_ago
                    })
                if vital.oxygen_saturation:
                    historical_data['oxygen_saturation'].append({
                        'value': float(vital.oxygen_saturation),
                        'time_hours_ago': -hours_ago
                    })
                if vital.bp_systolic:
                    historical_data['bp_systolic'].append({
                        'value': float(vital.bp_systolic),
                        'time_hours_ago': -hours_ago
                    })
                if vital.temperature:
                    historical_data['temperature'].append({
                        'value': float(vital.temperature),
                        'time_hours_ago': -hours_ago
                    })

            # Generate forecasts
            engine = ForecastingEngine()
            forecasts = engine.forecast_all_vitals(historical_data, horizon_hours=24)

            # Analyze trajectory
            analyzer = TrajectoryAnalyzer()
            current_vitals = {
                'heart_rate': float(latest_vital.heart_rate) if latest_vital.heart_rate else None,
                'respiratory_rate': float(latest_vital.respiratory_rate) if latest_vital.respiratory_rate else None,
                'oxygen_saturation': float(latest_vital.oxygen_saturation) if latest_vital.oxygen_saturation else None,
                'bp_systolic': float(latest_vital.bp_systolic) if latest_vital.bp_systolic else None,
                'temperature': float(latest_vital.temperature) if latest_vital.temperature else None,
            }
            trajectory = analyzer.analyze_patient_trajectory(current_vitals, forecasts)

            # Determine trajectory level
            hours_to_critical = trajectory.get('intervention_window_hours')
            if hours_to_critical:
                if hours_to_critical < 6:
                    trajectory_level = 'critical_within_24h'
                elif hours_to_critical < 24:
                    trajectory_level = 'rapid_deterioration'
                elif hours_to_critical < 48:
                    trajectory_level = 'moderate_deterioration'
                else:
                    trajectory_level = 'slow_deterioration'
            else:
                trajectory_level = 'stable'

            # Create prediction record
            latest_prediction = PredictiveRiskAssessment.objects.create(
                patient=patient,
                based_on_vital=latest_vital,
                prediction_timestamp=timezone.now(),
                current_heart_rate=current_vitals['heart_rate'],
                current_respiratory_rate=current_vitals['respiratory_rate'],
                current_oxygen_saturation=current_vitals['oxygen_saturation'],
                current_bp_systolic=current_vitals['bp_systolic'],
                current_temperature=current_vitals['temperature'],
                forecast_24h_heart_rate=forecasts.get('heart_rate', {}).get('forecast'),
                forecast_24h_respiratory_rate=forecasts.get('respiratory_rate', {}).get('forecast'),
                forecast_24h_oxygen_saturation=forecasts.get('oxygen_saturation', {}).get('forecast'),
                forecast_24h_bp_systolic=forecasts.get('bp_systolic', {}).get('forecast'),
                forecast_24h_temperature=forecasts.get('temperature', {}).get('forecast'),
                hours_to_critical=hours_to_critical,
                vitals_at_risk=trajectory.get('vitals_at_risk', []),
                critical_vital_first=trajectory.get('earliest_critical', {}).get('vital'),
                critical_vital_first_hours=trajectory.get('earliest_critical', {}).get('hours'),
                trajectory_level=trajectory_level,
                forecast_confidence=min([
                    forecasts.get(v, {}).get('confidence', 0.7)
                    for v in ['heart_rate', 'oxygen_saturation']
                ] or [0.7]),
                historical_readings_used=len(vitals),
                recommended_actions=trajectory.get('recommendations', []),
                intervention_window_hours=hours_to_critical,
            )

    context = {
        'patient': patient,
        'latest_vital': latest_vital,
        'latest_prediction': latest_prediction,
        'prediction_history': prediction_history,
    }

    return render(request, 'vitals/patient_predictive_detail.html', context)


@login_required
def api_patient_predictive(request, patient_pk):
    """
    API endpoint returning latest prediction as JSON.
    """
    patient = get_object_or_404(Patient, pk=patient_pk)

    prediction = PredictiveRiskAssessment.objects.filter(
        patient=patient
    ).order_by('-prediction_timestamp').first()

    if not prediction:
        return JsonResponse({'error': 'No predictions available'}, status=404)

    return JsonResponse({
        'success': True,
        'prediction': {
            'patient_id': patient.id,
            'patient_name': patient.get_full_name(),
            'trajectory_level': prediction.trajectory_level,
            'urgency': prediction.urgency_level,
            'hours_to_critical': prediction.hours_to_critical,
            'vitals_at_risk': prediction.vitals_at_risk,
            'current_vitals': {
                'heart_rate': prediction.current_heart_rate,
                'respiratory_rate': prediction.current_respiratory_rate,
                'oxygen_saturation': prediction.current_oxygen_saturation,
                'bp_systolic': prediction.current_bp_systolic,
                'temperature': prediction.current_temperature,
            },
            'forecast_24h': {
                'heart_rate': prediction.forecast_24h_heart_rate,
                'respiratory_rate': prediction.forecast_24h_respiratory_rate,
                'oxygen_saturation': prediction.forecast_24h_oxygen_saturation,
                'bp_systolic': prediction.forecast_24h_bp_systolic,
                'temperature': prediction.forecast_24h_temperature,
            },
            'recommendations': prediction.recommended_actions,
            'confidence': float(prediction.forecast_confidence),
            'created_at': prediction.prediction_timestamp.isoformat(),
        }
    })
