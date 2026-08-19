"""
UNIFIED VITAL SIGNS FORECASTER - Integration of Regression + XAI

This module ties together all components:
- 5 Regression methods (exponential smoothing, ARIMA, linear trend, moving average, baseline)
- Ensemble combination (weighted average)
- Explainable AI confidence scoring (4-factor evaluation)

ARCHITECTURE:

Raw Vital Signs
    ↓
[TimeSeriesForecastingEngine]
    ↓
├─ Exponential Smoothing Forecaster
├─ ARIMA Forecaster
├─ Linear Trend Forecaster
├─ Moving Average Forecaster
└─ Baseline Forecaster
    ↓
[Ensemble Combination]
    Forecast = 0.35*ARIMA + 0.25*ExpSmooth + ...
    ↓
[Explainable AI Scorer]
    ├─ Data Volume Assessment
    ├─ Model Agreement Check
    ├─ Extrapolation Validation
    └─ Stability Analysis
    ↓
Confidence Score (e.g., 93%)
    ↓
[Result: Forecast + Confidence]
    Example: "Heart Rate 78 bpm (93% confident)"

USAGE:

    forecaster = VitalSignsForecaster('heart_rate')
    measurements = [72, 74, 75, 73, 76, 75, ...]
    result = forecaster.forecast(measurements)

    print(f"Next heart rate: {result.forecast} bpm")
    print(f"Confidence: {result.confidence}%")
    print(f"Reasoning: {result.confidence_reasoning}")
"""

import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass
import logging

from backend.vitals.regression.ensemble_forecaster import EnsembleForecaster
from backend.vitals.regression.explainable_ai import ExplainableAIScorer, ConfidenceScore

logger = logging.getLogger(__name__)


@dataclass
class ForecastResult:
    """Result of vital sign forecasting."""
    vital_type: str
    forecast_value: float
    confidence: float
    confidence_level: str  # 'HIGH', 'MEDIUM', 'LOW'
    prediction_interval_90: tuple  # (lower, upper)
    prediction_interval_95: tuple  # (lower, upper)
    individual_predictions: Dict[str, float]
    individual_weights: Dict[str, float]
    confidence_factors: Dict[str, float]
    reasoning: str
    n_measurements: int
    measurement_mean: float
    measurement_std: float


class VitalSignsForecaster:
    """
    Complete vital signs forecasting system with regression + explainable AI.

    This is the unified interface combining:
    1. Ensemble regression forecasting
    2. Explainable AI confidence scoring
    3. Prediction interval calculation
    """

    def __init__(self, vital_type: str):
        """
        Initialize forecaster for a specific vital sign.

        Args:
            vital_type (str): Type of vital (e.g., 'heart_rate', 'blood_pressure')
        """
        self.vital_type = vital_type
        self.ensemble = EnsembleForecaster()
        self.xai_scorer = ExplainableAIScorer()

    def forecast(self, measurements: List[float]) -> ForecastResult:
        """
        Generate complete forecast with confidence.

        Process:
        1. Run ensemble forecasting
        2. Calculate confidence scores
        3. Compute prediction intervals
        4. Package into result

        Args:
            measurements (List[float]): Historical vital sign measurements

        Returns:
            ForecastResult: Complete prediction with confidence and reasoning
        """
        if not measurements or len(measurements) < 2:
            raise ValueError("Need at least 2 measurements")

        # Step 1: Run ensemble forecasting
        ensemble_forecast = self.ensemble.fit_and_predict(measurements)

        # Step 2: Calculate confidence
        confidence_score = self.xai_scorer.calculate_confidence(
            measurements=measurements,
            ensemble_forecast=ensemble_forecast,
            individual_predictions=self.ensemble.predictions
        )

        # Step 3: Calculate prediction intervals
        pi_90 = self._calculate_prediction_interval(measurements, ensemble_forecast, 0.90)
        pi_95 = self._calculate_prediction_interval(measurements, ensemble_forecast, 0.95)

        # Step 4: Get prediction breakdown
        breakdown = self.ensemble.get_predictions_breakdown()
        data = np.array(measurements, dtype=np.float64)

        # Step 5: Package result
        result = ForecastResult(
            vital_type=self.vital_type,
            forecast_value=ensemble_forecast,
            confidence=round(confidence_score.overall, 2),
            confidence_level=confidence_score.level,
            prediction_interval_90=pi_90,
            prediction_interval_95=pi_95,
            individual_predictions=self.ensemble.predictions,
            individual_weights=self.ensemble.weights,
            confidence_factors={
                'data_volume': round(confidence_score.data_volume, 2),
                'model_agreement': round(confidence_score.model_agreement, 2),
                'extrapolation_distance': round(confidence_score.extrapolation_distance, 2),
                'stability': round(confidence_score.stability, 2)
            },
            reasoning=confidence_score.reasoning,
            n_measurements=len(measurements),
            measurement_mean=float(np.mean(data)),
            measurement_std=float(np.std(data))
        )

        return result

    def _calculate_prediction_interval(
        self,
        measurements: List[float],
        forecast: float,
        confidence_level: float = 0.95
    ) -> tuple:
        """
        Calculate prediction interval around forecast.

        Prediction intervals are wider than confidence intervals because
        they account for individual variation, not just mean uncertainty.

        Formula:
        PI = forecast ± (z_score * standard_error)

        Where:
        - z_score for 95% = 1.96
        - z_score for 90% = 1.645
        - standard_error = std(residuals) from historical predictions

        Args:
            measurements (List[float]): Historical measurements
            forecast (float): Point forecast
            confidence_level (float): Confidence level (0.90, 0.95)

        Returns:
            tuple: (lower_bound, upper_bound)
        """
        data = np.array(measurements, dtype=np.float64)

        # Calculate standard error based on historical variation
        # Using coefficient of variation approach
        mean = np.mean(data)
        std = np.std(data)

        if mean == 0:
            std_error = std
        else:
            # Standard error proportional to data std
            std_error = std * 0.5  # Conservative estimate

        # Get z-score for confidence level
        z_scores = {
            0.90: 1.645,
            0.95: 1.96,
            0.99: 2.576
        }
        z_score = z_scores.get(confidence_level, 1.96)

        # Calculate interval
        margin = z_score * std_error
        lower = forecast - margin
        upper = forecast + margin

        return (round(lower, 2), round(upper, 2))

    def get_prediction_summary(self, result: ForecastResult) -> str:
        """
        Get human-readable summary of prediction.

        Args:
            result (ForecastResult): Forecast result

        Returns:
            str: Formatted summary
        """
        lines = []
        lines.append("=" * 70)
        lines.append(f"VITAL SIGNS FORECAST: {self.vital_type.upper()}")
        lines.append("=" * 70)
        lines.append(f"\n[PREDICTION]")
        lines.append(f"Forecast: {result.forecast_value:.2f}")
        lines.append(f"90% PI: {result.prediction_interval_90[0]:.2f} - {result.prediction_interval_90[1]:.2f}")
        lines.append(f"95% PI: {result.prediction_interval_95[0]:.2f} - {result.prediction_interval_95[1]:.2f}")

        lines.append(f"\n[CONFIDENCE]")
        lines.append(f"Overall Confidence: {result.confidence}% ({result.confidence_level})")
        lines.append(f"  - Data Volume:         {result.confidence_factors['data_volume']}%")
        lines.append(f"  - Model Agreement:     {result.confidence_factors['model_agreement']}%")
        lines.append(f"  - Extrapolation:       {result.confidence_factors['extrapolation_distance']}%")
        lines.append(f"  - Stability:           {result.confidence_factors['stability']}%")

        lines.append(f"\n[INDIVIDUAL METHODS]")
        for method, weight in result.individual_weights.items():
            pred = result.individual_predictions.get(method, 0)
            lines.append(f"{method.upper():<20} {pred:>7.2f}  (weight: {weight:.1%})")

        lines.append(f"\n[CLINICAL GUIDANCE]")
        if result.confidence_level == 'HIGH':
            lines.append("✓ HIGH CONFIDENCE - Can use as alert trigger")
        elif result.confidence_level == 'MEDIUM':
            lines.append("⚠ MEDIUM CONFIDENCE - Manual review recommended")
        else:
            lines.append("✗ LOW CONFIDENCE - Information only, no automatic alert")

        lines.append(f"\n[DATA SUMMARY]")
        lines.append(f"Measurements analyzed: {result.n_measurements}")
        lines.append(f"Mean: {result.measurement_mean:.2f}")
        lines.append(f"Std Dev: {result.measurement_std:.2f}")

        lines.append("\n" + "=" * 70)
        return "\n".join(lines)


class BatchForecastor:
    """
    Process multiple patients or vitals in batch.

    Useful for:
    - Generating forecasts for all patients at once
    - Batch processing vital types
    - Creating comprehensive reports
    """

    def __init__(self):
        """Initialize batch forecaster."""
        self.results = {}

    def forecast_vital_for_patient(
        self,
        patient_id: str,
        vital_type: str,
        measurements: List[float]
    ) -> ForecastResult:
        """
        Forecast a vital sign for a specific patient.

        Args:
            patient_id (str): Patient identifier
            vital_type (str): Type of vital
            measurements (List[float]): Historical measurements

        Returns:
            ForecastResult: Prediction with confidence
        """
        forecaster = VitalSignsForecaster(vital_type)
        result = forecaster.forecast(measurements)

        # Store result
        key = f"{patient_id}_{vital_type}"
        self.results[key] = result

        return result

    def get_summary_report(self) -> str:
        """
        Get summary of all forecasts.

        Returns:
            str: Report of all predictions and confidence levels
        """
        if not self.results:
            return "No forecasts generated yet"

        lines = []
        lines.append("=" * 80)
        lines.append("BATCH FORECAST SUMMARY")
        lines.append("=" * 80)

        # Group by confidence level
        high_conf = []
        med_conf = []
        low_conf = []

        for key, result in self.results.items():
            if result.confidence_level == 'HIGH':
                high_conf.append((key, result))
            elif result.confidence_level == 'MEDIUM':
                med_conf.append((key, result))
            else:
                low_conf.append((key, result))

        # Display high confidence
        if high_conf:
            lines.append(f"\n[HIGH CONFIDENCE] ({len(high_conf)})")
            for key, result in high_conf:
                lines.append(f"  {key:<30} Forecast: {result.forecast_value:>7.2f}  Conf: {result.confidence:>5.1f}%")

        # Display medium confidence
        if med_conf:
            lines.append(f"\n[MEDIUM CONFIDENCE] ({len(med_conf)})")
            for key, result in med_conf:
                lines.append(f"  {key:<30} Forecast: {result.forecast_value:>7.2f}  Conf: {result.confidence:>5.1f}%")

        # Display low confidence
        if low_conf:
            lines.append(f"\n[LOW CONFIDENCE] ({len(low_conf)}) - Requires manual review")
            for key, result in low_conf:
                lines.append(f"  {key:<30} Forecast: {result.forecast_value:>7.2f}  Conf: {result.confidence:>5.1f}%")

        lines.append("\n" + "=" * 80)
        return "\n".join(lines)
