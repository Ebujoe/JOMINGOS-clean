"""
Phase 10: Predictive Forecasting API

REST endpoints for:
- Getting patient risk trajectories
- Forecast vital signs
- Predictive alerts
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.db.models import Q
from datetime import timedelta
from django.utils import timezone

from patients.models import Patient
from vitals.models import VitalSigns, PredictiveRiskAssessment
from vitals.utils.forecasting_engine import ForecastingEngine
from vitals.utils.trajectory_analyzer import TrajectoryAnalyzer


@login_required
@require_http_methods(["GET"])
def get_patient_prediction(request, patient_pk):
    """
    Get predictive forecast for a patient.

    Returns:
    - Current vitals
    - 24/48/72h forecasts
    - Risk trajectory
    - Time to deterioration
    - Recommendations
    """
    patient = get_object_or_404(Patient, pk=patient_pk)

    # Get last 10 vitals for historical context
    vitals_qs = VitalSigns.objects.filter(
        patient=patient
    ).order_by('-recorded_at')[:10]

    if vitals_qs.count() < 3:
        return JsonResponse({
            'error': 'Insufficient vital history',
            'readings_available': vitals_qs.count(),
            'minimum_required': 3
        }, status=400)

    vitals_list = list(reversed(vitals_qs))
    latest_vital = vitals_list[-1]

    try:
        # Build historical data structure
        historical_data = {
            'heart_rate': [],
            'respiratory_rate': [],
            'oxygen_saturation': [],
            'bp_systolic': [],
            'temperature': [],
        }

        now = timezone.now()
        for vital in vitals_list:
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
        forecasts_24h = engine.forecast_all_vitals(historical_data, horizon_hours=24)
        forecasts_48h = engine.forecast_all_vitals(historical_data, horizon_hours=48)
        forecasts_72h = engine.forecast_all_vitals(historical_data, horizon_hours=72)

        # Build current vitals dict
        current_vitals = {
            'heart_rate': float(latest_vital.heart_rate) if latest_vital.heart_rate else None,
            'respiratory_rate': float(latest_vital.respiratory_rate) if latest_vital.respiratory_rate else None,
            'oxygen_saturation': float(latest_vital.oxygen_saturation) if latest_vital.oxygen_saturation else None,
            'bp_systolic': float(latest_vital.bp_systolic) if latest_vital.bp_systolic else None,
            'temperature': float(latest_vital.temperature) if latest_vital.temperature else None,
        }

        # Analyze trajectory
        analyzer = TrajectoryAnalyzer()
        trajectory = analyzer.analyze_patient_trajectory(current_vitals, forecasts_24h)

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

        # Create predictive assessment record
        prediction_record = PredictiveRiskAssessment.objects.create(
            patient=patient,
            based_on_vital=latest_vital,
            prediction_timestamp=timezone.now(),
            # Current values
            current_heart_rate=current_vitals['heart_rate'],
            current_respiratory_rate=current_vitals['respiratory_rate'],
            current_oxygen_saturation=current_vitals['oxygen_saturation'],
            current_bp_systolic=current_vitals['bp_systolic'],
            current_temperature=current_vitals['temperature'],
            # 24h forecast
            forecast_24h_heart_rate=forecasts_24h.get('heart_rate', {}).get('forecast'),
            forecast_24h_respiratory_rate=forecasts_24h.get('respiratory_rate', {}).get('forecast'),
            forecast_24h_oxygen_saturation=forecasts_24h.get('oxygen_saturation', {}).get('forecast'),
            forecast_24h_bp_systolic=forecasts_24h.get('bp_systolic', {}).get('forecast'),
            forecast_24h_temperature=forecasts_24h.get('temperature', {}).get('forecast'),
            # 48h forecast
            forecast_48h_heart_rate=forecasts_48h.get('heart_rate', {}).get('forecast'),
            forecast_48h_respiratory_rate=forecasts_48h.get('respiratory_rate', {}).get('forecast'),
            forecast_48h_oxygen_saturation=forecasts_48h.get('oxygen_saturation', {}).get('forecast'),
            forecast_48h_bp_systolic=forecasts_48h.get('bp_systolic', {}).get('forecast'),
            forecast_48h_temperature=forecasts_48h.get('temperature', {}).get('forecast'),
            # 72h forecast
            forecast_72h_heart_rate=forecasts_72h.get('heart_rate', {}).get('forecast'),
            forecast_72h_respiratory_rate=forecasts_72h.get('respiratory_rate', {}).get('forecast'),
            forecast_72h_oxygen_saturation=forecasts_72h.get('oxygen_saturation', {}).get('forecast'),
            forecast_72h_bp_systolic=forecasts_72h.get('bp_systolic', {}).get('forecast'),
            forecast_72h_temperature=forecasts_72h.get('temperature', {}).get('forecast'),
            # Trajectory
            hours_to_critical=hours_to_critical,
            vitals_at_risk=trajectory.get('vitals_at_risk', []),
            critical_vital_first=trajectory.get('earliest_critical', {}).get('vital'),
            critical_vital_first_hours=trajectory.get('earliest_critical', {}).get('hours'),
            trajectory_level=trajectory_level,
            forecast_confidence=min([
                forecasts_24h.get(v, {}).get('confidence', 0.7)
                for v in ['heart_rate', 'oxygen_saturation']
            ] or [0.7]),
            historical_readings_used=len(vitals_list),
            recommended_actions=trajectory.get('recommendations', []),
            intervention_window_hours=hours_to_critical,
        )

        return JsonResponse({
            'success': True,
            'patient': {
                'id': patient.id,
                'name': patient.get_full_name(),
                'age': patient.age,
            },
            'current_vitals': current_vitals,
            'forecasts': {
                '24h': {vital: forecasts_24h.get(vital, {}).get('forecast')
                       for vital in current_vitals.keys()},
                '48h': {vital: forecasts_48h.get(vital, {}).get('forecast')
                       for vital in current_vitals.keys()},
                '72h': {vital: forecasts_72h.get(vital, {}).get('forecast')
                       for vital in current_vitals.keys()},
            },
            'trajectory': {
                'level': trajectory_level,
                'hours_to_critical': hours_to_critical,
                'critical_vital': trajectory.get('earliest_critical', {}).get('vital'),
                'vitals_at_risk': trajectory.get('vitals_at_risk', []),
                'urgency': trajectory.get('risk_summary', {}).get('urgency'),
            },
            'recommendations': trajectory.get('recommendations', []),
            'prediction_id': prediction_record.id,
            'confidence': float(prediction_record.forecast_confidence),
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'error': str(e),
            'type': type(e).__name__
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_cohort_predictions(request):
    """
    Get predictions for all monitored patients.

    Returns:
    - All patients with trajectory level
    - At-risk patients (sorted by urgency)
    """
    try:
        # Get latest prediction for each patient
        latest_predictions = PredictiveRiskAssessment.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=24)
        ).values('patient').distinct()

        predictions = []
        for pred_set in latest_predictions:
            patient_id = pred_set['patient']
            latest_pred = PredictiveRiskAssessment.objects.filter(
                patient_id=patient_id
            ).latest('prediction_timestamp')

            patient = latest_pred.patient
            predictions.append({
                'patient_id': patient.id,
                'patient_name': patient.get_full_name(),
                'trajectory_level': latest_pred.trajectory_level,
                'urgency': latest_pred.urgency_level,
                'hours_to_critical': latest_pred.hours_to_critical,
                'at_risk': latest_pred.is_critical_risk,
                'critical_vital': latest_pred.critical_vital_first,
            })

        # Sort by urgency (immediate first)
        urgency_order = {'immediate': 0, 'urgent': 1, 'elevated': 2, 'monitor': 3, 'routine': 4}
        predictions.sort(key=lambda x: urgency_order.get(x['urgency'], 5))

        # Separate at-risk from stable
        at_risk = [p for p in predictions if p['at_risk']]
        stable = [p for p in predictions if not p['at_risk']]

        return JsonResponse({
            'success': True,
            'cohort_summary': {
                'total_patients': len(predictions),
                'at_risk_count': len(at_risk),
                'stable_count': len(stable),
            },
            'at_risk_patients': at_risk,
            'stable_patients': stable,
        })

    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_prediction_details(request, prediction_id):
    """
    Get detailed information about a specific prediction.

    Returns:
    - Complete forecast data
    - Trajectory analysis
    - Recommendations
    - Forecast model details
    """
    prediction = get_object_or_404(PredictiveRiskAssessment, pk=prediction_id)

    return JsonResponse({
        'success': True,
        'prediction': {
            'id': prediction.id,
            'patient': {
                'id': prediction.patient.id,
                'name': prediction.patient.get_full_name(),
            },
            'created_at': prediction.created_at.isoformat(),
            'current_vitals': {
                'heart_rate': prediction.current_heart_rate,
                'respiratory_rate': prediction.current_respiratory_rate,
                'oxygen_saturation': prediction.current_oxygen_saturation,
                'bp_systolic': prediction.current_bp_systolic,
                'temperature': prediction.current_temperature,
            },
            'forecasts': {
                '24h': {
                    'heart_rate': prediction.forecast_24h_heart_rate,
                    'respiratory_rate': prediction.forecast_24h_respiratory_rate,
                    'oxygen_saturation': prediction.forecast_24h_oxygen_saturation,
                    'bp_systolic': prediction.forecast_24h_bp_systolic,
                    'temperature': prediction.forecast_24h_temperature,
                    'news2_score': prediction.forecast_24h_news2_score,
                },
                '48h': {
                    'heart_rate': prediction.forecast_48h_heart_rate,
                    'respiratory_rate': prediction.forecast_48h_respiratory_rate,
                    'oxygen_saturation': prediction.forecast_48h_oxygen_saturation,
                    'bp_systolic': prediction.forecast_48h_bp_systolic,
                    'temperature': prediction.forecast_48h_temperature,
                    'news2_score': prediction.forecast_48h_news2_score,
                },
                '72h': {
                    'heart_rate': prediction.forecast_72h_heart_rate,
                    'respiratory_rate': prediction.forecast_72h_respiratory_rate,
                    'oxygen_saturation': prediction.forecast_72h_oxygen_saturation,
                    'bp_systolic': prediction.forecast_72h_bp_systolic,
                    'temperature': prediction.forecast_72h_temperature,
                    'news2_score': prediction.forecast_72h_news2_score,
                },
            },
            'trajectory': {
                'level': prediction.trajectory_level,
                'hours_to_critical': prediction.hours_to_critical,
                'projected_critical_time': prediction.projected_critical_timestamp.isoformat() if prediction.projected_critical_timestamp else None,
                'vitals_at_risk': prediction.vitals_at_risk,
                'critical_vital_first': prediction.critical_vital_first,
                'urgency': prediction.urgency_level,
                'is_critical_risk': prediction.is_critical_risk,
            },
            'forecast_quality': {
                'confidence': prediction.forecast_confidence,
                'historical_readings': prediction.historical_readings_used,
            },
            'recommendations': prediction.recommended_actions,
        }
    })
