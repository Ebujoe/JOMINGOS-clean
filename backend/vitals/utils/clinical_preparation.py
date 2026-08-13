"""
CLINICAL PREPARATION FRAMEWORK - WEEK 6
========================================

Generates materials for expert clinical review before deployment.

Provides:
1. Extended cross-validation report (200+ predictions)
2. Multi-patient cohort analysis
3. Clinical case summaries
4. Risk assessment and mitigation
5. Final readiness checklist
6. Expert review materials
"""

from typing import Dict, List, Tuple
from datetime import datetime
import numpy as np
import logging

logger = logging.getLogger(__name__)


class ExtendedCrossValidationReport:
    """Generate comprehensive cross-validation report for 200+ predictions."""

    @staticmethod
    def generate_comprehensive_report(
        forecasts: List[Dict],
        min_forecasts: int = 200,
    ) -> Dict:
        """
        Generate comprehensive CV report with extensive testing.

        Args:
            forecasts: All forecast records with actual values
            min_forecasts: Minimum forecasts required (target 200+)

        Returns:
            Comprehensive report
        """

        valid_forecasts = [
            f for f in forecasts if f.get('actual_value') is not None
        ]

        if len(valid_forecasts) < 10:
            return {'status': 'insufficient_data'}

        # Overall metrics
        errors = np.array([
            abs(f.get('forecast_value', 0) - f.get('actual_value'))
            for f in valid_forecasts
        ])

        report = {
            'total_forecasts': len(valid_forecasts),
            'status': 'ADEQUATE' if len(valid_forecasts) >= min_forecasts else 'SUBOPTIMAL',
            'progress': f"{len(valid_forecasts)}/{min_forecasts}",

            # Error metrics
            'mae': float(np.mean(errors)),
            'rmse': float(np.sqrt(np.mean(errors ** 2))),
            'median_error': float(np.median(errors)),
            'max_error': float(np.max(errors)),

            # Accuracy
            'accuracy_rate': float(
                sum(
                    1 for f in valid_forecasts
                    if f.get('prediction_interval_95_lower', 0) <=
                    f.get('actual_value') <=
                    f.get('prediction_interval_95_upper', 0)
                ) / len(valid_forecasts)
            ),

            # Confidence analysis
            'avg_confidence': float(
                np.mean([f.get('confidence_score', 0) for f in valid_forecasts])
            ),

            # PI coverage
            'pi_95_coverage': float(
                sum(
                    1 for f in valid_forecasts
                    if f.get('prediction_interval_95_lower', 0) <=
                    f.get('actual_value') <=
                    f.get('prediction_interval_95_upper', 0)
                ) / len(valid_forecasts)
            ),

            # Safety metrics
            'no_extreme_errors': float(np.max(errors)) < np.mean(errors) + 3 * np.std(errors),
            'consistent_performance': float(np.std(errors) / np.mean(errors)) < 0.5 if np.mean(errors) > 0 else False,

            # Recommendation
            'recommendation': ExtendedCrossValidationReport._generate_recommendation(
                len(valid_forecasts),
                float(np.mean(errors)),
                float(
                    sum(
                        1 for f in valid_forecasts
                        if f.get('prediction_interval_95_lower', 0) <=
                        f.get('actual_value') <=
                        f.get('prediction_interval_95_upper', 0)
                    ) / len(valid_forecasts)
                )
            ),
        }

        return report

    @staticmethod
    def _generate_recommendation(n_forecasts: int, mae: float, accuracy: float) -> str:
        """Generate recommendation based on metrics."""
        if n_forecasts >= 200 and accuracy >= 0.80 and mae < 5:
            return 'READY_FOR_CLINICAL_DEPLOYMENT'
        elif n_forecasts >= 150 and accuracy >= 0.75 and mae < 7:
            return 'READY_WITH_CLOSE_MONITORING'
        elif n_forecasts >= 100 and accuracy >= 0.70:
            return 'ACCEPTABLE_FOR_RESEARCH_USE'
        else:
            return 'CONTINUE_DEVELOPMENT'


class MultiPatientCohortAnalysis:
    """Analyze forecasting performance across multiple patients."""

    @staticmethod
    def analyze_cohort_performance(
        patients_forecasts: Dict[int, List[Dict]],
    ) -> Dict:
        """
        Analyze performance across patient cohort.

        Args:
            patients_forecasts: Dict of patient_id -> forecasts

        Returns:
            Cohort analysis
        """

        if not patients_forecasts:
            return {}

        patient_results = {}
        all_accuracies = []
        all_maes = []

        for patient_id, forecasts in patients_forecasts.items():
            valid = [f for f in forecasts if f.get('actual_value') is not None]

            if len(valid) < 10:
                continue

            errors = np.array([
                abs(f.get('forecast_value', 0) - f.get('actual_value'))
                for f in valid
            ])

            accuracy = sum(
                1 for f in valid
                if f.get('prediction_interval_95_lower', 0) <=
                f.get('actual_value') <=
                f.get('prediction_interval_95_upper', 0)
            ) / len(valid)

            mae = np.mean(errors)

            patient_results[patient_id] = {
                'n_forecasts': len(valid),
                'mae': float(mae),
                'accuracy': float(accuracy),
                'confidence_consistency': float(np.std([f.get('confidence_score', 0) for f in valid])),
            }

            all_accuracies.append(accuracy)
            all_maes.append(mae)

        # Cohort summary
        if all_accuracies:
            return {
                'n_patients': len(patient_results),
                'total_forecasts': sum(r['n_forecasts'] for r in patient_results.values()),
                'cohort_mean_accuracy': float(np.mean(all_accuracies)),
                'cohort_mean_mae': float(np.mean(all_maes)),
                'cohort_std_accuracy': float(np.std(all_accuracies)),
                'cohort_std_mae': float(np.std(all_maes)),
                'min_accuracy': float(np.min(all_accuracies)),
                'max_accuracy': float(np.max(all_accuracies)),
                'patient_results': patient_results,
            }

        return {}


class ClinicalCaseSummary:
    """Generate case summaries for expert clinical review."""

    @staticmethod
    def generate_case_summaries(
        patient_forecasts: Dict[int, List[Dict]],
        n_cases: int = 5,
    ) -> List[Dict]:
        """
        Select and summarize representative cases for review.

        Args:
            patient_forecasts: Dict of patient_id -> forecasts
            n_cases: Number of cases to summarize

        Returns:
            List of case summaries
        """

        cases = []

        for patient_id, forecasts in patient_forecasts.items():
            valid = [f for f in forecasts if f.get('actual_value') is not None]

            if len(valid) < 5:
                continue

            # Select varied cases (best, worst, typical)
            errors = [
                abs(f.get('forecast_value', 0) - f.get('actual_value'))
                for f in valid
            ]

            best_idx = np.argmin(errors)
            worst_idx = np.argmax(errors)
            median_idx = np.argsort(errors)[len(errors) // 2]

            for idx, label in [(best_idx, 'Best'), (median_idx, 'Typical'), (worst_idx, 'Worst')]:
                forecast = valid[idx]
                error = errors[idx]

                case = {
                    'patient_id': patient_id,
                    'label': label,
                    'vital': forecast.get('vital_name', 'unknown'),
                    'horizon': forecast.get('horizon_hours', 24),
                    'forecast': float(forecast.get('forecast_value', 0)),
                    'actual': float(forecast.get('actual_value', 0)),
                    'error': float(error),
                    'confidence': float(forecast.get('confidence_score', 0)),
                    'pi_95_lower': float(forecast.get('prediction_interval_95_lower', 0)),
                    'pi_95_upper': float(forecast.get('prediction_interval_95_upper', 0)),
                    'within_pi': (
                        forecast.get('prediction_interval_95_lower', 0) <=
                        forecast.get('actual_value', 0) <=
                        forecast.get('prediction_interval_95_upper', 0)
                    ),
                    'assessment': (
                        'Accurate and confident' if error < 5 and forecast.get('confidence_score', 0) >= 50
                        else 'Accurate but low confidence' if error < 5
                        else 'Inaccurate - requires review'
                    ),
                }

                cases.append(case)

            if len(cases) >= n_cases:
                return cases[:n_cases]

        return cases


class FinalReadinessChecklist:
    """Generate final readiness checklist for Week 7 clinical validation."""

    @staticmethod
    def generate_checklist(
        validation_report: Dict,
        cohort_analysis: Dict,
        case_summaries: List[Dict],
    ) -> Dict:
        """
        Generate comprehensive readiness checklist.

        Args:
            validation_report: Extended CV report
            cohort_analysis: Multi-patient analysis
            case_summaries: Clinical case summaries

        Returns:
            Readiness checklist
        """

        checks = {
            'data_sufficiency': validation_report.get('total_forecasts', 0) >= 200,
            'accuracy_target': validation_report.get('accuracy_rate', 0) >= 0.75,
            'mae_acceptable': validation_report.get('mae', float('inf')) < 7,
            'confidence_consistent': cohort_analysis.get('cohort_std_accuracy', 1) < 0.15,
            'no_failure_modes': validation_report.get('no_extreme_errors', False),
            'pi_coverage_valid': 0.90 <= validation_report.get('pi_95_coverage', 0) <= 1.0,
            'cohort_balanced': cohort_analysis.get('n_patients', 0) >= 2,
            'cases_reviewed': len(case_summaries) >= 5,
        }

        passed = sum(1 for v in checks.values() if v)
        total = len(checks)

        readiness_score = (passed / total * 100) if total > 0 else 0

        return {
            'checks': checks,
            'passed': passed,
            'total': total,
            'readiness_score': readiness_score,
            'status': (
                'READY_FOR_CLINICAL_VALIDATION' if readiness_score >= 75
                else 'READY_WITH_CAVEATS' if readiness_score >= 50
                else 'NOT_READY'
            ),
            'critical_issues': [
                k for k, v in checks.items() if not v and k in [
                    'data_sufficiency', 'accuracy_target', 'pi_coverage_valid'
                ]
            ],
            'non_critical_issues': [
                k for k, v in checks.items() if not v and k not in [
                    'data_sufficiency', 'accuracy_target', 'pi_coverage_valid'
                ]
            ],
        }


class RiskAssessment:
    """Assess risks and mitigation strategies."""

    @staticmethod
    def generate_risk_assessment(readiness: Dict) -> Dict:
        """
        Generate clinical risk assessment.

        Returns:
            Risk assessment with mitigation strategies
        """

        risks = []

        if readiness['readiness_score'] < 75:
            risks.append({
                'level': 'HIGH',
                'risk': 'Model not fully validated',
                'mitigation': 'Continue data collection and validation',
            })

        if not readiness['checks'].get('data_sufficiency'):
            risks.append({
                'level': 'MEDIUM',
                'risk': 'Insufficient forecast history (<200)',
                'mitigation': 'Generate more predictions before clinical use',
            })

        if not readiness['checks'].get('accuracy_target'):
            risks.append({
                'level': 'MEDIUM',
                'risk': 'Accuracy below 75% target',
                'mitigation': 'Improve data quality and revalidate',
            })

        if not readiness['checks'].get('pi_coverage_valid'):
            risks.append({
                'level': 'HIGH',
                'risk': 'Prediction intervals not properly calibrated',
                'mitigation': 'Recalibrate uncertainty bounds',
            })

        if readiness['critical_issues']:
            risks.append({
                'level': 'HIGH',
                'risk': f"Critical issues: {', '.join(readiness['critical_issues'])}",
                'mitigation': 'Address all critical issues before deployment',
            })

        return {
            'risks': risks,
            'overall_risk_level': 'LOW' if len([r for r in risks if r['level'] == 'HIGH']) == 0 else 'MEDIUM' if len([r for r in risks if r['level'] == 'HIGH']) == 1 else 'HIGH',
            'recommended_action': (
                'PROCEED_TO_CLINICAL_VALIDATION' if readiness['readiness_score'] >= 75
                else 'PROCEED_WITH_MONITORING' if readiness['readiness_score'] >= 50
                else 'CONTINUE_DEVELOPMENT'
            ),
        }
