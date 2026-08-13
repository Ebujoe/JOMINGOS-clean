"""
PERFORMANCE TRACKING & CONFIDENCE OPTIMIZATION - WEEK 4
=======================================================

Tracks forecast performance over time and optimizes confidence thresholds.

Enables:
1. Continuous performance monitoring
2. Confidence calibration
3. Trend analysis
4. Automated threshold optimization
5. Production readiness metrics
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import numpy as np
import logging

logger = logging.getLogger(__name__)


class PerformanceTracker:
    """Track forecast performance metrics over time."""

    @staticmethod
    def calculate_performance_by_confidence_bin(
        forecasts_list: List[Dict],
    ) -> Dict:
        """
        Calculate performance in different confidence bins.

        Helps understand: do higher confidence forecasts actually perform better?

        Args:
            forecasts_list: List of forecast records with actual values

        Returns:
            Performance by confidence level
        """

        if not forecasts_list:
            return {}

        # Bin forecasts by confidence level
        bins = {
            '0-20%': [],
            '20-40%': [],
            '40-60%': [],
            '60-80%': [],
            '80-100%': [],
        }

        for forecast in forecasts_list:
            conf = forecast.get('confidence_score', 0)
            actual = forecast.get('actual_value')

            if actual is None:
                continue

            error = abs(forecast.get('forecast_value', 0) - actual)

            if conf < 20:
                bins['0-20%'].append(error)
            elif conf < 40:
                bins['20-40%'].append(error)
            elif conf < 60:
                bins['40-60%'].append(error)
            elif conf < 80:
                bins['60-80%'].append(error)
            else:
                bins['80-100%'].append(error)

        # Calculate stats per bin
        results = {}
        for bin_name, errors in bins.items():
            if errors:
                results[bin_name] = {
                    'n_forecasts': len(errors),
                    'mae': float(np.mean(errors)),
                    'rmse': float(np.sqrt(np.mean(np.array(errors) ** 2))),
                    'min_error': float(np.min(errors)),
                    'max_error': float(np.max(errors)),
                }

        return results

    @staticmethod
    def calculate_weekly_trend(
        forecasts_list: List[Dict],
        weeks: int = 4,
    ) -> Dict:
        """
        Calculate performance trend over recent weeks.

        Helps identify: is model performance improving?

        Args:
            forecasts_list: Historical forecasts
            weeks: Number of weeks to analyze

        Returns:
            Trend data by week
        """

        now = datetime.now()
        trends = {}

        for week in range(weeks):
            week_start = now - timedelta(weeks=week + 1)
            week_end = now - timedelta(weeks=week)

            week_forecasts = [
                f for f in forecasts_list
                if week_start <= f.get('forecast_timestamp', now) <= week_end
                and f.get('actual_value') is not None
            ]

            if week_forecasts:
                errors = [
                    abs(f.get('forecast_value', 0) - f['actual_value'])
                    for f in week_forecasts
                ]
                trends[f'week_{week}'] = {
                    'n_forecasts': len(week_forecasts),
                    'mae': float(np.mean(errors)),
                    'avg_confidence': float(
                        np.mean([f.get('confidence_score', 0) for f in week_forecasts])
                    ),
                    'accuracy': float(
                        sum(
                            1 for f in week_forecasts
                            if f.get('prediction_interval_95_lower', 0) <=
                            f.get('actual_value') <=
                            f.get('prediction_interval_95_upper', 0)
                        ) / len(week_forecasts)
                    ),
                }

        return trends

    @staticmethod
    def is_performance_improving(
        week1_mae: float,
        week2_mae: float,
    ) -> bool:
        """Check if performance is improving."""
        if week1_mae == 0:
            return False
        improvement = (week1_mae - week2_mae) / week1_mae
        return improvement > 0.05  # 5% improvement threshold


class ConfidenceOptimizer:
    """Optimize confidence score thresholds based on actual performance."""

    @staticmethod
    def optimize_confidence_threshold(
        forecasts_by_confidence: Dict,
        target_accuracy: float = 0.70,
    ) -> Tuple[float, float]:
        """
        Find confidence threshold that maximizes accuracy.

        Args:
            forecasts_by_confidence: Grouped by confidence level
            target_accuracy: Target accuracy rate (default 70%)

        Returns:
            (optimal_threshold, expected_accuracy)
        """

        # Sort by confidence
        sorted_bins = sorted(
            forecasts_by_confidence.items(),
            key=lambda x: float(x[0].split('-')[0]),
        )

        best_threshold = 0
        best_accuracy = 0

        for bin_name, stats in sorted_bins:
            # Estimate accuracy as inverse of MAE ratio
            # Higher MAE = lower accuracy
            mae = stats.get('mae', 0)
            estimated_accuracy = max(0, 1 - (mae / 10))  # Normalize to 0-1

            if estimated_accuracy >= target_accuracy:
                threshold = float(bin_name.split('-')[0])
                if estimated_accuracy > best_accuracy:
                    best_threshold = threshold
                    best_accuracy = estimated_accuracy

        return best_threshold, best_accuracy

    @staticmethod
    def recommend_confidence_adjustments(
        current_performance: Dict,
        target_validation_score: float = 80.0,
    ) -> List[str]:
        """
        Recommend adjustments to improve confidence calibration.

        Args:
            current_performance: Current validation metrics
            target_validation_score: Target score (0-100)

        Returns:
            List of recommendations
        """

        recommendations = []
        score = current_performance.get('overall_validation_score', 0)

        if score < 50:
            recommendations.append(
                "Low validation score - recommend collecting more data before clinical use"
            )
            recommendations.append(
                "Consider reducing confidence penalty thresholds - system is overly conservative"
            )

        elif score < 70:
            recommendations.append(
                "Moderate validation score - continue monitoring during clinical trials"
            )
            recommendations.append(
                "Increase data collection to 50+ readings per patient"
            )

        else:
            recommendations.append(
                "Good validation score - ready for clinical deployment"
            )

        # Check calibration
        cal = current_performance.get('calibration', {})
        pi_90_cov = cal.get('pi_90_coverage', 0)
        pi_95_cov = cal.get('pi_95_coverage', 0)

        if pi_90_cov < 0.85 or pi_90_cov > 0.95:
            recommendations.append(
                f"90% PI coverage is {pi_90_cov*100:.0f}% (target ~90%) - "
                "adjust interval width"
            )

        if pi_95_cov < 0.90:
            recommendations.append(
                f"95% PI coverage is {pi_95_cov*100:.0f}% (target ~95%) - "
                "intervals too narrow"
            )

        # Check by horizon
        if current_performance.get('horizon_hours', 0) > 168:
            recommendations.append(
                "For long-term forecasts (>7 days), consider increasing confidence penalties"
            )

        return recommendations


class ProductionReadinessAssessment:
    """Assess readiness for production deployment."""

    @staticmethod
    def evaluate_readiness(
        validation_metrics: Dict,
        performance_history: Dict,
    ) -> Dict:
        """
        Comprehensive production readiness evaluation.

        Args:
            validation_metrics: Current validation results
            performance_history: Historical performance data

        Returns:
            Readiness assessment
        """

        criteria = {
            'validation_score': {
                'requirement': 80,
                'current': validation_metrics.get('overall_validation_score', 0),
                'weight': 0.30,
            },
            'accuracy_rate': {
                'requirement': 0.75,
                'current': validation_metrics.get('n_accurate', 0) /
                          validation_metrics.get('n_forecasts', 1),
                'weight': 0.25,
            },
            'calibration': {
                'requirement': 0.80,
                'current': validation_metrics.get('calibration', {}).get(
                    'calibration_score', 0
                ) / 100,
                'weight': 0.25,
            },
            'data_points': {
                'requirement': 100,
                'current': validation_metrics.get('n_forecasts', 0),
                'weight': 0.20,
            },
        }

        # Calculate weighted score
        total_score = 0
        n_criteria = 0

        for criterion, data in criteria.items():
            requirement = data['requirement']
            current = data['current']
            weight = data['weight']

            # Score: 0-100 based on requirement achievement
            if requirement > 1:  # Absolute value
                criterion_score = min(100, (current / requirement) * 100)
            else:  # Percentage
                criterion_score = min(100, (current / requirement) * 100)

            weighted_score = criterion_score * weight
            total_score += weighted_score
            n_criteria += 1

        overall_readiness = total_score / n_criteria if n_criteria > 0 else 0

        # Determine status
        if overall_readiness >= 85:
            status = 'READY_FOR_PRODUCTION'
            recommendation = 'Proceed with deployment'
        elif overall_readiness >= 70:
            status = 'READY_WITH_MONITORING'
            recommendation = 'Deploy with close monitoring'
        elif overall_readiness >= 50:
            status = 'IN_DEVELOPMENT'
            recommendation = 'Continue validation testing'
        else:
            status = 'NOT_READY'
            recommendation = 'More development required'

        return {
            'overall_readiness_score': float(overall_readiness),
            'status': status,
            'recommendation': recommendation,
            'criteria': {k: {
                'requirement': v['requirement'],
                'current': v['current'],
                'met': v['current'] >= v['requirement'],
            } for k, v in criteria.items()},
        }
