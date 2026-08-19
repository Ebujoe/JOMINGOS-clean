"""
EXPONENTIAL SMOOTHING - Time Series Forecasting Method

This module implements exponential smoothing, a statistical method that gives
more weight to recent observations when forecasting future values.

Mathematical Foundation:
    S_t = α * X_t + (1 - α) * S_{t-1}

    Where:
    - S_t = smoothed value at time t
    - X_t = actual observation at time t
    - α = smoothing coefficient (0.3 by default, between 0-1)
    - S_{t-1} = previous smoothed value

Why This Method?
- Healthcare data often has short-term fluctuations (noise)
- Recent vital signs more predictive than old measurements
- Fast to compute (no complex matrix operations)
- Works well for stable patients with small variations
"""

import numpy as np
from typing import List, Dict, Tuple


class ExponentialSmoothingForecaster:
    """
    Exponential smoothing forecaster for vital signs.

    This method is particularly effective for vital signs because:
    1. It adapts quickly to changes (good for detecting deterioration)
    2. It gives more weight to recent measurements
    3. It's simple but mathematically sound
    4. It requires minimal historical data (works with as few as 2 measurements)
    """

    def __init__(self, alpha: float = 0.3):
        """
        Initialize the exponential smoothing forecaster.

        Args:
            alpha (float): Smoothing coefficient (0 < alpha <= 1)
                - Higher alpha (0.7): Reacts quickly to changes (more responsive)
                - Lower alpha (0.1): Smoother predictions (more stable)
                - Default 0.3: Balance between responsiveness and stability
        """
        if not (0 < alpha <= 1):
            raise ValueError(f"Alpha must be between 0 and 1, got {alpha}")
        self.alpha = alpha
        self.forecast = None
        self.smoothed_series = None

    def fit_and_predict(self, measurements: List[float]) -> float:
        """
        Fit the exponential smoothing model and make a forecast.

        Args:
            measurements (List[float]): Historical vital sign measurements

        Returns:
            float: Forecasted next value

        Raises:
            ValueError: If measurements list is empty or contains invalid data
        """
        if not measurements:
            raise ValueError("Measurements list cannot be empty")

        # Convert to numpy array for numerical operations
        data = np.array(measurements, dtype=np.float64)

        # Validate data
        if np.any(np.isnan(data)) or np.any(np.isinf(data)):
            raise ValueError("Measurements contain NaN or infinite values")

        self.smoothed_series = []

        # Initialize with first value
        smoothed_value = data[0]
        self.smoothed_series.append(smoothed_value)

        # Apply exponential smoothing formula to each observation
        for t in range(1, len(data)):
            # S_t = α * X_t + (1 - α) * S_{t-1}
            smoothed_value = (self.alpha * data[t]) + ((1 - self.alpha) * smoothed_value)
            self.smoothed_series.append(smoothed_value)

        # Forecast the next value (continuation of the smoothed series)
        self.forecast = float(smoothed_value)

        return self.forecast

    def get_details(self) -> Dict:
        """
        Get detailed information about the forecast.

        Returns:
            Dict containing forecast, smoothing coefficient, and series
        """
        return {
            'forecast': self.forecast,
            'alpha': self.alpha,
            'smoothed_series': self.smoothed_series,
            'method': 'Exponential Smoothing',
            'description': 'Recent observations weighted more heavily'
        }


def calculate_optimal_alpha(measurements: List[float]) -> float:
    """
    Calculate an optimal smoothing coefficient based on data variability.

    This is an advanced technique to automatically tune alpha based on
    how stable or volatile the patient's vital signs are.

    Logic:
    - Stable patients (low variation): use lower alpha (0.1-0.2)
    - Variable patients (high variation): use higher alpha (0.4-0.5)

    Args:
        measurements (List[float]): Historical measurements

    Returns:
        float: Optimal alpha value
    """
    data = np.array(measurements, dtype=np.float64)

    # Calculate coefficient of variation (std / mean)
    mean = np.mean(data)
    std = np.std(data)

    if mean == 0:
        return 0.3  # Default for edge case

    cv = std / mean

    # Map variability to alpha
    # High CV (variable) -> higher alpha (more responsive)
    # Low CV (stable) -> lower alpha (more stable)
    if cv < 0.05:
        alpha = 0.2  # Very stable
    elif cv < 0.10:
        alpha = 0.3  # Stable
    elif cv < 0.15:
        alpha = 0.4  # Moderate variation
    else:
        alpha = 0.5  # High variation

    return alpha
