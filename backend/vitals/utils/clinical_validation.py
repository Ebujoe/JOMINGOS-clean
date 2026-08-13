"""
CLINICAL VALIDATION FRAMEWORK - WEEK 7
=======================================

Generates materials for expert clinical panel review.

Provides:
1. Expert panel review orchestration
2. Safety assessment
3. Utility assessment
4. Clinical approval workflow
5. Clinician feedback collection
"""

from typing import Dict, List, Tuple
from datetime import datetime
import numpy as np
import logging

logger = logging.getLogger(__name__)


class ExpertPanelReviewMaterials:
    """Prepare materials for expert clinical panel review."""

    @staticmethod
    def prepare_review_materials(
        forecasts: List[Dict],
        cases: List[Dict],
        cohort_analysis: Dict,
        n_review: int = 50,
    ) -> Dict:
        """
        Prepare structured review materials for clinical experts.

        Args:
            forecasts: All forecast records
            cases: Representative case summaries
            cohort_analysis: Multi-patient performance
            n_review: Number of predictions to review (target 50)

        Returns:
            Structured review materials
        """

        valid_forecasts = [
            f for f in forecasts if f.get('actual_value') is not None
        ]

        # Select diverse cases: different vitals, horizons, accuracy levels
        selected = ExpertPanelReviewMaterials._select_diverse_predictions(
            valid_forecasts, n_review
        )

        # Prepare review format
        review_items = []

        for forecast in selected:
            error = abs(forecast.get('forecast_value', 0) - forecast.get('actual_value', 0))
            within_pi = (
                forecast.get('prediction_interval_95_lower', 0) <=
                forecast.get('actual_value', 0) <=
                forecast.get('prediction_interval_95_upper', 0)
            )

            review_items.append({
                'vital': forecast.get('vital_name', 'unknown'),
                'horizon': forecast.get('horizon_hours', 24),
                'forecast': float(forecast.get('forecast_value', 0)),
                'actual': float(forecast.get('actual_value', 0)),
                'error': float(error),
                'error_pct': float((error / forecast.get('actual_value', 1) * 100) if forecast.get('actual_value') else 0),
                'confidence': float(forecast.get('confidence_score', 0)),
                'pi_95_lower': float(forecast.get('prediction_interval_95_lower', 0)),
                'pi_95_upper': float(forecast.get('prediction_interval_95_upper', 0)),
                'within_pi': within_pi,
                'clinical_assessment': 'Acceptable' if error < 5 and within_pi else 'Requires review' if error < 10 else 'Poor',
                'expert_review_needed': not (error < 5 and within_pi),
            })

        return {
            'n_cases_selected': len(review_items),
            'target_n_cases': n_review,
            'review_items': review_items,
            'cohort_context': cohort_analysis,
            'representative_cases': cases,
        }

    @staticmethod
    def _select_diverse_predictions(forecasts: List[Dict], n: int) -> List[Dict]:
        """Select diverse predictions across vitals, horizons, and accuracy levels."""

        if len(forecasts) <= n:
            return forecasts

        # Group by vital and horizon
        groups = {}

        for f in forecasts:
            vital = f.get('vital_name', 'unknown')
            horizon = f.get('horizon_hours', 24)
            key = (vital, horizon)

            if key not in groups:
                groups[key] = []
            groups[key].append(f)

        # Select evenly from each group
        selected = []
        per_group = max(1, n // len(groups))

        for group_forecasts in groups.values():
            # Sort by error and select best, middle, worst
            sorted_by_error = sorted(
                group_forecasts,
                key=lambda f: abs(f.get('forecast_value', 0) - f.get('actual_value', 0))
            )

            # Take diverse representatives
            if len(sorted_by_error) <= per_group:
                selected.extend(sorted_by_error)
            else:
                # Sample evenly across error range
                indices = np.linspace(0, len(sorted_by_error) - 1, per_group, dtype=int)
                selected.extend([sorted_by_error[i] for i in indices])

        return selected[:n]


class SafetyAssessment:
    """Assess safety metrics and adverse event risk."""

    @staticmethod
    def generate_safety_assessment(
        forecasts: List[Dict],
    ) -> Dict:
        """
        Generate comprehensive safety assessment.

        Args:
            forecasts: All forecast records

        Returns:
            Safety assessment
        """

        valid_forecasts = [
            f for f in forecasts if f.get('actual_value') is not None
        ]

        if len(valid_forecasts) < 10:
            return {'status': 'insufficient_data'}

        # Calculate safety metrics
        errors = np.array([
            abs(f.get('forecast_value', 0) - f.get('actual_value', 0))
            for f in valid_forecasts
        ])

        # Identify unsafe predictions
        unsafe_predictions = [
            f for f in valid_forecasts
            if abs(f.get('forecast_value', 0) - f.get('actual_value', 0)) > 10
        ]

        unsafe_rate = len(unsafe_predictions) / len(valid_forecasts)

        # Identify missed alerts
        missed_alerts = [
            f for f in valid_forecasts
            if (f.get('actual_value', 0) > f.get('forecast_value', 0) + 5 and
                f.get('confidence_score', 0) > 50)
        ]

        missed_alert_rate = len(missed_alerts) / len(valid_forecasts) if valid_forecasts else 0

        # False positive rate (forecast warned but didn't occur)
        false_positives = [
            f for f in valid_forecasts
            if (f.get('forecast_value', 0) > f.get('actual_value', 0) + 5 and
                f.get('confidence_score', 0) > 50 and
                not (f.get('prediction_interval_95_lower', 0) <=
                     f.get('actual_value', 0) <=
                     f.get('prediction_interval_95_upper', 0)))
        ]

        false_positive_rate = len(false_positives) / len(valid_forecasts) if valid_forecasts else 0

        # Safety score
        safety_score = SafetyAssessment._calculate_safety_score(
            unsafe_rate, missed_alert_rate, false_positive_rate
        )

        return {
            'total_predictions': len(valid_forecasts),
            'unsafe_predictions': len(unsafe_predictions),
            'unsafe_rate': float(unsafe_rate),
            'missed_alerts': len(missed_alerts),
            'missed_alert_rate': float(missed_alert_rate),
            'false_positives': len(false_positives),
            'false_positive_rate': float(false_positive_rate),
            'max_error': float(np.max(errors)),
            '95_percentile_error': float(np.percentile(errors, 95)),
            'safety_score': safety_score,
            'safety_status': (
                'SAFE' if safety_score >= 85
                else 'CONDITIONAL' if safety_score >= 70
                else 'UNSAFE'
            ),
            'key_risks': SafetyAssessment._identify_key_risks(
                unsafe_rate, missed_alert_rate, false_positive_rate
            ),
        }

    @staticmethod
    def _calculate_safety_score(
        unsafe_rate: float,
        missed_alert_rate: float,
        false_positive_rate: float,
    ) -> float:
        """Calculate overall safety score (0-100)."""

        # Missed alerts are most critical (weight 50%)
        # Unsafe predictions are critical (weight 35%)
        # False positives are secondary (weight 15%)

        score = 100
        score -= missed_alert_rate * 100 * 0.50  # Up to -50 points
        score -= unsafe_rate * 100 * 0.35  # Up to -35 points
        score -= false_positive_rate * 100 * 0.15  # Up to -15 points

        return max(0, min(100, score))

    @staticmethod
    def _identify_key_risks(
        unsafe_rate: float,
        missed_alert_rate: float,
        false_positive_rate: float,
    ) -> List[str]:
        """Identify key safety risks."""

        risks = []

        if missed_alert_rate > 0.05:
            risks.append(f"CRITICAL: {missed_alert_rate*100:.1f}% missed alerts")

        if unsafe_rate > 0.10:
            risks.append(f"HIGH: {unsafe_rate*100:.1f}% unsafe predictions (error>10)")

        if false_positive_rate > 0.15:
            risks.append(f"MEDIUM: {false_positive_rate*100:.1f}% false positives")

        return risks


class UtilityAssessment:
    """Assess clinical utility and benefit."""

    @staticmethod
    def generate_utility_assessment(
        forecasts: List[Dict],
        cohort_analysis: Dict,
    ) -> Dict:
        """
        Generate clinical utility assessment.

        Args:
            forecasts: All forecast records
            cohort_analysis: Multi-patient performance

        Returns:
            Utility assessment
        """

        valid_forecasts = [
            f for f in forecasts if f.get('actual_value') is not None
        ]

        if len(valid_forecasts) < 10:
            return {'status': 'insufficient_data'}

        # Accuracy metrics
        within_pi_95 = sum(
            1 for f in valid_forecasts
            if (f.get('prediction_interval_95_lower', 0) <=
                f.get('actual_value') <=
                f.get('prediction_interval_95_upper', 0))
        ) / len(valid_forecasts)

        # Decision support capability
        confident_predictions = [
            f for f in valid_forecasts
            if f.get('confidence_score', 0) >= 70
        ]

        confident_accuracy = (
            sum(
                1 for f in confident_predictions
                if (f.get('prediction_interval_95_lower', 0) <=
                    f.get('actual_value') <=
                    f.get('prediction_interval_95_upper', 0))
            ) / len(confident_predictions)
            if confident_predictions else 0
        )

        # Time horizon capability
        by_horizon = {}

        for f in valid_forecasts:
            horizon = f.get('horizon_hours', 24)
            if horizon not in by_horizon:
                by_horizon[horizon] = []
            by_horizon[horizon].append(f)

        horizon_utility = {}

        for horizon, h_forecasts in by_horizon.items():
            utility = UtilityAssessment._assess_horizon_utility(h_forecasts)
            horizon_utility[horizon] = utility

        # Clinical decision impact
        clinical_impact = UtilityAssessment._assess_clinical_impact(
            confident_accuracy, within_pi_95
        )

        return {
            'total_predictions': len(valid_forecasts),
            'overall_accuracy': float(within_pi_95),
            'high_confidence_predictions': len(confident_predictions),
            'high_confidence_accuracy': float(confident_accuracy),
            'horizon_utility': horizon_utility,
            'clinical_impact': clinical_impact,
            'utility_score': UtilityAssessment._calculate_utility_score(
                within_pi_95, confident_accuracy, clinical_impact
            ),
            'utility_status': (
                'HIGH' if within_pi_95 >= 0.80
                else 'MODERATE' if within_pi_95 >= 0.70
                else 'LOW'
            ),
        }

    @staticmethod
    def _assess_horizon_utility(horizon_forecasts: List[Dict]) -> Dict:
        """Assess utility for specific horizon."""

        valid = [f for f in horizon_forecasts if f.get('actual_value') is not None]

        if not valid:
            return {}

        accuracy = sum(
            1 for f in valid
            if (f.get('prediction_interval_95_lower', 0) <=
                f.get('actual_value') <=
                f.get('prediction_interval_95_upper', 0))
        ) / len(valid)

        return {
            'n_predictions': len(valid),
            'accuracy': float(accuracy),
            'suitable_for_clinical_use': accuracy >= 0.75,
        }

    @staticmethod
    def _assess_clinical_impact(confident_accuracy: float, overall_accuracy: float) -> str:
        """Assess potential clinical impact."""

        if confident_accuracy >= 0.85 and overall_accuracy >= 0.80:
            return 'HIGH: Can support clinical decisions'
        elif confident_accuracy >= 0.75 and overall_accuracy >= 0.70:
            return 'MODERATE: Adjunctive to clinical judgment'
        else:
            return 'LOW: Research use only'

    @staticmethod
    def _calculate_utility_score(
        overall_accuracy: float,
        confident_accuracy: float,
        clinical_impact: str,
    ) -> float:
        """Calculate utility score (0-100)."""

        score = 0

        # Overall accuracy (50 points)
        score += overall_accuracy * 50

        # High-confidence accuracy (40 points)
        score += confident_accuracy * 40

        # Clinical impact bonus (10 points)
        if 'HIGH' in clinical_impact:
            score += 10
        elif 'MODERATE' in clinical_impact:
            score += 5

        return float(score)


class ClinicalApprovalWorkflow:
    """Manage clinical approval workflow."""

    @staticmethod
    def generate_approval_summary(
        safety_assessment: Dict,
        utility_assessment: Dict,
    ) -> Dict:
        """
        Generate approval summary for clinical leadership.

        Args:
            safety_assessment: Safety metrics
            utility_assessment: Utility metrics

        Returns:
            Approval summary
        """

        # Overall approval decision
        safety_approved = safety_assessment.get('safety_status') in ['SAFE', 'CONDITIONAL']
        utility_approved = utility_assessment.get('utility_status') in ['HIGH', 'MODERATE']

        if safety_approved and utility_approved:
            approval_status = 'APPROVED_FOR_DEPLOYMENT'
            approval_confidence = 'HIGH'
        elif safety_approved and utility_assessment.get('utility_status') == 'LOW':
            approval_status = 'APPROVED_FOR_RESEARCH_USE'
            approval_confidence = 'MODERATE'
        else:
            approval_status = 'NOT_APPROVED'
            approval_confidence = 'LOW'

        # Deployment conditions
        deployment_conditions = []

        if safety_assessment.get('safety_score', 100) < 85:
            deployment_conditions.append('Continuous safety monitoring required')

        if utility_assessment.get('utility_score', 0) < 70:
            deployment_conditions.append('Adjunctive use only - not primary decision')

        if safety_assessment.get('missed_alert_rate', 0) > 0.05:
            deployment_conditions.append('Enhanced surveillance for missed alerts')

        return {
            'approval_status': approval_status,
            'approval_confidence': approval_confidence,
            'safety_approved': safety_approved,
            'safety_score': safety_assessment.get('safety_score', 0),
            'utility_approved': utility_approved,
            'utility_score': utility_assessment.get('utility_score', 0),
            'deployment_conditions': deployment_conditions,
            'monitoring_requirements': ClinicalApprovalWorkflow._define_monitoring(
                safety_assessment, utility_assessment
            ),
            'approval_date': str(datetime.now()),
            'approval_valid_until': 'Ongoing - annual review recommended',
        }

    @staticmethod
    def _define_monitoring(
        safety_assessment: Dict,
        utility_assessment: Dict,
    ) -> List[str]:
        """Define monitoring requirements post-approval."""

        requirements = []

        if safety_assessment.get('unsafe_rate', 0) > 0.05:
            requirements.append('Daily review of unsafe predictions')

        if safety_assessment.get('missed_alert_rate', 0) > 0.02:
            requirements.append('Continuous alert accuracy monitoring')

        if utility_assessment.get('utility_score', 100) < 75:
            requirements.append('Weekly utility assessment')

        requirements.append('Monthly performance review')
        requirements.append('Quarterly expert panel review')

        return requirements
