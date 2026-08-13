"""
COMPREHENSIVE FORECAST VALIDATION FRAMEWORK - WEEK 4
=====================================================

Extends Week 3 backtesting with:
1. Time-series cross-validation
2. Calibration curve analysis
3. Performance tracking by horizon
4. Confidence optimization
5. Comprehensive validation reporting

Prepares for clinical validation (Week 7) and production (Week 8).
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging
import json

logger = logging.getLogger(__name__)


@dataclass
class CalibrationMetrics:
    """Calibration analysis results."""
    pi_90_coverage: float  # % of actuals within 90% PI
    pi_95_coverage: float  # % of actuals within 95% PI
    pi_90_excess_width: float  # How wide are 90% PIs?
    pi_95_excess_width: float  # How wide are 95% PIs?
    calibration_score: float  # 0-100 score (100 = perfect)
    is_well_calibrated: bool  # Pass/fail


@dataclass
class ValidationMetrics:
    """Complete validation results for a forecast horizon."""
    horizon_hours: int
    vital_name: str
    n_forecasts: int
    n_accurate: int  # Within 95% PI

    # Error metrics
    mae: float  # Mean absolute error
    rmse: float  # Root mean square error
    mape: float  # Mean absolute percentage error
    mean_bias: float  # Systematic bias

    # Directional accuracy
    directional_accuracy: float  # % correct trend predictions

    # Calibration
    calibration: CalibrationMetrics

    # Overall score
    overall_validation_score: float  # 0-100

    # Assessment
    recommendation: str
    pass_fail: bool


class TimeSeriesCrossValidator:
    """
    Time-series aware cross-validation.

    Unlike standard k-fold, preserves temporal order:
    - Never trains on future data
    - Tests on each forward-looking window
    - Respects the sequential nature of vital signs
    """

    def __init__(self, min_train_size: int = 20, window_size: int = 10):
        """
        Initialize cross-validator.

        Args:
            min_train_size: Minimum training samples required
            window_size: Size of each validation window
        """
        self.min_train_size = min_train_size
        self.window_size = window_size
        logger.info("TimeSeriesCrossValidator initialized")

    def generate_splits(
        self,
        data_length: int,
    ) -> List[Tuple[List[int], List[int]]]:
        """
        Generate train/test splits preserving temporal order.

        Args:
            data_length: Total number of data points

        Returns:
            List of (train_indices, test_indices) tuples
        """

        if data_length < self.min_train_size + self.window_size:
            logger.warning(f"Insufficient data for CV: {data_length}")
            return []

        splits = []

        # Progressive expanding window
        for test_start in range(
            self.min_train_size,
            data_length - self.window_size,
            max(1, self.window_size // 2),  # 50% overlap
        ):
            train_indices = list(range(test_start))
            test_indices = list(range(test_start, test_start + self.window_size))

            if len(test_indices) > 0:
                splits.append((train_indices, test_indices))

        logger.info(f"Generated {len(splits)} CV splits")
        return splits

    @staticmethod
    def calculate_cv_score(
        splits: List[Tuple[List[int], List[int]]],
        forecasts: List[float],
        actuals: List[float],
    ) -> Dict:
        """
        Calculate cross-validation score across splits.

        Args:
            splits: List of (train, test) index pairs
            forecasts: Forecasted values
            actuals: Actual values

        Returns:
            Cross-validation metrics
        """

        if not splits:
            return {'error': 'No valid splits'}

        errors = []
        accuracies = []

        for train_idx, test_idx in splits:
            # Get test set predictions and actuals
            test_forecasts = [forecasts[i] for i in test_idx if i < len(forecasts)]
            test_actuals = [actuals[i] for i in test_idx if i < len(actuals)]

            if not test_forecasts or not test_actuals:
                continue

            # Calculate error
            test_errors = [
                abs(f - a) for f, a in zip(test_forecasts, test_actuals)
            ]
            mae = np.mean(test_errors)
            errors.append(mae)

            # Accuracy (within reasonable range)
            within_range = sum(
                1 for e in test_errors if e < np.std(test_actuals) * 2
            )
            accuracy = within_range / len(test_errors)
            accuracies.append(accuracy)

        return {
            'mean_cv_mae': float(np.mean(errors)) if errors else 0,
            'std_cv_mae': float(np.std(errors)) if errors else 0,
            'mean_accuracy': float(np.mean(accuracies)) if accuracies else 0,
            'n_splits': len(splits),
        }


class CalibrationAnalyzer:
    """
    Analyze prediction interval calibration.

    A forecast is well-calibrated if:
    - 90% PI contains ~90% of actual values
    - 95% PI contains ~95% of actual values
    """

    @staticmethod
    def analyze_calibration(
        forecasts: List[float],
        pi_90_lower: List[float],
        pi_90_upper: List[float],
        pi_95_lower: List[float],
        pi_95_upper: List[float],
        actuals: List[float],
    ) -> CalibrationMetrics:
        """
        Analyze prediction interval calibration.

        Args:
            forecasts: Point estimates
            pi_90_lower/upper: 90% prediction intervals
            pi_95_lower/upper: 95% prediction intervals
            actuals: Actual measured values

        Returns:
            CalibrationMetrics object
        """

        if len(actuals) < 10:
            return CalibrationMetrics(
                pi_90_coverage=0,
                pi_95_coverage=0,
                pi_90_excess_width=0,
                pi_95_excess_width=0,
                calibration_score=0,
                is_well_calibrated=False,
            )

        # Calculate coverage
        pi_90_in = sum(
            1 for i, actual in enumerate(actuals)
            if pi_90_lower[i] <= actual <= pi_90_upper[i]
        )
        pi_95_in = sum(
            1 for i, actual in enumerate(actuals)
            if pi_95_lower[i] <= actual <= pi_95_upper[i]
        )

        coverage_90 = pi_90_in / len(actuals)
        coverage_95 = pi_95_in / len(actuals)

        # Calculate widths
        widths_90 = [pi_90_upper[i] - pi_90_lower[i] for i in range(len(actuals))]
        widths_95 = [pi_95_upper[i] - pi_95_lower[i] for i in range(len(actuals))]

        width_90 = np.mean(widths_90)
        width_95 = np.mean(widths_95)

        # Calibration score
        # Target: 90% PI covers ~90%, 95% PI covers ~95%
        error_90 = abs(coverage_90 - 0.90)
        error_95 = abs(coverage_95 - 0.95)
        calibration_error = (error_90 + error_95) / 2

        # Score: 100 = perfect, 0 = terrible
        calibration_score = max(0, 100 * (1 - calibration_error))

        is_well_calibrated = (
            0.85 <= coverage_90 <= 0.95 and
            0.90 <= coverage_95 <= 1.0
        )

        return CalibrationMetrics(
            pi_90_coverage=float(coverage_90),
            pi_95_coverage=float(coverage_95),
            pi_90_excess_width=float(width_90),
            pi_95_excess_width=float(width_95),
            calibration_score=float(calibration_score),
            is_well_calibrated=is_well_calibrated,
        )


class ComprehensiveValidator:
    """
    Complete validation framework combining all metrics.
    """

    @staticmethod
    def validate_horizon(
        patient_id: int,
        vital_name: str,
        horizon_hours: int,
        forecasts: List[Dict],
        actuals: List[float],
        timestamps: List[datetime],
    ) -> ValidationMetrics:
        """
        Comprehensive validation for a single horizon.

        Args:
            patient_id: Patient ID
            vital_name: Vital type
            horizon_hours: Forecast horizon
            forecasts: List of forecast dicts
            actuals: Actual measured values
            timestamps: Measurement timestamps

        Returns:
            ValidationMetrics object
        """

        if len(forecasts) < 5:
            logger.warning(f"Insufficient forecasts for validation: {len(forecasts)}")
            return None

        # Extract values
        forecast_values = [f.get('forecast_value', 0) for f in forecasts]
        pi_90_lowers = [f.get('prediction_interval_90_lower', 0) for f in forecasts]
        pi_90_uppers = [f.get('prediction_interval_90_upper', 0) for f in forecasts]
        pi_95_lowers = [f.get('prediction_interval_95_lower', 0) for f in forecasts]
        pi_95_uppers = [f.get('prediction_interval_95_upper', 0) for f in forecasts]
        confidence_scores = [f.get('confidence_score', 0) for f in forecasts]

        # Error metrics
        errors = np.array([
            abs(forecast_values[i] - actuals[i])
            for i in range(min(len(forecast_values), len(actuals)))
        ])

        mae = float(np.mean(errors)) if len(errors) > 0 else 0
        rmse = float(np.sqrt(np.mean(errors ** 2))) if len(errors) > 0 else 0

        # MAPE (avoid division by zero)
        mape_values = [
            abs((forecast_values[i] - actuals[i]) / actuals[i] * 100)
            for i in range(min(len(forecast_values), len(actuals)))
            if actuals[i] != 0
        ]
        mape = float(np.mean(mape_values)) if mape_values else 0

        # Bias
        bias_values = [
            forecast_values[i] - actuals[i]
            for i in range(min(len(forecast_values), len(actuals)))
        ]
        mean_bias = float(np.mean(bias_values)) if bias_values else 0

        # Directional accuracy
        if len(forecast_values) > 1 and len(actuals) > 1:
            forecast_diffs = np.diff(forecast_values)
            actual_diffs = np.diff(actuals)
            directions_correct = sum(
                1 for i in range(len(forecast_diffs))
                if (forecast_diffs[i] > 0) == (actual_diffs[i] > 0)
            )
            directional_accuracy = directions_correct / len(forecast_diffs)
        else:
            directional_accuracy = 0.5

        # Accuracy within PI
        n_accurate = sum(
            1 for i in range(min(len(forecast_values), len(actuals)))
            if pi_95_lowers[i] <= actuals[i] <= pi_95_uppers[i]
        )
        accuracy_rate = n_accurate / min(len(forecast_values), len(actuals))

        # Calibration
        calibration = CalibrationAnalyzer.analyze_calibration(
            forecast_values,
            pi_90_lowers,
            pi_90_uppers,
            pi_95_lowers,
            pi_95_uppers,
            actuals,
        )

        # Overall validation score (0-100)
        score_components = {
            'accuracy': accuracy_rate * 40,  # 40 points
            'calibration': (calibration.calibration_score / 100) * 30,  # 30 points
            'directional': directional_accuracy * 20,  # 20 points
            'mae_penalty': max(0, 10 - mae) if mae < 10 else 0,  # 10 points
        }
        overall_score = sum(score_components.values())

        # Recommendation
        if overall_score >= 80:
            recommendation = "EXCELLENT - Ready for clinical use"
            pass_fail = True
        elif overall_score >= 60:
            recommendation = "GOOD - Monitor performance closely"
            pass_fail = True
        elif overall_score >= 40:
            recommendation = "FAIR - Acceptable but with reservations"
            pass_fail = True
        else:
            recommendation = "POOR - Requires improvement before clinical use"
            pass_fail = False

        metrics = ValidationMetrics(
            horizon_hours=horizon_hours,
            vital_name=vital_name,
            n_forecasts=len(forecasts),
            n_accurate=n_accurate,
            mae=mae,
            rmse=rmse,
            mape=mape,
            mean_bias=mean_bias,
            directional_accuracy=float(directional_accuracy),
            calibration=calibration,
            overall_validation_score=float(overall_score),
            recommendation=recommendation,
            pass_fail=pass_fail,
        )

        logger.info(
            f"Validation complete: {vital_name} @ {horizon_hours}h "
            f"score={overall_score:.0f}, MAE={mae:.2f}"
        )

        return metrics

    @staticmethod
    def validate_all_horizons(
        patient_id: int,
        vital_name: str,
    ) -> Dict[int, ValidationMetrics]:
        """Validate all standard horizons."""

        from vitals.models import PatientForecast
        from vitals.utils.forecasting_service import ForecastingService

        service = ForecastingService()
        horizons = [24, 168, 336, 720]  # 24h, 7d, 14d, 30d
        results = {}

        for horizon in horizons:
            # Get forecasts from database
            forecasts_qs = PatientForecast.objects.filter(
                patient_id=patient_id,
                vital_name=vital_name,
                horizon_hours=horizon,
            ).values()

            if not forecasts_qs.exists():
                logger.warning(f"No forecasts for {vital_name} @ {horizon}h")
                continue

            # Extract data
            forecasts = list(forecasts_qs)
            actuals = [
                f['actual_value'] for f in forecasts if f['actual_value'] is not None
            ]
            timestamps = [f['forecast_timestamp'] for f in forecasts]

            if len(actuals) < 5:
                logger.warning(f"Insufficient actuals for validation: {len(actuals)}")
                continue

            # Validate
            metrics = ComprehensiveValidator.validate_horizon(
                patient_id=patient_id,
                vital_name=vital_name,
                horizon_hours=horizon,
                forecasts=forecasts,
                actuals=actuals,
                timestamps=timestamps,
            )

            if metrics:
                results[horizon] = metrics

        return results


def validation_to_dict(metrics: ValidationMetrics) -> Dict:
    """Convert ValidationMetrics to dict."""

    if not metrics:
        return {}

    return {
        'horizon_hours': metrics.horizon_hours,
        'vital_name': metrics.vital_name,
        'n_forecasts': metrics.n_forecasts,
        'n_accurate': metrics.n_accurate,
        'accuracy_rate': metrics.n_accurate / metrics.n_forecasts if metrics.n_forecasts > 0 else 0,
        'mae': metrics.mae,
        'rmse': metrics.rmse,
        'mape': metrics.mape,
        'mean_bias': metrics.mean_bias,
        'directional_accuracy': metrics.directional_accuracy,
        'calibration': {
            'pi_90_coverage': metrics.calibration.pi_90_coverage,
            'pi_95_coverage': metrics.calibration.pi_95_coverage,
            'pi_90_width': metrics.calibration.pi_90_excess_width,
            'pi_95_width': metrics.calibration.pi_95_excess_width,
            'calibration_score': metrics.calibration.calibration_score,
            'is_well_calibrated': metrics.calibration.is_well_calibrated,
        },
        'overall_validation_score': metrics.overall_validation_score,
        'recommendation': metrics.recommendation,
        'pass_fail': metrics.pass_fail,
    }
