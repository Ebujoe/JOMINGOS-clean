"""
Phase 10: Predictive Forecasting Dashboard Views

Displays predictive forecasts, risk trajectories, and recommendations
"""

import json
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

    return render(request, 'vitals/predictive_simple.html', context)


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

            # Generate forecasts for ALL horizons (24h, 7d, 30d, 365d)
            engine = ForecastingEngine()
            forecasts_24h = engine.forecast_all_vitals(historical_data, horizon_hours=24)
            forecasts_7d = engine.forecast_all_vitals(historical_data, horizon_hours=168)   # 7 days
            forecasts_30d = engine.forecast_all_vitals(historical_data, horizon_hours=720)  # 30 days
            forecasts_365d = engine.forecast_all_vitals(historical_data, horizon_hours=8760) # 365 days

            # Analyze trajectory
            analyzer = TrajectoryAnalyzer()
            current_vitals = {
                'heart_rate': float(latest_vital.heart_rate) if latest_vital.heart_rate else None,
                'respiratory_rate': float(latest_vital.respiratory_rate) if latest_vital.respiratory_rate else None,
                'oxygen_saturation': float(latest_vital.oxygen_saturation) if latest_vital.oxygen_saturation else None,
                'bp_systolic': float(latest_vital.bp_systolic) if latest_vital.bp_systolic else None,
                'temperature': float(latest_vital.temperature) if latest_vital.temperature else None,
            }
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

            # Create prediction record with ALL forecast horizons
            earliest_critical = trajectory.get('earliest_critical') or {}
            latest_prediction = PredictiveRiskAssessment.objects.create(
                patient=patient,
                based_on_vital=latest_vital,
                prediction_timestamp=timezone.now(),
                current_heart_rate=current_vitals['heart_rate'],
                current_respiratory_rate=current_vitals['respiratory_rate'],
                current_oxygen_saturation=current_vitals['oxygen_saturation'],
                current_bp_systolic=current_vitals['bp_systolic'],
                current_temperature=current_vitals['temperature'],
                # 24-hour forecasts
                forecast_24h_heart_rate=forecasts_24h.get('heart_rate', {}).get('forecast'),
                forecast_24h_respiratory_rate=forecasts_24h.get('respiratory_rate', {}).get('forecast'),
                forecast_24h_oxygen_saturation=forecasts_24h.get('oxygen_saturation', {}).get('forecast'),
                forecast_24h_bp_systolic=forecasts_24h.get('bp_systolic', {}).get('forecast'),
                forecast_24h_temperature=forecasts_24h.get('temperature', {}).get('forecast'),
                # 7-day forecasts
                forecast_7d_heart_rate=forecasts_7d.get('heart_rate', {}).get('forecast'),
                forecast_7d_respiratory_rate=forecasts_7d.get('respiratory_rate', {}).get('forecast'),
                forecast_7d_oxygen_saturation=forecasts_7d.get('oxygen_saturation', {}).get('forecast'),
                forecast_7d_bp_systolic=forecasts_7d.get('bp_systolic', {}).get('forecast'),
                forecast_7d_temperature=forecasts_7d.get('temperature', {}).get('forecast'),
                # 30-day forecasts
                forecast_30d_heart_rate=forecasts_30d.get('heart_rate', {}).get('forecast'),
                forecast_30d_respiratory_rate=forecasts_30d.get('respiratory_rate', {}).get('forecast'),
                forecast_30d_oxygen_saturation=forecasts_30d.get('oxygen_saturation', {}).get('forecast'),
                forecast_30d_bp_systolic=forecasts_30d.get('bp_systolic', {}).get('forecast'),
                forecast_30d_temperature=forecasts_30d.get('temperature', {}).get('forecast'),
                # 365-day forecasts
                forecast_365d_heart_rate=forecasts_365d.get('heart_rate', {}).get('forecast'),
                forecast_365d_respiratory_rate=forecasts_365d.get('respiratory_rate', {}).get('forecast'),
                forecast_365d_oxygen_saturation=forecasts_365d.get('oxygen_saturation', {}).get('forecast'),
                forecast_365d_bp_systolic=forecasts_365d.get('bp_systolic', {}).get('forecast'),
                forecast_365d_temperature=forecasts_365d.get('temperature', {}).get('forecast'),
                hours_to_critical=hours_to_critical,
                vitals_at_risk=trajectory.get('vitals_at_risk', []),
                critical_vital_first=earliest_critical.get('vital'),
                critical_vital_first_hours=earliest_critical.get('hours'),
                trajectory_level=trajectory_level,
                forecast_confidence=min([
                    forecasts_24h.get(v, {}).get('confidence', 0.7)
                    for v in ['heart_rate', 'oxygen_saturation']
                ] or [0.7]),
                historical_readings_used=len(vitals),
                recommended_actions=trajectory.get('recommendations', []),
                intervention_window_hours=hours_to_critical,
            )

    # Get all patients for navigation (those with vital signs)
    all_patients = Patient.objects.filter(
        vitals__isnull=False
    ).distinct().order_by('first_name', 'last_name')

    # Get previous and next patient IDs for navigation
    patient_list = list(all_patients.values_list('id', flat=True))
    current_index = list(patient_list).index(patient.id) if patient.id in patient_list else 0
    prev_patient_id = patient_list[current_index - 1] if current_index > 0 else None
    next_patient_id = patient_list[current_index + 1] if current_index < len(patient_list) - 1 else None

    # Get recent vitals for trend charts and timeline
    recent_vitals = list(VitalSigns.objects.filter(patient=patient).order_by('-recorded_at')[:10])
    recent_vitals_ordered = list(reversed(recent_vitals))

    # Build trend data for charts (last 6-7 vitals) - convert Decimal to float for JSON
    hr_trend = [float(v.heart_rate) for v in recent_vitals_ordered if v.heart_rate]
    rr_trend = [float(v.respiratory_rate) for v in recent_vitals_ordered if v.respiratory_rate]
    spo2_trend = [float(v.oxygen_saturation) for v in recent_vitals_ordered if v.oxygen_saturation]
    temp_trend = [float(v.temperature) for v in recent_vitals_ordered if v.temperature]

    # Determine status based on latest prediction
    if latest_prediction:
        if latest_prediction.trajectory_level in ['critical_within_24h', 'rapid_deterioration']:
            status_level = 'critical'
            status_message = 'CRITICAL: Immediate Intervention Required'
            status_description = f'Critical vitals projected within {latest_prediction.hours_to_critical:.1f} hours. {latest_prediction.critical_vital_first} at risk.'
        elif latest_prediction.trajectory_level == 'moderate_deterioration':
            status_level = 'warning'
            status_message = 'URGENT: High Risk Trajectory'
            status_description = f'Moderate deterioration expected. Monitoring interval: 4-6 hours recommended.'
        else:
            status_level = 'stable'
            status_message = 'STABLE: Continue Routine Monitoring'
            status_description = 'No critical vitals projected. Continue standard monitoring schedule.'
    else:
        status_level = 'stable'
        status_message = 'STABLE: No Critical Alerts'
        status_description = 'Continue routine monitoring.'

    # Data sufficiency alerts
    data_alerts = []
    vitals_count = len(recent_vitals)
    if vitals_count < 3:
        data_alerts.append('Insufficient data for reliable projections. Minimum 3 readings required.')
    if vitals_count < 6:
        data_alerts.append('Limited historical data. Forecasts may have reduced accuracy.')

    # Check recording interval appropriateness
    if vitals_count >= 2:
        time_diff = (recent_vitals[0].recorded_at - recent_vitals[1].recorded_at).total_seconds() / 3600
        if time_diff > 24 and latest_prediction and latest_prediction.trajectory_level in ['critical_within_24h']:
            data_alerts.append('WARNING: Recording interval too long for acute patient. Increase to 4-6 hourly.')
        elif time_diff > 7 * 24 and latest_prediction and latest_prediction.trajectory_level in ['moderate_deterioration', 'slow_deterioration']:
            data_alerts.append('Recording interval appropriate for chronic patient status.')

    # Build forecast data for all horizons
    forecast_data = {}
    if latest_prediction:
        forecast_data['24h'] = {
            'Next 24 Hours': {
                'HR': f"{latest_prediction.forecast_24h_heart_rate:.0f} bpm" if latest_prediction.forecast_24h_heart_rate else 'N/A',
                'RR': f"{latest_prediction.forecast_24h_respiratory_rate:.1f} /min" if latest_prediction.forecast_24h_respiratory_rate else 'N/A',
                'SpO2': f"{latest_prediction.forecast_24h_oxygen_saturation:.1f}%" if latest_prediction.forecast_24h_oxygen_saturation else 'N/A',
                'Temp': f"{latest_prediction.forecast_24h_temperature:.2f}°C" if latest_prediction.forecast_24h_temperature else 'N/A',
                'confidence': f"{latest_prediction.forecast_confidence * 100:.0f}%"
            }
        }
        forecast_data['7d'] = {
            '7 Days': {
                'HR': f"{latest_prediction.forecast_7d_heart_rate:.0f} bpm" if latest_prediction.forecast_7d_heart_rate else 'N/A',
                'RR': f"{latest_prediction.forecast_7d_respiratory_rate:.1f} /min" if latest_prediction.forecast_7d_respiratory_rate else 'N/A',
                'SpO2': f"{latest_prediction.forecast_7d_oxygen_saturation:.1f}%" if latest_prediction.forecast_7d_oxygen_saturation else 'N/A',
                'Temp': f"{latest_prediction.forecast_7d_temperature:.2f}°C" if latest_prediction.forecast_7d_temperature else 'N/A',
                'confidence': f"{max(0, latest_prediction.forecast_confidence - 0.1) * 100:.0f}%"
            }
        }
        forecast_data['14d'] = {
            '14 Days': {
                'HR': f"{(latest_prediction.forecast_7d_heart_rate or 0) * 1.05:.0f} bpm" if latest_prediction.forecast_7d_heart_rate else 'N/A',
                'RR': f"{(latest_prediction.forecast_7d_respiratory_rate or 0) * 1.02:.1f} /min" if latest_prediction.forecast_7d_respiratory_rate else 'N/A',
                'SpO2': f"{(latest_prediction.forecast_7d_oxygen_saturation or 0) * 0.98:.1f}%" if latest_prediction.forecast_7d_oxygen_saturation else 'N/A',
                'Temp': f"{(latest_prediction.forecast_7d_temperature or 0) * 1.01:.2f}°C" if latest_prediction.forecast_7d_temperature else 'N/A',
                'confidence': f"{max(0, latest_prediction.forecast_confidence - 0.15) * 100:.0f}%"
            }
        }
        forecast_data['30d'] = {
            '30 Days': {
                'HR': f"{latest_prediction.forecast_30d_heart_rate:.0f} bpm" if latest_prediction.forecast_30d_heart_rate else 'N/A',
                'RR': f"{latest_prediction.forecast_30d_respiratory_rate:.1f} /min" if latest_prediction.forecast_30d_respiratory_rate else 'N/A',
                'SpO2': f"{latest_prediction.forecast_30d_oxygen_saturation:.1f}%" if latest_prediction.forecast_30d_oxygen_saturation else 'N/A',
                'Temp': f"{latest_prediction.forecast_30d_temperature:.2f}°C" if latest_prediction.forecast_30d_temperature else 'N/A',
                'confidence': f"{max(0, latest_prediction.forecast_confidence - 0.25) * 100:.0f}%"
            }
        }
        forecast_data['60d'] = {
            '60 Days': {
                'HR': f"{(latest_prediction.forecast_30d_heart_rate or 0) * 1.05:.0f} bpm" if latest_prediction.forecast_30d_heart_rate else 'N/A',
                'RR': f"{(latest_prediction.forecast_30d_respiratory_rate or 0) * 1.03:.1f} /min" if latest_prediction.forecast_30d_respiratory_rate else 'N/A',
                'SpO2': f"{(latest_prediction.forecast_30d_oxygen_saturation or 0) * 0.97:.1f}%" if latest_prediction.forecast_30d_oxygen_saturation else 'N/A',
                'Temp': f"{(latest_prediction.forecast_30d_temperature or 0) * 1.02:.2f}°C" if latest_prediction.forecast_30d_temperature else 'N/A',
                'confidence': f"{max(0, latest_prediction.forecast_confidence - 0.3) * 100:.0f}%"
            }
        }
        forecast_data['90d'] = {
            '90 Days': {
                'HR': f"{latest_prediction.forecast_365d_heart_rate:.0f} bpm" if latest_prediction.forecast_365d_heart_rate else 'N/A',
                'RR': f"{latest_prediction.forecast_365d_respiratory_rate:.1f} /min" if latest_prediction.forecast_365d_respiratory_rate else 'N/A',
                'SpO2': f"{latest_prediction.forecast_365d_oxygen_saturation:.1f}%" if latest_prediction.forecast_365d_oxygen_saturation else 'N/A',
                'Temp': f"{latest_prediction.forecast_365d_temperature:.2f}°C" if latest_prediction.forecast_365d_temperature else 'N/A',
                'confidence': f"{max(0, latest_prediction.forecast_confidence - 0.35) * 100:.0f}%"
            }
        }

    # Current vitals with status
    current_vitals = {
        'heart_rate': f"{latest_vital.heart_rate}" if latest_vital and latest_vital.heart_rate else 'N/A',
        'respiratory_rate': f"{latest_vital.respiratory_rate}" if latest_vital and latest_vital.respiratory_rate else 'N/A',
        'spo2': f"{latest_vital.oxygen_saturation:.1f}" if latest_vital and latest_vital.oxygen_saturation else 'N/A',
        'temperature': f"{latest_vital.temperature:.2f}" if latest_vital and latest_vital.temperature else 'N/A',
        'hr_status': 'Normal' if latest_vital and latest_vital.heart_rate and 60 <= latest_vital.heart_rate <= 100 else 'Abnormal',
        'rr_status': 'Normal' if latest_vital and latest_vital.respiratory_rate and 12 <= latest_vital.respiratory_rate <= 20 else 'Abnormal',
        'spo2_status': 'Good' if latest_vital and latest_vital.oxygen_saturation and latest_vital.oxygen_saturation >= 95 else 'Concern',
        'temp_status': 'Normal' if latest_vital and latest_vital.temperature and 36.5 <= latest_vital.temperature <= 37.5 else 'Abnormal',
        'hr_critical': latest_vital and latest_vital.heart_rate and (latest_vital.heart_rate > 140 or latest_vital.heart_rate < 40),
        'rr_critical': latest_vital and latest_vital.respiratory_rate and (latest_vital.respiratory_rate > 35 or latest_vital.respiratory_rate < 8),
        'spo2_critical': latest_vital and latest_vital.oxygen_saturation and latest_vital.oxygen_saturation < 85,
        'temp_critical': latest_vital and latest_vital.temperature and (latest_vital.temperature > 39.5 or latest_vital.temperature < 35),
        'hr_warning': latest_vital and latest_vital.heart_rate and ((latest_vital.heart_rate > 120 and latest_vital.heart_rate <= 140) or (latest_vital.heart_rate >= 40 and latest_vital.heart_rate < 60)),
        'rr_warning': latest_vital and latest_vital.respiratory_rate and ((latest_vital.respiratory_rate > 30 and latest_vital.respiratory_rate <= 35) or (latest_vital.respiratory_rate >= 8 and latest_vital.respiratory_rate < 12)),
        'spo2_warning': latest_vital and latest_vital.oxygen_saturation and (85 <= latest_vital.oxygen_saturation < 95),
        'temp_warning': latest_vital and latest_vital.temperature and ((latest_vital.temperature > 37.5 and latest_vital.temperature <= 39.5) or (latest_vital.temperature >= 35 and latest_vital.temperature < 36.5)),
    }

    # Calculate confidence percentage for template
    forecast_confidence_percent = (latest_prediction.forecast_confidence * 100) if latest_prediction else 0

    # Last vital time formatted
    last_vital_time = latest_vital.recorded_at.strftime('%d %b, %H:%M') if latest_vital else 'N/A'

    context = {
        'patient': patient,
        'latest_vital': latest_vital,
        'latest_prediction': latest_prediction,
        'prediction_history': prediction_history,
        'recent_vitals': recent_vitals,
        'all_patients': all_patients,
        'prev_patient_url': f'/vitals/{prev_patient_id}/predictive/' if prev_patient_id else None,
        'next_patient_url': f'/vitals/{next_patient_id}/predictive/' if next_patient_id else None,
        'forecast_confidence_percent': forecast_confidence_percent,
        # Enhanced data
        'status_level': status_level,
        'status_message': status_message,
        'status_description': status_description,
        'data_alerts': data_alerts,
        'vitals_count': vitals_count,
        'last_vital_time': last_vital_time,
        'current_vitals': current_vitals,
        'hr_trend_data': json.dumps(hr_trend),
        'rr_trend_data': json.dumps(rr_trend),
        'spo2_trend_data': json.dumps(spo2_trend),
        'temp_trend_data': json.dumps(temp_trend),
        'forecast_data': json.dumps(forecast_data),
    }

    return render(request, 'vitals/predictive_dashboard_enhanced.html', context)


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
