"""
Phase 10: Predictive Forecasting Engine

Forecasts future vital signs using multiple time-series models:
- Linear regression (simple trend continuation)
- Exponential smoothing (weighted recent history)
- Moving average (smoothed trend)

Provides predictions for 24, 48, and 72 hours ahead.
"""

import numpy as np
from datetime import timedelta
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class ForecastingEngine:
    """
    Time-series forecasting for vital signs.

    Uses multiple models to predict future vital values based on
    historical readings. Combines predictions for robustness.
    """

    def __init__(self, min_readings: int = 3):
        """
        Initialize forecasting engine.

        Args:
            min_readings: Minimum historical readings required for forecast
        """
        self.min_readings = min_readings
        self.forecast_horizons = [24, 48, 72]  # hours

    def forecast_vital(
        self,
        historical_values: List[float],
        historical_times: List[float],
        horizon_hours: int = 24,
    ) -> Dict:
        """
        Forecast a single vital sign value.

        Args:
            historical_values: Past vital sign measurements
            historical_times: Time points (in hours from now, negative = past)
            horizon_hours: Hours ahead to forecast

        Returns:
            Dictionary with forecasted value and confidence
        """
        if len(historical_values) < self.min_readings:
            return {
                'forecast': None,
                'confidence': 0,
                'reason': 'insufficient_data'
            }

        try:
            # Convert to numpy arrays
            times = np.array(historical_times, dtype=float)
            values = np.array(historical_values, dtype=float)

            # Linear regression forecast
            linear_forecast = self._linear_regression_forecast(
                values, times, horizon_hours
            )

            # Exponential smoothing forecast
            exp_forecast = self._exponential_smoothing_forecast(
                values, horizon_hours
            )

            # Moving average forecast
            ma_forecast = self._moving_average_forecast(
                values, times, horizon_hours
            )

            # Combine forecasts (weighted average)
            combined_forecast = self._combine_forecasts(
                linear_forecast, exp_forecast, ma_forecast, values
            )

            return {
                'forecast': round(combined_forecast['value'], 2),
                'confidence': round(combined_forecast['confidence'], 2),
                'models': {
                    'linear': round(linear_forecast, 2),
                    'exponential': round(exp_forecast, 2),
                    'moving_average': round(ma_forecast, 2),
                },
                'trend': self._calculate_trend(values, times),
            }

        except Exception as e:
            logger.error(f"Forecasting error: {e}")
            return {
                'forecast': None,
                'confidence': 0,
                'reason': str(e)
            }

    def _linear_regression_forecast(
        self,
        values: np.ndarray,
        times: np.ndarray,
        horizon: int,
    ) -> float:
        """
        Linear regression forecast: y = mx + b
        Extrapolates current trend linearly.
        """
        if len(values) < 2:
            return values[-1]

        coefficients = np.polyfit(times, values, 1)
        slope, intercept = coefficients[0], coefficients[1]
        forecast = slope * horizon + intercept
        return forecast

    def _exponential_smoothing_forecast(
        self,
        values: np.ndarray,
        horizon: int,
    ) -> float:
        """
        Exponential smoothing (Simple Exponential Smoothing).
        Gives more weight to recent observations.
        """
        alpha = 0.3  # Smoothing factor (0-1)

        # Calculate smoothed values
        smoothed = [values[0]]
        for i in range(1, len(values)):
            smoothed_val = alpha * values[i] + (1 - alpha) * smoothed[i - 1]
            smoothed.append(smoothed_val)

        # Forecast: the last smoothed value (constant in SES)
        # For deterioration trends, use last value as anchor
        return smoothed[-1]

    def _moving_average_forecast(
        self,
        values: np.ndarray,
        times: np.ndarray,
        horizon: int,
    ) -> float:
        """
        Moving average with trend.
        Calculates trend from recent readings and projects forward.
        """
        if len(values) < 2:
            return values[-1]

        # Use last 3 readings to calculate trend
        window = min(3, len(values))
        recent_values = values[-window:]
        recent_times = times[-window:]

        # Calculate trend per hour
        if len(recent_times) >= 2:
            time_diff = recent_times[-1] - recent_times[0]
            if time_diff != 0:
                trend_per_hour = (recent_values[-1] - recent_values[0]) / time_diff
            else:
                trend_per_hour = 0
        else:
            trend_per_hour = 0

        # Project forward
        base_value = recent_values[-1]
        forecast = base_value + (trend_per_hour * horizon)
        return forecast

    def _combine_forecasts(
        self,
        linear: float,
        exponential: float,
        moving_avg: float,
        historical_values: np.ndarray,
    ) -> Dict:
        """
        Combine multiple forecasts using weighted average.
        Weights based on value stability.
        """
        forecasts = np.array([linear, exponential, moving_avg])

        # Weight by inverse of variance from historical mean
        hist_mean = np.mean(historical_values)
        hist_std = np.std(historical_values)

        if hist_std > 0:
            # More stable forecasts get higher weight
            deviations = np.abs(forecasts - hist_mean)
            weights = 1 / (1 + deviations / hist_std)
        else:
            weights = np.array([1 / 3, 1 / 3, 1 / 3])

        # Normalize weights
        weights = weights / np.sum(weights)

        # Combined forecast
        combined_value = np.sum(forecasts * weights)

        # Confidence: inverse of model disagreement
        model_std = np.std(forecasts)
        confidence = 1 / (1 + model_std / hist_std) if hist_std > 0 else 0.7

        return {
            'value': combined_value,
            'confidence': min(confidence, 0.95),  # Cap at 95%
            'weights': {
                'linear': round(weights[0], 2),
                'exponential': round(weights[1], 2),
                'moving_average': round(weights[2], 2),
            }
        }

    def _calculate_trend(self, values: np.ndarray, times: np.ndarray) -> Dict:
        """
        Calculate trend direction and magnitude.
        """
        if len(values) < 2:
            return {'direction': 'stable', 'magnitude': 0}

        # Calculate overall trend
        coefficients = np.polyfit(times, values, 1)
        slope = coefficients[0]

        if abs(slope) < 0.1:
            direction = 'stable'
        elif slope > 0:
            direction = 'rising'
        else:
            direction = 'falling'

        return {
            'direction': direction,
            'magnitude': round(slope, 3),
            'interpretation': f"Changing {abs(slope):.2f} units/hour"
        }

    def forecast_all_vitals(
        self,
        vital_history: Dict[str, List[Dict]],
        horizon_hours: int = 24,
    ) -> Dict:
        """
        Forecast all vital signs from complete history.

        Args:
            vital_history: {
                'heart_rate': [{'value': 75, 'time_hours_ago': -24}, ...],
                'respiratory_rate': [...],
                ...
            }
            horizon_hours: Hours ahead to forecast

        Returns:
            Forecasts for all vitals
        """
        forecasts = {}

        for vital_name, readings in vital_history.items():
            if not readings:
                continue

            # Extract values and times
            values = [r['value'] for r in readings if r['value'] is not None]
            times = [r['time_hours_ago'] for r in readings if r['value'] is not None]

            if values and times:
                forecasts[vital_name] = self.forecast_vital(
                    values, times, horizon_hours
                )

        return forecasts
