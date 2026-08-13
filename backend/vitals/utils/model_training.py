"""
MODEL TRAINING - Data-Driven Forecasting

Trains forecasting models on actual vital signs data from care home.
Uses time series methods to generate data-backed predictions.
"""

import numpy as np
from typing import Dict, List, Tuple
from datetime import timedelta
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class TimeSeriesModel:
    """Base time series forecasting model."""

    def __init__(self, data: List[float], window: int = 14):
        """Initialize with historical data."""
        self.data = np.array(data)
        self.window = min(window, len(data) // 2)
        self.mean = np.mean(data)
        self.std = np.std(data)

    def fit_exponential_smoothing(self, alpha: float = 0.3) -> float:
        """Simple exponential smoothing forecast."""
        if len(self.data) < 2:
            return self.mean

        s = self.data[0]
        for t in range(1, len(self.data)):
            s = alpha * self.data[t] + (1 - alpha) * s

        return float(s)

    def fit_moving_average(self, window: int = None) -> float:
        """Simple moving average forecast."""
        if window is None:
            window = self.window
        if len(self.data) < window:
            return float(np.mean(self.data))
        return float(np.mean(self.data[-window:]))

    def fit_linear_trend(self) -> float:
        """Linear regression trend forecast."""
        if len(self.data) < 3:
            return self.mean

        x = np.arange(len(self.data))
        coeffs = np.polyfit(x, self.data, 1)
        slope, intercept = coeffs

        # Next value (assume 1 step ahead)
        next_x = len(self.data)
        return float(intercept + slope * next_x)

    def fit_arima_simple(self) -> float:
        """Simplified ARIMA using differencing and autoregression."""
        if len(self.data) < 3:
            return self.mean

        # First difference (remove trend)
        diff = np.diff(self.data)

        # AR(1) on differenced data
        if len(diff) > 1:
            ar_coeff = np.corrcoef(diff[:-1], diff[1:])[0, 1]
            if np.isnan(ar_coeff):
                ar_coeff = 0
        else:
            ar_coeff = 0

        # Forecast: last_diff + AR correction
        last_diff = diff[-1] if len(diff) > 0 else 0
        next_diff = ar_coeff * last_diff

        # Undifference
        return float(self.data[-1] + next_diff)

    def ensemble_forecast(self) -> Tuple[float, float]:
        """Ensemble of 4 models with weighted average."""
        models = {
            'exp_smooth': self.fit_exponential_smoothing(),
            'ma': self.fit_moving_average(),
            'linear': self.fit_linear_trend(),
            'arima': self.fit_arima_simple(),
        }

        # Weighted ensemble: ARIMA 35%, Exp Smooth 25%, Linear 20%, MA 20%
        weights = {
            'arima': 0.35,
            'exp_smooth': 0.25,
            'linear': 0.20,
            'ma': 0.20,
        }

        forecast = sum(models[k] * weights[k] for k in models)

        # Calculate uncertainty based on model disagreement
        values = list(models.values())
        model_std = np.std(values)
        data_uncertainty = self.std

        # Combined uncertainty: data variability + model disagreement
        uncertainty = np.sqrt(data_uncertainty ** 2 + model_std ** 2)

        return float(forecast), float(uncertainty)


class ModelTrainer:
    """Train forecasting models on patient vital signs data."""

    @staticmethod
    def train_patient_models(patient, vital_name: str) -> Dict:
        """
        Train ensemble model for specific vital sign.

        Args:
            patient: Patient object
            vital_name: Vital sign name (heart_rate, etc.)

        Returns:
            Dictionary with forecast, confidence, prediction intervals
        """
        from vitals.models import VitalSigns

        # Get historical data
        vitals = VitalSigns.objects.filter(patient=patient).order_by('recorded_at')

        if vital_name == 'heart_rate':
            data = [v.heart_rate for v in vitals if v.heart_rate]
        elif vital_name == 'respiratory_rate':
            data = [v.respiratory_rate for v in vitals if v.respiratory_rate]
        elif vital_name == 'oxygen_saturation':
            data = [float(v.oxygen_saturation) for v in vitals if v.oxygen_saturation]
        elif vital_name == 'temperature':
            data = [float(v.temperature) for v in vitals if v.temperature]
        else:
            data = []

        if len(data) < 10:
            return {
                'status': 'insufficient_data',
                'n_points': len(data),
            }

        # Train model
        model = TimeSeriesModel(data, window=min(14, len(data) // 2))
        forecast, uncertainty = model.ensemble_forecast()

        # Calculate confidence score
        # High data volume → high confidence
        # Stable data → high confidence
        # High uncertainty → low confidence

        n_points = len(data)
        data_stability = 1 - min(np.std(data) / np.mean(data), 1) if np.mean(data) > 0 else 0.5

        confidence_base = 50
        confidence_base += min((n_points - 10) / 50 * 30, 30)  # Up to +30 for data volume
        confidence_base += data_stability * 15  # Up to +15 for stability
        confidence_base -= (uncertainty / np.mean(data) * 20) if np.mean(data) > 0 else 10  # Penalize uncertainty

        confidence = max(20, min(95, confidence_base))

        # Prediction intervals
        pi_90_margin = uncertainty * 1.645  # 90% confidence
        pi_95_margin = uncertainty * 1.96   # 95% confidence

        return {
            'status': 'success',
            'forecast_value': float(forecast),
            'confidence_score': float(confidence),
            'uncertainty': float(uncertainty),
            'prediction_interval_90_lower': float(forecast - pi_90_margin),
            'prediction_interval_90_upper': float(forecast + pi_90_margin),
            'prediction_interval_95_lower': float(forecast - pi_95_margin),
            'prediction_interval_95_upper': float(forecast + pi_95_margin),
            'forecast_reliability': (
                'HIGH' if confidence >= 80
                else 'MEDIUM' if confidence >= 60
                else 'LOW'
            ),
            'recommendation': (
                'Safe for clinical use' if confidence >= 80
                else 'Monitor closely' if confidence >= 60
                else 'Manual review recommended'
            ),
            'n_training_points': len(data),
            'data_mean': float(np.mean(data)),
            'data_std': float(np.std(data)),
        }
