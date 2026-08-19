"""
LINEAR TREND - Regression-Based Forecasting

This module implements linear regression for trend analysis.
It fits a straight line through historical data and extends it forward.

Mathematical Foundation:

LINEAR REGRESSION FORMULA:
y = mx + b

Where:
- y = predicted value (vital sign)
- x = time (which measurement number)
- m = slope (rate of change per time unit)
- b = intercept (value at time 0)

LEAST SQUARES METHOD (finding best fit line):
m = Σ(x_i - mean_x)(y_i - mean_y) / Σ(x_i - mean_x)²
b = mean_y - m * mean_x

Why Linear Trend?
- Detects steady increase/decrease (deterioration trends)
- Simple to understand and explain to clinicians
- Mathematically proven least-squares method
- Works well when data has clear directional trend
- Requires minimal assumptions about data distribution
"""

import numpy as np
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class LinearTrendForecaster:
    """
    Linear regression forecaster for vital signs.

    This method is effective for vital signs because:
    1. Detects sustained trends (e.g., gradual BP increase)
    2. Simple enough to explain to clinical staff
    3. Fast computation (O(n) complexity)
    4. Works with any amount of historical data
    5. Easy to interpret (slope = rate of change)
    """

    def __init__(self):
        """Initialize linear trend forecaster."""
        self.slope = None
        self.intercept = None
        self.forecast = None
        self.r_squared = None
        self.n_observations = None

    def _calculate_least_squares(self, x: np.ndarray, y: np.ndarray) -> Tuple[float, float]:
        """
        Calculate least squares regression line coefficients.

        This finds the line that minimizes the sum of squared residuals
        (vertical distances from points to line).

        Formula:
        m = Σ((x_i - mean_x)(y_i - mean_y)) / Σ((x_i - mean_x)²)
        b = mean_y - m * mean_x

        Args:
            x (np.ndarray): Time indices (0, 1, 2, ..., n-1)
            y (np.ndarray): Vital sign measurements

        Returns:
            Tuple[float, float]: (slope, intercept)
        """
        n = len(x)

        # Calculate means
        mean_x = np.mean(x)
        mean_y = np.mean(y)

        # Calculate slope numerator and denominator
        numerator = np.sum((x - mean_x) * (y - mean_y))
        denominator = np.sum((x - mean_x) ** 2)

        # Avoid division by zero
        if denominator == 0:
            return 0.0, mean_y

        # Calculate slope and intercept
        slope = numerator / denominator
        intercept = mean_y - (slope * mean_x)

        return slope, intercept

    def _calculate_r_squared(self, y_actual: np.ndarray, y_predicted: np.ndarray) -> float:
        """
        Calculate R-squared (coefficient of determination).

        R² measures how well the line fits the data (0-1, higher is better).
        R² = 1 - (SS_residual / SS_total)

        Args:
            y_actual (np.ndarray): Actual measurements
            y_predicted (np.ndarray): Predicted values from line

        Returns:
            float: R² value between 0 and 1
        """
        # Sum of squared residuals (errors)
        ss_residual = np.sum((y_actual - y_predicted) ** 2)

        # Total sum of squares
        mean_y = np.mean(y_actual)
        ss_total = np.sum((y_actual - mean_y) ** 2)

        # Avoid division by zero
        if ss_total == 0:
            return 0.0

        # Calculate R²
        r_squared = 1 - (ss_residual / ss_total)

        return float(max(0.0, r_squared))  # Clamp to [0, 1]

    def fit_and_predict(self, measurements: List[float]) -> float:
        """
        Fit linear regression model and forecast next value.

        Process:
        1. Create time index (0, 1, 2, ..., n-1)
        2. Calculate least squares slope and intercept
        3. Calculate R² to assess fit quality
        4. Forecast next value at time n

        Args:
            measurements (List[float]): Historical vital sign measurements

        Returns:
            float: Forecasted next value
        """
        if not measurements:
            raise ValueError("Measurements list cannot be empty")

        if len(measurements) < 2:
            # Not enough data for linear fit
            return float(measurements[0])

        y = np.array(measurements, dtype=np.float64)

        # Validate data
        if np.any(np.isnan(y)) or np.any(np.isinf(y)):
            raise ValueError("Measurements contain NaN or infinite values")

        # Step 1: Create time index
        x = np.arange(len(y), dtype=np.float64)

        # Step 2: Calculate least squares coefficients
        self.slope, self.intercept = self._calculate_least_squares(x, y)

        # Step 3: Calculate R² for model quality assessment
        y_predicted = self.intercept + self.slope * x
        self.r_squared = self._calculate_r_squared(y, y_predicted)

        # Step 4: Forecast next value
        # y = mx + b, where x = len(measurements) (next time point)
        next_x = len(measurements)
        self.forecast = float(self.intercept + self.slope * next_x)

        self.n_observations = len(measurements)

        return self.forecast

    def get_details(self) -> Dict:
        """
        Get detailed information about the linear model and forecast.

        Returns:
            Dict containing forecast, slope, intercept, and model quality
        """
        return {
            'forecast': self.forecast,
            'slope': self.slope,
            'intercept': self.intercept,
            'r_squared': self.r_squared,
            'n_observations': self.n_observations,
            'method': 'Linear Trend',
            'description': 'Straight line fit using least squares regression'
        }

    def interpret_trend(self) -> str:
        """
        Interpret what the trend means clinically.

        Args:
            None

        Returns:
            str: Clinical interpretation of the trend
        """
        if self.slope is None:
            return "No trend calculated yet"

        # Interpret based on slope direction and magnitude
        if abs(self.slope) < 0.5:
            direction = "stable"
        elif self.slope > 0:
            direction = f"increasing ({self.slope:.2f} units/measurement)"
        else:
            direction = f"decreasing ({self.slope:.2f} units/measurement)"

        # Add model quality assessment
        quality = ""
        if self.r_squared is not None:
            if self.r_squared > 0.7:
                quality = " - Strong fit (high confidence in trend)"
            elif self.r_squared > 0.4:
                quality = " - Moderate fit (some noise in trend)"
            else:
                quality = " - Weak fit (trend may be unclear)"

        return f"Trend is {direction}{quality}"


class PolynomialTrendForecaster:
    """
    Extension: Polynomial regression for more complex trends.

    If linear trend doesn't capture data well, can use quadratic (parabola).
    However, kept separate to maintain simplicity for primary analysis.
    """

    def __init__(self, degree: int = 2):
        """
        Initialize polynomial forecaster.

        Args:
            degree (int): Polynomial degree (2 = quadratic, 3 = cubic)
        """
        self.degree = degree
        self.coefficients = None
        self.forecast = None

    def fit_and_predict(self, measurements: List[float]) -> float:
        """Fit polynomial and predict next value."""
        if len(measurements) < self.degree + 1:
            return float(np.mean(measurements))

        y = np.array(measurements, dtype=np.float64)
        x = np.arange(len(y), dtype=np.float64)

        # Fit polynomial using numpy
        self.coefficients = np.polyfit(x, y, self.degree)

        # Predict next value
        next_x = len(measurements)
        self.forecast = float(np.polyval(self.coefficients, next_x))

        return self.forecast
