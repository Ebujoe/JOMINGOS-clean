"""
FORECASTING SERVICE - WEEK 3 INTEGRATION
=========================================

Integrates RobustForecastingEngine with the data foundation (Week 1-2).

Provides:
1. End-to-end forecasting pipeline
2. Forecast storage and retrieval
3. Uncertainty visualization data
4. Backtesting framework
5. Forecast accuracy tracking
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
import logging
import json

logger = logging.getLogger(__name__)


class ForecastingService:
    """
    High-level forecasting service that orchestrates:
    - Data collection (Week 1-2)
    - Model inference (RobustForecastingEngine)
    - Result storage
    - Performance tracking
    """

    def __init__(self):
        """Initialize forecasting service."""
        from .robust_forecasting_engine import RobustForecastingEngine

        self.engine = RobustForecastingEngine()
        logger.info("ForecastingService initialized")

    def generate_forecast_for_patient(
        self,
        patient_id: int,
        vital_name: str,
        horizon_hours: int = 24,
    ) -> Dict:
        """
        Generate forecast for a patient's vital sign.

        Args:
            patient_id: Patient ID
            vital_name: Vital sign name
            horizon_hours: Hours ahead to forecast (24, 168, 336, 720)

        Returns:
            Dict with forecast and uncertainty details
        """

        from vitals.models import VitalSigns, PatientBaselineData
        from patients.models import Patient
        from .robust_forecasting_engine import PatientBaseline

        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            logger.error(f"Patient {patient_id} not found")
            return {'error': 'Patient not found'}

        # Get historical measurements
        vitals = VitalSigns.objects.filter(
            patient=patient,
            vital_name=vital_name,
            is_approved=True,
        ).order_by('recorded_at')

        if not vitals.exists():
            logger.warning(f"No vitals for {vital_name} patient {patient_id}")
            return {
                'status': 'no_data',
                'message': 'No approved measurements available',
            }

        # Extract values and times
        historical_values = [float(v.value) for v in vitals]
        historical_times = [v.recorded_at for v in vitals]

        # Get patient baseline if available
        patient_baseline = None
        try:
            baseline_record = PatientBaselineData.objects.get(
                patient=patient,
                vital_name=vital_name,
            )
            patient_baseline = PatientBaseline(
                patient_id=patient_id,
                vital_name=vital_name,
                mean_value=float(baseline_record.mean_value),
                std_dev=float(baseline_record.std_dev),
                min_value=float(baseline_record.min_value),
                max_value=float(baseline_record.max_value),
                percentile_5=float(baseline_record.percentile_5),
                percentile_95=float(baseline_record.percentile_95),
                n_samples=baseline_record.n_samples,
                last_updated=baseline_record.updated_at,
            )
        except PatientBaselineData.DoesNotExist:
            pass

        # Generate prediction
        prediction = self.engine.generate_prediction(
            historical_values=historical_values,
            historical_times=historical_times,
            vital_name=vital_name,
            patient_baseline=patient_baseline,
            horizon_hours=horizon_hours,
        )

        # Convert to JSON-serializable format
        return self._prediction_to_dict(prediction)

    def generate_forecasts_for_all_vitals(
        self,
        patient_id: int,
        horizons: List[int] = None,
    ) -> Dict:
        """
        Generate forecasts for all vital types.

        Args:
            patient_id: Patient ID
            horizons: List of hours (default: [24, 168, 336])

        Returns:
            Dict of vital_name -> list of forecasts
        """

        if horizons is None:
            horizons = [24, 168, 336]  # 24h, 7d, 14d

        from vitals.models import VitalSigns

        # Get all vital types for this patient
        vital_types = (
            VitalSigns.objects.filter(patient_id=patient_id)
            .values_list('vital_name', flat=True)
            .distinct()
        )

        all_forecasts = {}

        for vital_name in vital_types:
            all_forecasts[vital_name] = []

            for horizon in horizons:
                forecast = self.generate_forecast_for_patient(
                    patient_id=patient_id,
                    vital_name=vital_name,
                    horizon_hours=horizon,
                )
                all_forecasts[vital_name].append(forecast)

        logger.info(f"Generated forecasts for {len(vital_types)} vitals (patient {patient_id})")

        return all_forecasts

    def store_forecast(
        self,
        patient_id: int,
        forecast_dict: Dict,
    ) -> 'PatientForecast':
        """
        Store forecast in database for tracking.

        Args:
            patient_id: Patient ID
            forecast_dict: Forecast data to store

        Returns:
            PatientForecast object
        """

        from vitals.models import PatientForecast

        forecast = PatientForecast.objects.create(
            patient_id=patient_id,
            vital_name=forecast_dict.get('vital_name'),
            horizon_hours=forecast_dict.get('horizon_hours'),
            forecast_value=Decimal(str(forecast_dict.get('forecast_value', 0))),
            confidence_score=forecast_dict.get('confidence_score', 0),
            prediction_interval_95_lower=Decimal(
                str(forecast_dict.get('prediction_interval_95_lower', 0))
            ),
            prediction_interval_95_upper=Decimal(
                str(forecast_dict.get('prediction_interval_95_upper', 0))
            ),
            prediction_interval_90_lower=Decimal(
                str(forecast_dict.get('prediction_interval_90_lower', 0))
            ),
            prediction_interval_90_upper=Decimal(
                str(forecast_dict.get('prediction_interval_90_upper', 0))
            ),
            forecast_reliability=forecast_dict.get('forecast_reliability', 'LOW'),
            recommendation=forecast_dict.get('recommendation', ''),
            clinical_notes=forecast_dict.get('clinical_notes', ''),
            forecast_details=json.dumps(forecast_dict),
        )

        logger.info(f"Stored forecast: {forecast.vital_name} for patient {patient_id}")

        return forecast

    def get_latest_forecast(
        self,
        patient_id: int,
        vital_name: str,
        horizon_hours: int = 24,
    ) -> Optional[Dict]:
        """Get latest forecast from database."""

        from vitals.models import PatientForecast

        try:
            forecast = PatientForecast.objects.filter(
                patient_id=patient_id,
                vital_name=vital_name,
                horizon_hours=horizon_hours,
            ).order_by('-created_at').first()

            if forecast:
                return json.loads(forecast.forecast_details)

        except Exception as e:
            logger.error(f"Error retrieving forecast: {e}")

        return None

    def generate_forecast_visualization_data(
        self,
        patient_id: int,
        vital_name: str,
        horizon_hours: int = 24,
    ) -> Dict:
        """
        Generate data for forecast visualization.

        Returns:
            Dict with historical data, forecast, and confidence bands
        """

        from vitals.models import VitalSigns

        # Get historical data
        vitals = VitalSigns.objects.filter(
            patient_id=patient_id,
            vital_name=vital_name,
            is_approved=True,
        ).order_by('recorded_at')[:100]

        historical_data = [
            {
                'timestamp': v.recorded_at.isoformat(),
                'value': float(v.value),
                'quality_score': v.quality_score or 100,
            }
            for v in vitals
        ]

        # Get forecast
        forecast = self.generate_forecast_for_patient(
            patient_id=patient_id,
            vital_name=vital_name,
            horizon_hours=horizon_hours,
        )

        # Calculate forecast timestamp
        if vitals.exists():
            forecast_timestamp = vitals.last().recorded_at + timedelta(hours=horizon_hours)
        else:
            forecast_timestamp = datetime.now() + timedelta(hours=horizon_hours)

        visualization_data = {
            'vital_name': vital_name,
            'horizon_hours': horizon_hours,
            'historical_data': historical_data,
            'forecast': {
                'timestamp': forecast_timestamp.isoformat(),
                'value': forecast.get('forecast_value'),
                'confidence_score': forecast.get('confidence_score', 0),
                'reliability': forecast.get('forecast_reliability', 'LOW'),
            },
            'uncertainty_bands': {
                'ci_95_lower': forecast.get('prediction_interval_95_lower'),
                'ci_95_upper': forecast.get('prediction_interval_95_upper'),
                'ci_90_lower': forecast.get('prediction_interval_90_lower'),
                'ci_90_upper': forecast.get('prediction_interval_90_upper'),
                'std_error': forecast.get('std_error'),
            },
            'recommendation': forecast.get('recommendation', ''),
            'caveats': forecast.get('caveats', []),
        }

        return visualization_data

    @staticmethod
    def _prediction_to_dict(prediction) -> Dict:
        """Convert PredictionWithUncertainty to dict."""

        return {
            'status': 'success',
            'vital_name': prediction.vital_name,
            'horizon_hours': prediction.horizon_hours,
            'forecast_value': prediction.forecast_value,
            'point_estimate': prediction.point_estimate,
            'confidence_score': prediction.confidence_score,
            'prediction_interval_95_lower': prediction.prediction_interval_95_lower,
            'prediction_interval_95_upper': prediction.prediction_interval_95_upper,
            'prediction_interval_90_lower': prediction.prediction_interval_90_lower,
            'prediction_interval_90_upper': prediction.prediction_interval_90_upper,
            'std_error': prediction.std_error,
            'model_agreement': prediction.model_agreement,
            'model_count': prediction.model_count,
            'models_used': prediction.models_used,
            'data_sufficiency': prediction.data_sufficiency,
            'extrapolation_distance': prediction.extrapolation_distance,
            'model_disagreement_component': prediction.model_disagreement_component,
            'data_sparsity_component': prediction.data_sparsity_component,
            'extrapolation_component': prediction.extrapolation_component,
            'patient_variability_component': prediction.patient_variability_component,
            'is_plausible': prediction.is_plausible,
            'plausibility_score': prediction.plausibility_score,
            'clinical_notes': prediction.clinical_notes,
            'forecast_reliability': prediction.forecast_reliability,
            'recommendation': prediction.recommendation,
            'caveats': prediction.caveats,
            'prediction_timestamp': prediction.prediction_timestamp.isoformat(),
        }


class BacktestingService:
    """
    Backtesting framework for validating forecast accuracy.

    Tests forecasts against actual future values.
    """

    @staticmethod
    def backtest_single_horizon(
        patient_id: int,
        vital_name: str,
        horizon_hours: int = 24,
        lookback_days: int = 30,
    ) -> Dict:
        """
        Backtest forecasts for a specific horizon.

        Methodology:
        1. For each historical point, generate forecast
        2. Compare to actual future value
        3. Calculate error metrics

        Returns:
            Backtest results with accuracy metrics
        """

        from vitals.models import VitalSigns

        vitals = list(
            VitalSigns.objects.filter(
                patient_id=patient_id,
                vital_name=vital_name,
                is_approved=True,
                recorded_at__gte=(
                    datetime.now() - timedelta(days=lookback_days)
                ),
            ).order_by('recorded_at')
        )

        if len(vitals) < 20:
            return {
                'status': 'insufficient_data',
                'message': f'Need 20+ vitals, have {len(vitals)}',
            }

        # Generate forecasts and compare to actuals
        forecasting_service = ForecastingService()
        errors = []
        forecasts_generated = 0

        for i in range(len(vitals) - 10):  # Keep last 10 as test set
            current_vital = vitals[i]
            future_vital = None

            # Find actual future value closest to forecast horizon
            for j in range(i + 1, len(vitals)):
                time_diff = (vitals[j].recorded_at - current_vital.recorded_at).total_seconds() / 3600
                if abs(time_diff - horizon_hours) < 12:  # Within 12 hours
                    future_vital = vitals[j]
                    break

            if not future_vital:
                continue

            # Generate forecast
            historical_values = [float(v.value) for v in vitals[:i+1]]
            historical_times = [v.recorded_at for v in vitals[:i+1]]

            forecast = forecasting_service.generate_forecast_for_patient(
                patient_id=patient_id,
                vital_name=vital_name,
                horizon_hours=horizon_hours,
            )

            if forecast.get('status') == 'success':
                error = abs(forecast['forecast_value'] - float(future_vital.value))
                errors.append({
                    'forecast': forecast['forecast_value'],
                    'actual': float(future_vital.value),
                    'error': error,
                    'confidence': forecast['confidence_score'],
                    'timestamp': current_vital.recorded_at.isoformat(),
                })
                forecasts_generated += 1

        if not errors:
            return {'status': 'no_comparable_forecasts'}

        # Calculate metrics
        import numpy as np

        forecast_values = np.array([e['forecast'] for e in errors])
        actual_values = np.array([e['actual'] for e in errors])
        errors_array = np.array([e['error'] for e in errors])

        mae = np.mean(errors_array)
        rmse = np.sqrt(np.mean(errors_array ** 2))
        mape = np.mean(np.abs(errors_array / actual_values)) * 100

        return {
            'status': 'success',
            'vital_name': vital_name,
            'horizon_hours': horizon_hours,
            'forecasts_tested': forecasts_generated,
            'accuracy_metrics': {
                'mae': float(mae),
                'rmse': float(rmse),
                'mape': float(mape),
            },
            'forecast_errors': errors,
        }

    @staticmethod
    def backtest_all_horizons(
        patient_id: int,
        vital_name: str,
    ) -> Dict:
        """Backtest all standard horizons."""

        horizons = [24, 168, 336, 720]  # 24h, 7d, 14d, 30d
        results = {}

        for horizon in horizons:
            result = BacktestingService.backtest_single_horizon(
                patient_id=patient_id,
                vital_name=vital_name,
                horizon_hours=horizon,
            )
            results[f'{horizon}h'] = result

        return results
