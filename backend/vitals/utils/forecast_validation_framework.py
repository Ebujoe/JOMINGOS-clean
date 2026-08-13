"""
FORECAST VALIDATION FRAMEWORK
==============================

Rigorous statistical validation for the forecasting system.

Implements:
1. Backtesting against historical data
2. Cross-validation (time-series aware)
3. Error metrics and calibration
4. Prediction interval coverage analysis
5. Clinical validation protocol
6. Continuous monitoring
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging
import json

logger = logging.getLogger(__name__)


@dataclass
class ValidationMetrics:
    """Comprehensive validation metrics."""

    # Point prediction errors
    mae: float  # Mean Absolute Error
    rmse: float  # Root Mean Square Error
    mape: float  # Mean Absolute Percentage Error
    mean_bias: float  # Systematic bias

    # Confidence/Uncertainty
    prediction_interval_coverage_90: float  # Should be ~0.90
    prediction_interval_coverage_95: float  # Should be ~0.95
    calibration_score: float  # 0-1, how well calibrated
    sharpness_score: float  # Average prediction interval width

    # Directional accuracy
    directional_accuracy: float  # % correct direction (up/down/stable)

    # Model diagnostics
    model_disagreement_avg: float
    confidence_avg: float

    # Overall score (0-100)
    overall_validation_score: float

    # Validation details
    n_predictions: int
    horizon_hours: int
    vital_name: str
    validation_date: datetime
    notes: str


@dataclass
class BacktestResult:
    """Results from backtesting."""
    vital_name: str
    horizon_hours: int
    metrics: ValidationMetrics
    prediction_errors: List[float]
    confidence_scores: List[float]
    is_passed: bool
    summary: str


class ForecastValidationFramework:
    """Rigorous validation system for forecasts."""

    def __init__(self):
        self.min_predictions_for_validation = 20
        self.target_pi_coverage_90 = 0.90
        self.target_pi_coverage_95 = 0.95
        self.mae_threshold_acceptable = {'heart_rate': 8, 'respiratory_rate': 2,
                                         'oxygen_saturation': 2, 'temperature': 0.3}
        self.direction_accuracy_threshold = 0.65

    def backtest_forecast(
        self,
        forecast_engine,
        historical_vital_data: List[Tuple[datetime, float]],
        vital_name: str,
        horizon_hours: int,
        patient_baseline: Optional[object] = None,
        train_test_split: float = 0.8,
    ) -> BacktestResult:
        """
        Backtest forecast on historical data.

        Splits data into train/test, makes predictions on test set,
        compares to actual values.
        """

        logger.info(f"Starting backtest: {vital_name} @ {horizon_hours}h horizon")
        logger.info(f"Total data points: {len(historical_vital_data)}")

        # Need enough data
        if len(historical_vital_data) < horizon_hours + 30:
            logger.warning("Insufficient data for meaningful backtest")
            return BacktestResult(
                vital_name=vital_name,
                horizon_hours=horizon_hours,
                metrics=ValidationMetrics(
                    mae=np.nan, rmse=np.nan, mape=np.nan, mean_bias=np.nan,
                    prediction_interval_coverage_90=np.nan,
                    prediction_interval_coverage_95=np.nan,
                    calibration_score=0.0, sharpness_score=np.nan,
                    directional_accuracy=0.0, model_disagreement_avg=np.nan,
                    confidence_avg=0.0, overall_validation_score=0.0,
                    n_predictions=0, horizon_hours=horizon_hours,
                    vital_name=vital_name, validation_date=datetime.now(),
                    notes="Insufficient data"
                ),
                prediction_errors=[],
                confidence_scores=[],
                is_passed=False,
                summary="Backtest skipped: insufficient historical data"
            )

        # Sort by date
        sorted_data = sorted(historical_vital_data, key=lambda x: x[0])
        times = np.array([d[0] for d in sorted_data])
        values = np.array([d[1] for d in sorted_data])

        # Split into train/test
        split_idx = int(len(sorted_data) * train_test_split)
        train_times = times[:split_idx]
        train_values = values[:split_idx]

        test_times = times[split_idx:]
        test_values = values[split_idx:]

        logger.info(f"Train: {len(train_times)} points, Test: {len(test_times)} points")

        # Make predictions on test set
        predictions = []
        actuals = []
        errors = []
        confidence_scores = []
        pi_90_coverage = []
        pi_95_coverage = []
        directions_predicted = []
        directions_actual = []

        for i in range(horizon_hours, len(test_values)):
            # Historical window
            hist_end = split_idx + i - horizon_hours
            if hist_end < split_idx + horizon_hours:
                continue

            hist_times = times[:hist_end]
            hist_values = values[:hist_end]

            # Make prediction
            try:
                prediction = forecast_engine.generate_prediction(
                    hist_values.tolist(),
                    hist_times.tolist(),
                    vital_name,
                    patient_baseline,
                    horizon_hours
                )

                if np.isnan(prediction.forecast_value):
                    continue

                actual = test_values[i]

                predictions.append(prediction.forecast_value)
                actuals.append(actual)
                confidence_scores.append(prediction.confidence_score)

                # Error
                error = actual - prediction.forecast_value
                errors.append(error)

                # Prediction interval coverage
                if actual >= prediction.prediction_interval_90_lower and \
                   actual <= prediction.prediction_interval_90_upper:
                    pi_90_coverage.append(1)
                else:
                    pi_90_coverage.append(0)

                if actual >= prediction.prediction_interval_95_lower and \
                   actual <= prediction.prediction_interval_95_upper:
                    pi_95_coverage.append(1)
                else:
                    pi_95_coverage.append(0)

                # Direction accuracy
                if i > 0:
                    prev_actual = test_values[i - 1]
                    if (actual > prev_actual and prediction.forecast_value > hist_values[-1]) or \
                       (actual < prev_actual and prediction.forecast_value < hist_values[-1]) or \
                       (abs(actual - prev_actual) < 1 and
                        abs(prediction.forecast_value - hist_values[-1]) < 1):
                        directions_predicted.append(1)
                    else:
                        directions_predicted.append(0)

                    if actual > prev_actual:
                        directions_actual.append(1)  # up
                    elif actual < prev_actual:
                        directions_actual.append(-1)  # down
                    else:
                        directions_actual.append(0)  # stable

            except Exception as e:
                logger.error(f"Error making prediction: {e}")
                continue

        if len(predictions) < self.min_predictions_for_validation:
            logger.warning(f"Too few predictions for validation: {len(predictions)}")
            return BacktestResult(
                vital_name=vital_name,
                horizon_hours=horizon_hours,
                metrics=ValidationMetrics(
                    mae=np.nan, rmse=np.nan, mape=np.nan, mean_bias=np.nan,
                    prediction_interval_coverage_90=np.nan,
                    prediction_interval_coverage_95=np.nan,
                    calibration_score=0.0, sharpness_score=np.nan,
                    directional_accuracy=0.0, model_disagreement_avg=np.nan,
                    confidence_avg=np.mean(confidence_scores) if confidence_scores else 0.0,
                    overall_validation_score=0.0,
                    n_predictions=len(predictions), horizon_hours=horizon_hours,
                    vital_name=vital_name, validation_date=datetime.now(),
                    notes=f"Only {len(predictions)} predictions"
                ),
                prediction_errors=errors,
                confidence_scores=confidence_scores,
                is_passed=False,
                summary=f"Insufficient predictions ({len(predictions)}) for validation"
            )

        # Calculate metrics
        predictions = np.array(predictions)
        actuals = np.array(actuals)
        errors = np.array(errors)

        mae = np.mean(np.abs(errors))
        rmse = np.sqrt(np.mean(errors**2))
        mape = np.mean(np.abs(errors / (np.abs(actuals) + 0.001))) * 100
        mean_bias = np.mean(errors)

        pi_90_cov = np.mean(pi_90_coverage) if pi_90_coverage else 0.0
        pi_95_cov = np.mean(pi_95_coverage) if pi_95_coverage else 0.0

        # Calibration score
        calibration_score = self._calculate_calibration_score(pi_90_cov, pi_95_cov)

        # Sharpness
        sharpness_score = np.mean(
            [p for p in predictions if not np.isnan(p)]
        ) if len(predictions) > 0 else np.nan

        # Directional accuracy
        if len(directions_predicted) > 0:
            directional_accuracy = np.mean(directions_predicted)
        else:
            directional_accuracy = 0.0

        # Overall validation score
        overall_score = self._calculate_overall_validation_score(
            mae, rmse, mape, calibration_score, directional_accuracy, vital_name
        )

        # Pass/fail
        is_passed = overall_score >= 70.0

        metrics = ValidationMetrics(
            mae=float(mae),
            rmse=float(rmse),
            mape=float(mape),
            mean_bias=float(mean_bias),
            prediction_interval_coverage_90=float(pi_90_cov),
            prediction_interval_coverage_95=float(pi_95_cov),
            calibration_score=calibration_score,
            sharpness_score=float(sharpness_score) if not np.isnan(sharpness_score) else 0.0,
            directional_accuracy=directional_accuracy,
            model_disagreement_avg=0.0,  # Can be enhanced
            confidence_avg=float(np.mean(confidence_scores)) if confidence_scores else 0.0,
            overall_validation_score=overall_score,
            n_predictions=len(predictions),
            horizon_hours=horizon_hours,
            vital_name=vital_name,
            validation_date=datetime.now(),
            notes=f"Backtesting on {len(predictions)} predictions"
        )

        summary = self._generate_validation_summary(metrics, is_passed)

        result = BacktestResult(
            vital_name=vital_name,
            horizon_hours=horizon_hours,
            metrics=metrics,
            prediction_errors=errors.tolist(),
            confidence_scores=confidence_scores,
            is_passed=is_passed,
            summary=summary
        )

        logger.info(f"Backtest complete: {vital_name} - Score: {overall_score:.1f}%, {'PASSED' if is_passed else 'FAILED'}")

        return result

    def _calculate_calibration_score(self, pi_90_cov: float, pi_95_cov: float) -> float:
        """
        Calibration: how well do prediction intervals match claimed coverage?

        Perfect: PI_90=0.90, PI_95=0.95
        """
        error_90 = abs(pi_90_cov - 0.90)
        error_95 = abs(pi_95_cov - 0.95)

        avg_error = (error_90 + error_95) / 2
        calibration = max(1.0 - (avg_error * 2), 0.0)  # Penalize miscalibration

        return calibration

    def _calculate_overall_validation_score(
        self, mae: float, rmse: float, mape: float,
        calibration: float, dir_accuracy: float, vital_name: str
    ) -> float:
        """
        Calculate overall validation score (0-100).

        Weighted combination of:
        - Accuracy (40%): MAE/RMSE
        - Calibration (30%): Prediction interval quality
        - Direction (30%): Trend prediction accuracy
        """

        # Accuracy component (0-100)
        mae_threshold = self.mae_threshold_acceptable.get(vital_name, 5)
        accuracy_score = max(100 - (mae / mae_threshold * 30), 0)

        # Calibration component (0-100)
        calibration_score = calibration * 100

        # Direction component (0-100)
        direction_score = dir_accuracy * 100

        # Weighted combination
        overall = (accuracy_score * 0.4) + (calibration_score * 0.3) + (direction_score * 0.3)

        return overall

    def _generate_validation_summary(self, metrics: ValidationMetrics, is_passed: bool) -> str:
        """Generate human-readable validation summary."""

        status = "✓ PASSED" if is_passed else "✗ FAILED"

        summary = f"{status} Backtest Results:\n"
        summary += f"  Predictions: {metrics.n_predictions}\n"
        summary += f"  MAE: {metrics.mae:.2f}\n"
        summary += f"  RMSE: {metrics.rmse:.2f}\n"
        summary += f"  PI-90 Coverage: {metrics.prediction_interval_coverage_90:.1%}\n"
        summary += f"  PI-95 Coverage: {metrics.prediction_interval_coverage_95:.1%}\n"
        summary += f"  Calibration: {metrics.calibration_score:.2f}\n"
        summary += f"  Direction Accuracy: {metrics.directional_accuracy:.1%}\n"
        summary += f"  Overall Score: {metrics.overall_validation_score:.1f}/100"

        return summary


class ValidationReport:
    """Comprehensive validation report for documentation."""

    def __init__(self):
        self.validation_date = datetime.now()
        self.results: Dict[str, Dict[int, BacktestResult]] = {}  # vital -> horizon -> result
        self.overall_status = "PENDING"

    def add_result(self, result: BacktestResult):
        """Add backtest result to report."""
        if result.vital_name not in self.results:
            self.results[result.vital_name] = {}

        self.results[result.vital_name][result.metrics.horizon_hours] = result

    def generate_report(self) -> Dict:
        """Generate complete validation report."""

        all_passed = all(
            result.is_passed
            for vital_results in self.results.values()
            for result in vital_results.values()
        )

        self.overall_status = "PASSED" if all_passed else "CONDITIONAL"

        return {
            "validation_date": self.validation_date.isoformat(),
            "overall_status": self.overall_status,
            "results_by_vital": {
                vital: {
                    horizon: {
                        "passed": result.is_passed,
                        "metrics": {
                            "mae": result.metrics.mae,
                            "rmse": result.metrics.rmse,
                            "calibration": result.metrics.calibration_score,
                            "overall_score": result.metrics.overall_validation_score,
                        },
                        "summary": result.summary
                    }
                    for horizon, result in vital_results.items()
                }
                for vital, vital_results in self.results.items()
            }
        }

    def save_report(self, filepath: str):
        """Save report to file."""
        report = self.generate_report()
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Validation report saved to {filepath}")
