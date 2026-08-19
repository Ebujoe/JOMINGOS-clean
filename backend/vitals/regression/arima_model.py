"""
ARIMA - AutoRegressive Integrated Moving Average

This module implements a simplified ARIMA model for time series forecasting.
ARIMA detects and uses patterns in how measurements change over time.

Mathematical Foundation:

1. DIFFERENCING (I - Integrated):
   First differences remove trend:
   diff_t = X_t - X_{t-1}

   This transforms non-stationary data (trending) to stationary (no trend)

2. AUTOREGRESSION (AR):
   AR(1) model on differenced data:
   diff_t = φ * diff_{t-1} + ε_t

   Where:
   - φ = autoregressive coefficient (correlation of lag-1)
   - ε_t = random error term

3. FORECAST:
   next_diff = φ * last_diff
   next_value = last_value + next_diff

Why ARIMA?
- Captures trend changes (e.g., heart rate gradually increasing)
- Uses patterns in differences (not raw values)
- Handles non-stationary time series naturally
- Proven method in healthcare and weather forecasting
- More sophisticated than simple moving average
"""

import numpy as np
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class ARIMAForecaster:
    """
    ARIMA forecaster for vital signs time series.

    This method is effective for vital signs because:
    1. It detects trends (heart rate trending up indicates deterioration)
    2. It uses autoregressive patterns (patient rhythms/patterns)
    3. It's robust to non-stationary data (vital signs can drift over time)
    4. It combines differencing, autoregression, and smoothing
    """

    def __init__(self, p: int = 1, d: int = 1, q: int = 0):
        """
        Initialize ARIMA parameters.

        Args:
            p (int): Autoregressive order (how many past differences to use)
                     p=1 means use immediately previous difference
            d (int): Differencing order (d=1 means first differences)
                     d=0 would mean no differencing (for stationary data)
            q (int): Moving average order (q=0 for simplified version)
                     Full ARIMA uses this, we use simplified ARIMA
        """
        self.p = p  # AR order
        self.d = d  # Differencing order
        self.q = q  # MA order (kept at 0 for simplicity)
        self.forecast = None
        self.ar_coefficient = None
        self.differenced_data = None
        self.original_data = None

    def _difference(self, data: np.ndarray, order: int = 1) -> np.ndarray:
        """
        Compute differences of a time series.

        Args:
            data (np.ndarray): Original time series
            order (int): Order of differencing (1 = first difference, 2 = second difference)

        Returns:
            np.ndarray: Differenced series
        """
        differenced = data.copy()
        for _ in range(order):
            differenced = np.diff(differenced)
        return differenced

    def _calculate_ar_coefficient(self, diff_data: np.ndarray) -> float:
        """
        Calculate autoregressive coefficient φ using correlation.

        This measures how strongly the current difference is related to
        the previous difference. High correlation = strong autoregressive pattern.

        Args:
            diff_data (np.ndarray): Differenced time series

        Returns:
            float: AR coefficient between -1 and 1
        """
        if len(diff_data) < 2:
            return 0.0

        # Correlation between current and lagged values
        lag_1 = diff_data[:-1]  # t-1
        current = diff_data[1:]  # t

        # Calculate Pearson correlation
        if len(lag_1) > 1 and np.std(lag_1) > 0 and np.std(current) > 0:
            correlation = np.corrcoef(lag_1, current)[0, 1]

            # Handle NaN (occurs when std is 0, meaning no variation)
            if np.isnan(correlation):
                return 0.0

            return float(correlation)
        else:
            return 0.0

    def _undifference(self, last_value: float, forecast_diff: float) -> float:
        """
        Reverse the differencing to get back to original scale.

        If we differenced once: next_value = last_value + forecast_diff
        If we differenced twice: apply twice

        Args:
            last_value (float): Last original observation
            forecast_diff (float): Forecast in differenced scale

        Returns:
            float: Forecast in original scale
        """
        # For d=1 (first differencing)
        return last_value + forecast_diff

    def fit_and_predict(self, measurements: List[float]) -> float:
        """
        Fit ARIMA model and generate forecast.

        Process:
        1. Difference the data (remove trend)
        2. Calculate AR coefficient (how much last change predicts next change)
        3. Forecast the next difference
        4. Reverse differencing (back to original scale)

        Args:
            measurements (List[float]): Historical vital sign measurements

        Returns:
            float: Forecasted next value
        """
        if not measurements:
            raise ValueError("Measurements list cannot be empty")

        if len(measurements) < 3:
            # Not enough data for ARIMA, return mean
            return float(np.mean(measurements))

        self.original_data = np.array(measurements, dtype=np.float64)

        # Validate data
        if np.any(np.isnan(self.original_data)) or np.any(np.isinf(self.original_data)):
            raise ValueError("Measurements contain NaN or infinite values")

        # Step 1: Difference the data (remove trend)
        self.differenced_data = self._difference(self.original_data, order=self.d)

        # Step 2: Calculate AR coefficient on differenced data
        self.ar_coefficient = self._calculate_ar_coefficient(self.differenced_data)

        # Step 3: Forecast next difference using AR(1)
        # diff_{t+1} = φ * diff_t
        last_difference = self.differenced_data[-1] if len(self.differenced_data) > 0 else 0.0
        forecast_difference = self.ar_coefficient * last_difference

        # Step 4: Reverse differencing to get forecast in original scale
        last_original_value = self.original_data[-1]
        self.forecast = self._undifference(last_original_value, forecast_difference)

        return self.forecast

    def get_details(self) -> Dict:
        """
        Get detailed information about the ARIMA model and forecast.

        Returns:
            Dict containing forecast, model coefficients, and metadata
        """
        return {
            'forecast': self.forecast,
            'ar_coefficient': self.ar_coefficient,
            'p': self.p,
            'd': self.d,
            'q': self.q,
            'differenced_data': self.differenced_data.tolist() if self.differenced_data is not None else [],
            'method': 'ARIMA',
            'description': 'Captures trends and autoregressive patterns in vital signs'
        }


def interpret_ar_coefficient(ar_coeff: float) -> str:
    """
    Interpret what the AR coefficient means clinically.

    Args:
        ar_coeff (float): Autoregressive coefficient

    Returns:
        str: Interpretation of the pattern
    """
    if abs(ar_coeff) < 0.1:
        return "No autoregressive pattern (random fluctuations)"
    elif 0.1 <= ar_coeff < 0.5:
        return "Weak positive pattern (slight momentum)"
    elif 0.5 <= ar_coeff < 0.8:
        return "Strong positive pattern (momentum, trending)"
    elif ar_coeff >= 0.8:
        return "Very strong positive pattern (strong trend, possible deterioration)"
    elif -0.5 < ar_coeff <= -0.1:
        return "Weak negative pattern (oscillation)"
    else:
        return "Strong negative pattern (oscillation or reversal)"
