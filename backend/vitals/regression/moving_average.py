"""
MOVING AVERAGE - Smoothing-Based Forecasting

This module implements moving average methods for smoothing noise
and identifying underlying trends in vital signs data.

Mathematical Foundation:

SIMPLE MOVING AVERAGE (SMA):
MA_t = (X_t + X_{t-1} + X_{t-2} + ... + X_{t-n+1}) / n

Where:
- MA_t = moving average at time t
- X_t = observation at time t
- n = window size (e.g., 3 = average of last 3 measurements)

WEIGHTED MOVING AVERAGE (optional enhancement):
WMA_t = (w_1*X_t + w_2*X_{t-1} + ... + w_n*X_{t-n+1}) / Σ(weights)

Where weights are typically [1, 2, 3, ...] for more recent values

Why Moving Average?
- Removes short-term noise/fluctuations
- Reveals underlying trends
- Easy to compute and understand
- Robust to outliers (unlike single measurements)
- Used widely in medical monitoring
"""

import numpy as np
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class MovingAverageForecaster:
    """
    Moving average forecaster for vital signs.

    This method is effective for vital signs because:
    1. Smooths out measurement noise and artifacts
    2. Highlights true trends by averaging fluctuations
    3. Simple and transparent to clinical staff
    4. Works well with high-frequency monitoring
    5. Automatically adapts to available data (window size)
    """

    def __init__(self, window: int = 3):
        """
        Initialize moving average forecaster.

        Args:
            window (int): Number of recent measurements to average
                         Default 3 = average of last 3 measurements
                         Higher values = smoother but slower to detect changes
                         Lower values = more responsive but noisier
        """
        if window < 1:
            raise ValueError("Window size must be at least 1")
        self.window = window
        self.forecast = None
        self.used_window = None
        self.averaged_values = None

    def _calculate_simple_ma(self, measurements: np.ndarray) -> float:
        """
        Calculate simple moving average of recent measurements.

        Formula: SMA = (X_1 + X_2 + ... + X_n) / n

        Args:
            measurements (np.ndarray): All measurements

        Returns:
            float: Simple moving average of last 'window' measurements
        """
        # Use actual window size (may be smaller than requested if not enough data)
        actual_window = min(self.window, len(measurements))
        self.used_window = actual_window

        # Take last 'actual_window' measurements and calculate mean
        recent_measurements = measurements[-actual_window:]
        ma = np.mean(recent_measurements)

        return float(ma)

    def _calculate_weighted_ma(self, measurements: np.ndarray) -> float:
        """
        Calculate weighted moving average (recent values weighted more).

        Recent measurements given higher weight:
        Weight for measurement at position i: (i + 1)

        Formula: WMA = Σ(weight_i * X_i) / Σ(weight_i)

        Args:
            measurements (np.ndarray): All measurements

        Returns:
            float: Weighted moving average
        """
        actual_window = min(self.window, len(measurements))
        self.used_window = actual_window

        recent_measurements = measurements[-actual_window:]

        # Create weights: [1, 2, 3, ...] so most recent is heaviest
        weights = np.arange(1, actual_window + 1, dtype=np.float64)

        # Calculate weighted average
        wma = np.average(recent_measurements, weights=weights)

        return float(wma)

    def _calculate_exponential_weighted_ma(self, measurements: np.ndarray, alpha: float = 0.3) -> float:
        """
        Calculate exponential weighted moving average.

        Similar to exponential smoothing but formulated as moving average.
        Recent values given exponentially higher weights.

        Args:
            measurements (np.ndarray): All measurements
            alpha (float): Smoothing factor (0-1)

        Returns:
            float: Exponential weighted average
        """
        actual_window = min(self.window, len(measurements))
        self.used_window = actual_window

        recent_measurements = measurements[-actual_window:]

        # Create exponential weights: recent = heavier
        positions = np.arange(actual_window, dtype=np.float64)
        weights = alpha ** (actual_window - 1 - positions)
        weights = weights / np.sum(weights)  # Normalize to sum to 1

        # Calculate weighted average
        ewma = np.average(recent_measurements, weights=weights)

        return float(ewma)

    def fit_and_predict(self, measurements: List[float], method: str = 'simple') -> float:
        """
        Calculate moving average and use it as forecast.

        Assumption: The moving average of past values is our best estimate
        of the current state, so we forecast it continuing.

        Args:
            measurements (List[float]): Historical vital sign measurements
            method (str): 'simple', 'weighted', or 'exponential'

        Returns:
            float: Forecasted value (the moving average)
        """
        if not measurements:
            raise ValueError("Measurements list cannot be empty")

        data = np.array(measurements, dtype=np.float64)

        # Validate data
        if np.any(np.isnan(data)) or np.any(np.isinf(data)):
            raise ValueError("Measurements contain NaN or infinite values")

        # Calculate moving average using chosen method
        if method == 'weighted':
            self.forecast = self._calculate_weighted_ma(data)
        elif method == 'exponential':
            self.forecast = self._calculate_exponential_weighted_ma(data)
        else:  # 'simple'
            self.forecast = self._calculate_simple_ma(data)

        return self.forecast

    def get_details(self) -> Dict:
        """
        Get detailed information about the moving average calculation.

        Returns:
            Dict containing forecast, window size, and metadata
        """
        return {
            'forecast': self.forecast,
            'window_requested': self.window,
            'window_used': self.used_window,
            'method': 'Moving Average',
            'description': 'Average of recent measurements'
        }

    @staticmethod
    def calculate_optimal_window(data_length: int) -> int:
        """
        Calculate optimal window size based on data length.

        Heuristic:
        - Short data (< 10): use all data (window = data_length)
        - Medium data (10-30): use ~33% (window ≈ n/3)
        - Long data (> 30): use ~20% (window ≈ n/5)

        Args:
            data_length (int): Number of measurements

        Returns:
            int: Suggested window size
        """
        if data_length < 10:
            return max(2, data_length)
        elif data_length < 30:
            return max(3, data_length // 3)
        else:
            return max(5, data_length // 5)


class CumulativeMovingAverageForecaster:
    """
    Cumulative moving average (all-time average, updated with each new measurement).

    Useful as a simple baseline: the overall average of all measurements
    to date. Often used as a baseline method in ensemble forecasting.
    """

    def __init__(self):
        """Initialize cumulative moving average."""
        self.forecast = None

    def fit_and_predict(self, measurements: List[float]) -> float:
        """
        Calculate cumulative (all-time) moving average.

        Args:
            measurements (List[float]): All historical measurements

        Returns:
            float: Average of all measurements
        """
        if not measurements:
            raise ValueError("Measurements list cannot be empty")

        data = np.array(measurements, dtype=np.float64)

        if np.any(np.isnan(data)) or np.any(np.isinf(data)):
            raise ValueError("Measurements contain NaN or infinite values")

        self.forecast = float(np.mean(data))
        return self.forecast

    def get_details(self) -> Dict:
        """Get cumulative moving average details."""
        return {
            'forecast': self.forecast,
            'method': 'Cumulative Moving Average',
            'description': 'All-time average (baseline method)'
        }
