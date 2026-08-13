"""
CALIBRATION CURVE ANALYSIS - WEEK 5
===================================

Generates calibration curves for visualization and assessment.

Provides:
1. Confidence calibration curves
2. Prediction interval coverage curves
3. Error by confidence bins
4. Horizon-specific calibration
5. Vital-specific calibration
6. Calibration plots data for visualization
"""

from typing import Dict, List, Tuple
import numpy as np
import logging

logger = logging.getLogger(__name__)


class CalibrationCurveGenerator:
    """Generate calibration curves from forecast history."""

    @staticmethod
    def generate_confidence_calibration_curve(
        forecasts: List[Dict],
        n_bins: int = 10,
    ) -> Dict:
        """
        Generate confidence calibration curve.

        Shows: Does 70% confidence really mean 70% accuracy?

        Args:
            forecasts: List of forecast records with actual values
            n_bins: Number of confidence bins

        Returns:
            Calibration curve data
        """

        if not forecasts:
            return {}

        # Filter forecasts with actual values
        valid_forecasts = [
            f for f in forecasts if f.get('actual_value') is not None
        ]

        if len(valid_forecasts) < 10:
            logger.warning(f"Insufficient forecasts: {len(valid_forecasts)}")
            return {}

        # Create confidence bins
        confidence_scores = [f.get('confidence_score', 0) for f in valid_forecasts]
        min_conf = min(confidence_scores)
        max_conf = max(confidence_scores)

        bins = np.linspace(min_conf, max_conf, n_bins)
        calibration_data = []

        for i in range(len(bins) - 1):
            bin_lower = bins[i]
            bin_upper = bins[i + 1]
            bin_mid = (bin_lower + bin_upper) / 2

            # Get forecasts in this bin
            bin_forecasts = [
                f for f in valid_forecasts
                if bin_lower <= f.get('confidence_score', 0) < bin_upper
            ]

            if not bin_forecasts:
                continue

            # Calculate accuracy for this bin
            accurate = sum(
                1 for f in bin_forecasts
                if (f.get('prediction_interval_95_lower', 0) <=
                    f.get('actual_value') <=
                    f.get('prediction_interval_95_upper', 0))
            )

            accuracy = accurate / len(bin_forecasts)

            calibration_data.append({
                'confidence': float(bin_mid),
                'actual_accuracy': float(accuracy),
                'n_forecasts': len(bin_forecasts),
                'bin_lower': float(bin_lower),
                'bin_upper': float(bin_upper),
            })

        return {
            'curve_data': calibration_data,
            'perfect_calibration': [
                {'confidence': 0, 'accuracy': 0},
                {'confidence': 100, 'accuracy': 100},
            ],
        }

    @staticmethod
    def generate_pi_coverage_curve(
        forecasts: List[Dict],
        n_bins: int = 10,
    ) -> Dict:
        """
        Generate prediction interval coverage curve.

        Shows: Do 90% PIs cover 90% of values?

        Args:
            forecasts: List of forecasts with actual values
            n_bins: Number of confidence bins

        Returns:
            PI coverage curve data
        """

        if not forecasts:
            return {}

        valid_forecasts = [
            f for f in forecasts if f.get('actual_value') is not None
        ]

        if len(valid_forecasts) < 10:
            return {}

        confidence_scores = [f.get('confidence_score', 0) for f in valid_forecasts]
        min_conf = min(confidence_scores)
        max_conf = max(confidence_scores)

        bins = np.linspace(min_conf, max_conf, n_bins)
        coverage_data = {
            'pi_90': [],
            'pi_95': [],
        }

        for i in range(len(bins) - 1):
            bin_lower = bins[i]
            bin_upper = bins[i + 1]
            bin_mid = (bin_lower + bin_upper) / 2

            bin_forecasts = [
                f for f in valid_forecasts
                if bin_lower <= f.get('confidence_score', 0) < bin_upper
            ]

            if not bin_forecasts:
                continue

            # 90% PI coverage
            covered_90 = sum(
                1 for f in bin_forecasts
                if (f.get('prediction_interval_90_lower', 0) <=
                    f.get('actual_value') <=
                    f.get('prediction_interval_90_upper', 0))
            )
            coverage_90 = covered_90 / len(bin_forecasts)

            # 95% PI coverage
            covered_95 = sum(
                1 for f in bin_forecasts
                if (f.get('prediction_interval_95_lower', 0) <=
                    f.get('actual_value') <=
                    f.get('prediction_interval_95_upper', 0))
            )
            coverage_95 = covered_95 / len(bin_forecasts)

            coverage_data['pi_90'].append({
                'confidence': float(bin_mid),
                'coverage': float(coverage_90),
                'target': 0.90,
                'n_forecasts': len(bin_forecasts),
            })

            coverage_data['pi_95'].append({
                'confidence': float(bin_mid),
                'coverage': float(coverage_95),
                'target': 0.95,
                'n_forecasts': len(bin_forecasts),
            })

        return coverage_data

    @staticmethod
    def generate_error_by_confidence_curve(
        forecasts: List[Dict],
        n_bins: int = 10,
    ) -> Dict:
        """
        Generate error metric curves by confidence level.

        Shows: How does accuracy degrade with confidence?

        Args:
            forecasts: List of forecasts
            n_bins: Number of bins

        Returns:
            Error curve data
        """

        if not forecasts:
            return {}

        valid_forecasts = [
            f for f in forecasts if f.get('actual_value') is not None
        ]

        if len(valid_forecasts) < 10:
            return {}

        confidence_scores = [f.get('confidence_score', 0) for f in valid_forecasts]
        min_conf = min(confidence_scores)
        max_conf = max(confidence_scores)

        bins = np.linspace(min_conf, max_conf, n_bins)
        error_data = []

        for i in range(len(bins) - 1):
            bin_lower = bins[i]
            bin_upper = bins[i + 1]
            bin_mid = (bin_lower + bin_upper) / 2

            bin_forecasts = [
                f for f in valid_forecasts
                if bin_lower <= f.get('confidence_score', 0) < bin_upper
            ]

            if not bin_forecasts:
                continue

            # Calculate error metrics
            errors = [
                abs(f.get('forecast_value', 0) - f.get('actual_value'))
                for f in bin_forecasts
            ]

            mae = np.mean(errors)
            rmse = np.sqrt(np.mean(np.array(errors) ** 2))

            error_data.append({
                'confidence': float(bin_mid),
                'mae': float(mae),
                'rmse': float(rmse),
                'n_forecasts': len(bin_forecasts),
            })

        return {'error_data': error_data}


class HorizonCalibrationAnalyzer:
    """Analyze calibration by forecast horizon."""

    @staticmethod
    def analyze_by_horizon(
        forecasts: List[Dict],
    ) -> Dict[int, Dict]:
        """
        Analyze calibration for each horizon separately.

        Args:
            forecasts: List of forecasts

        Returns:
            Dict of horizon -> calibration metrics
        """

        # Group by horizon
        by_horizon = {}

        for forecast in forecasts:
            horizon = forecast.get('horizon_hours', 24)
            if horizon not in by_horizon:
                by_horizon[horizon] = []
            by_horizon[horizon].append(forecast)

        # Analyze each horizon
        results = {}

        for horizon, horizon_forecasts in by_horizon.items():
            valid = [
                f for f in horizon_forecasts if f.get('actual_value') is not None
            ]

            if len(valid) < 5:
                continue

            # Calculate metrics
            errors = [
                abs(f.get('forecast_value', 0) - f.get('actual_value'))
                for f in valid
            ]

            mae = np.mean(errors)
            rmse = np.sqrt(np.mean(np.array(errors) ** 2))

            # PI coverage
            pi_95_coverage = sum(
                1 for f in valid
                if (f.get('prediction_interval_95_lower', 0) <=
                    f.get('actual_value') <=
                    f.get('prediction_interval_95_upper', 0))
            ) / len(valid)

            results[horizon] = {
                'horizon_hours': horizon,
                'n_forecasts': len(valid),
                'mae': float(mae),
                'rmse': float(rmse),
                'pi_95_coverage': float(pi_95_coverage),
                'well_calibrated': 0.90 <= pi_95_coverage <= 1.0,
                'avg_confidence': float(
                    np.mean([f.get('confidence_score', 0) for f in valid])
                ),
            }

        return results


class VitalCalibrationAnalyzer:
    """Analyze calibration by vital type."""

    @staticmethod
    def analyze_by_vital(
        forecasts: List[Dict],
    ) -> Dict[str, Dict]:
        """
        Analyze calibration for each vital type.

        Args:
            forecasts: List of forecasts

        Returns:
            Dict of vital_name -> calibration metrics
        """

        # Group by vital
        by_vital = {}

        for forecast in forecasts:
            vital = forecast.get('vital_name', 'unknown')
            if vital not in by_vital:
                by_vital[vital] = []
            by_vital[vital].append(forecast)

        # Analyze each vital
        results = {}

        for vital, vital_forecasts in by_vital.items():
            valid = [
                f for f in vital_forecasts if f.get('actual_value') is not None
            ]

            if len(valid) < 5:
                continue

            errors = [
                abs(f.get('forecast_value', 0) - f.get('actual_value'))
                for f in valid
            ]

            mae = np.mean(errors)
            accuracy = sum(
                1 for f in valid
                if (f.get('prediction_interval_95_lower', 0) <=
                    f.get('actual_value') <=
                    f.get('prediction_interval_95_upper', 0))
            ) / len(valid)

            results[vital] = {
                'vital_name': vital,
                'n_forecasts': len(valid),
                'mae': float(mae),
                'accuracy': float(accuracy),
                'avg_confidence': float(
                    np.mean([f.get('confidence_score', 0) for f in valid])
                ),
            }

        return results


class CalibrationSummary:
    """Generate calibration summary for clinical review."""

    @staticmethod
    def generate_clinical_summary(
        validation_results: Dict,
        by_horizon: Dict,
        by_vital: Dict,
    ) -> Dict:
        """
        Generate summary for clinical deployment decision.

        Args:
            validation_results: Overall validation metrics
            by_horizon: Calibration by horizon
            by_vital: Calibration by vital type

        Returns:
            Clinical summary with recommendations
        """

        # Assess overall calibration
        horizons_well_calibrated = sum(
            1 for h in by_horizon.values() if h.get('well_calibrated')
        )
        total_horizons = len(by_horizon)

        vitals_acceptable = sum(
            1 for v in by_vital.values() if v.get('accuracy', 0) >= 0.75
        )
        total_vitals = len(by_vital)

        # Determine readiness
        if horizons_well_calibrated == total_horizons and vitals_acceptable == total_vitals:
            readiness = 'READY_FOR_CLINICAL_DEPLOYMENT'
            confidence_for_deployment = 'HIGH'
            action = 'PROCEED TO WEEK 6'
        elif horizons_well_calibrated >= total_horizons * 0.8:
            readiness = 'READY_WITH_CAVEATS'
            confidence_for_deployment = 'MODERATE'
            action = 'PROCEED WITH MONITORING'
        else:
            readiness = 'NOT_READY'
            confidence_for_deployment = 'LOW'
            action = 'CONTINUE DEVELOPMENT'

        return {
            'overall_readiness': readiness,
            'deployment_confidence': confidence_for_deployment,
            'recommendation': action,
            'horizons': {
                'well_calibrated': horizons_well_calibrated,
                'total': total_horizons,
                'pct': (horizons_well_calibrated / total_horizons * 100) if total_horizons > 0 else 0,
            },
            'vitals': {
                'acceptable': vitals_acceptable,
                'total': total_vitals,
                'pct': (vitals_acceptable / total_vitals * 100) if total_vitals > 0 else 0,
            },
            'details_by_horizon': by_horizon,
            'details_by_vital': by_vital,
        }
