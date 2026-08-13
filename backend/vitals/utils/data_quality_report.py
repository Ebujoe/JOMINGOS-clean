"""
COMPREHENSIVE DATA QUALITY REPORTING
====================================

Week 2 Deliverable: Detailed data quality reports and readiness assessment.

Provides:
1. Per-patient quality metrics
2. Baseline stability analysis
3. Data collection progress tracking
4. Phase 2 readiness assessment
5. Quality trend analysis
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class DataQualityReport:
    """Generate comprehensive quality reports."""

    @staticmethod
    def generate_patient_report(patient_id: int) -> Dict:
        """
        Generate detailed quality report for a patient.

        Returns:
            Dict with comprehensive quality metrics
        """

        from vitals.models import VitalSigns, PatientBaselineData
        from patients.models import Patient

        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return {}

        all_vitals = VitalSigns.objects.filter(patient=patient)
        approved = all_vitals.filter(is_approved=True).count()
        rejected = all_vitals.filter(is_approved=False).count()
        total = all_vitals.count()

        # Calculate quality metrics
        if total == 0:
            return {
                'patient_id': patient_id,
                'patient_name': patient.get_full_name(),
                'status': 'NO_DATA',
                'total_measurements': 0,
            }

        avg_quality_score = (
            all_vitals.filter(quality_score__isnull=False)
            .aggregate(avg=__import__('django.db.models', fromlist=['Avg']).Avg('quality_score'))
            ['avg'] or 0
        )

        # Time span
        first_vital = all_vitals.order_by('recorded_at').first()
        last_vital = all_vitals.order_by('recorded_at').last()
        days_span = (last_vital.recorded_at - first_vital.recorded_at).days if first_vital else 0

        # Vital type coverage
        vital_types = {}
        for vital in all_vitals.values('vital_name').distinct():
            if vital['vital_name']:
                vital_types[vital['vital_name']] = all_vitals.filter(
                    vital_name=vital['vital_name'],
                    is_approved=True
                ).count()

        # Baseline info
        baselines = PatientBaselineData.objects.filter(patient=patient)
        baseline_info = {}
        for baseline in baselines:
            baseline_info[baseline.vital_name] = {
                'mean': float(baseline.mean_value),
                'std_dev': float(baseline.std_dev),
                'n_samples': baseline.n_samples,
            }

        # Rejection analysis
        rejection_reasons = {}
        for vital in all_vitals.filter(is_approved=False):
            reason = vital.quality_check_notes.split('\n')[0] if vital.quality_check_notes else 'Unknown'
            rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1

        # Determine readiness
        readiness = DataQualityReport._assess_readiness(
            total_approved=approved,
            rejection_rate=rejected / total if total > 0 else 0,
            avg_quality=avg_quality_score,
            baselines_available=len(baseline_info),
            vital_types=len(vital_types),
        )

        return {
            'patient_id': patient_id,
            'patient_name': patient.get_full_name(),
            'report_generated': datetime.now().isoformat(),
            'status': 'DATA_AVAILABLE',

            # Quantity metrics
            'total_measurements': total,
            'approved': approved,
            'rejected': rejected,
            'approval_rate': approved / total if total > 0 else 0,
            'rejection_rate': rejected / total if total > 0 else 0,

            # Quality metrics
            'average_quality_score': avg_quality_score,
            'time_span_days': days_span,
            'measurements_per_day': total / (days_span + 1) if days_span > 0 else 0,

            # Coverage
            'vital_types': vital_types,
            'vital_types_count': len(vital_types),

            # Baselines
            'baselines_available': baseline_info,
            'baselines_count': len(baseline_info),

            # Issues
            'rejection_reasons': rejection_reasons,

            # Readiness
            'week2_readiness': readiness['status'],
            'readiness_score': readiness['score'],
            'readiness_details': readiness['details'],
            'recommendations': readiness['recommendations'],
        }

    @staticmethod
    def generate_cohort_report(patient_ids: List[int]) -> Dict:
        """
        Generate aggregate report for multiple patients.

        Returns:
            Dict with cohort-level statistics
        """

        individual_reports = []
        total_vitals = 0
        total_approved = 0
        total_rejected = 0
        ready_count = 0

        for patient_id in patient_ids:
            report = DataQualityReport.generate_patient_report(patient_id)

            if report.get('status') == 'DATA_AVAILABLE':
                individual_reports.append(report)
                total_vitals += report['total_measurements']
                total_approved += report['approved']
                total_rejected += report['rejected']

                if report['week2_readiness'] == 'READY_FOR_PHASE2':
                    ready_count += 1

        # Aggregate statistics
        avg_quality = (
            sum(r['average_quality_score'] for r in individual_reports) / len(individual_reports)
            if individual_reports else 0
        )

        avg_approval_rate = (
            sum(r['approval_rate'] for r in individual_reports) / len(individual_reports)
            if individual_reports else 0
        )

        return {
            'report_type': 'COHORT',
            'report_generated': datetime.now().isoformat(),
            'patients_with_data': len(individual_reports),
            'patients_ready_phase2': ready_count,

            # Aggregate metrics
            'total_measurements': total_vitals,
            'total_approved': total_approved,
            'total_rejected': total_rejected,
            'overall_approval_rate': total_approved / total_vitals if total_vitals > 0 else 0,
            'average_quality_score': avg_quality,
            'average_approval_rate': avg_approval_rate,

            # Per-patient details
            'individual_reports': individual_reports,

            # Phase 2 readiness
            'phase2_readiness': 'READY' if ready_count == len(individual_reports) else 'IN_PROGRESS',
            'progress_percentage': (ready_count / len(individual_reports) * 100) if individual_reports else 0,
        }

    @staticmethod
    def _assess_readiness(
        total_approved: int,
        rejection_rate: float,
        avg_quality: float,
        baselines_available: int,
        vital_types: int,
    ) -> Dict:
        """Assess readiness for Phase 2."""

        score = 0
        details = []
        recommendations = []

        # Data volume (30 points)
        if total_approved >= 30:
            score += 30
            details.append('✓ Sufficient data (30+ readings)')
        elif total_approved >= 20:
            score += 20
            details.append('⚠ Moderate data (20-29 readings)')
            recommendations.append('Collect 10 more readings for optimal baselines')
        elif total_approved >= 10:
            score += 10
            details.append('⚠ Limited data (10-19 readings)')
            recommendations.append('Need 20+ more readings for baselines')
        else:
            details.append('✗ Insufficient data (<10 readings)')
            recommendations.append('Continue data collection - need 30+ readings')

        # Quality (30 points)
        if rejection_rate < 0.05:
            score += 30
            details.append('✓ Excellent quality (<5% rejection)')
        elif rejection_rate < 0.10:
            score += 20
            details.append('✓ Good quality (5-10% rejection)')
        elif rejection_rate < 0.20:
            score += 10
            details.append('⚠ Fair quality (10-20% rejection)')
            recommendations.append('Review rejected vitals and improve recording')
        else:
            details.append('✗ Poor quality (>20% rejection)')
            recommendations.append('Investigate rejection causes - retrain staff')

        # Quality score (20 points)
        if avg_quality >= 90:
            score += 20
            details.append('✓ Excellent measurement quality (90+)')
        elif avg_quality >= 80:
            score += 15
            details.append('✓ Good measurement quality (80-90)')
        elif avg_quality >= 70:
            score += 10
            details.append('⚠ Fair measurement quality (70-80)')
        else:
            details.append('⚠ Low measurement quality (<70)')
            recommendations.append('Check vital sign recording procedures')

        # Baselines (10 points)
        if baselines_available >= vital_types:
            score += 10
            details.append(f'✓ Baselines calculated ({baselines_available} vitals)')
        elif baselines_available > 0:
            score += 5
            details.append(f'⚠ Partial baselines ({baselines_available}/{vital_types})')
            recommendations.append('Need more data for missing vital baselines')
        else:
            details.append('⚠ No baselines yet')
            recommendations.append('Collect 5+ readings to calculate baselines')

        # Vital types (10 points)
        if vital_types >= 4:
            score += 10
            details.append(f'✓ Multiple vital types ({vital_types})')
        else:
            score += 5
            details.append(f'⚠ Limited vital types ({vital_types})')
            recommendations.append('Ensure all vital types are being recorded')

        # Overall status
        if score >= 80:
            status = 'READY_FOR_PHASE2'
        elif score >= 60:
            status = 'IN_PROGRESS'
        else:
            status = 'NEEDS_ATTENTION'

        if not recommendations:
            recommendations.append('Ready to proceed with baseline validation')

        return {
            'status': status,
            'score': score,
            'details': details,
            'recommendations': recommendations,
        }


class BaselineStabilityAnalyzer:
    """Analyze baseline stability and trends."""

    @staticmethod
    def analyze_baseline_stability(patient_id: int, vital_name: str) -> Dict:
        """
        Analyze whether a baseline is stable enough for forecasting.

        Returns:
            Stability assessment
        """

        from vitals.models import VitalSigns, PatientBaselineData

        # Get baseline
        try:
            baseline = PatientBaselineData.objects.get(
                patient_id=patient_id,
                vital_name=vital_name,
            )
        except PatientBaselineData.DoesNotExist:
            return {'status': 'NO_BASELINE'}

        # Get vitals and split into windows
        vitals = list(
            VitalSigns.objects.filter(
                patient_id=patient_id,
                vital_name=vital_name,
                is_approved=True,
            ).order_by('recorded_at').values_list('value', flat=True)
        )

        if len(vitals) < 10:
            return {'status': 'INSUFFICIENT_DATA', 'samples': len(vitals)}

        import statistics

        # Split into early and late measurements
        mid_point = len(vitals) // 2
        early = vitals[:mid_point]
        late = vitals[mid_point:]

        # Calculate statistics for each
        early_mean = statistics.mean(early)
        early_stdev = statistics.stdev(early) if len(early) > 1 else 0
        late_mean = statistics.mean(late)
        late_stdev = statistics.stdev(late) if len(late) > 1 else 0

        # Check for significant change
        mean_shift = abs(late_mean - early_mean)
        shift_percent = (mean_shift / early_mean * 100) if early_mean else 0

        if shift_percent < 5:
            stability = 'STABLE'
            score = 90
        elif shift_percent < 10:
            stability = 'SOMEWHAT_STABLE'
            score = 70
        else:
            stability = 'UNSTABLE'
            score = 50

        return {
            'status': stability,
            'stability_score': score,
            'samples': len(vitals),
            'early_period': {
                'mean': float(early_mean),
                'std_dev': float(early_stdev),
                'n': len(early),
            },
            'late_period': {
                'mean': float(late_mean),
                'std_dev': float(late_stdev),
                'n': len(late),
            },
            'mean_shift_percent': float(shift_percent),
            'recommendation': 'Ready for forecasting' if stability == 'STABLE' else 'Continue monitoring',
        }

    @staticmethod
    def analyze_all_baselines(patient_id: int) -> Dict:
        """Analyze stability of all patient baselines."""

        from vitals.models import PatientBaselineData

        baselines = PatientBaselineData.objects.filter(patient_id=patient_id)

        results = {
            'patient_id': patient_id,
            'report_generated': datetime.now().isoformat(),
            'baselines': {},
            'overall_stability': 'STABLE',
        }

        unstable_count = 0

        for baseline in baselines:
            analysis = BaselineStabilityAnalyzer.analyze_baseline_stability(
                patient_id, baseline.vital_name
            )
            results['baselines'][baseline.vital_name] = analysis

            if analysis['status'] == 'UNSTABLE':
                unstable_count += 1

        if unstable_count > 0:
            results['overall_stability'] = 'UNSTABLE'
        elif unstable_count == 0 and len(results['baselines']) > 0:
            results['overall_stability'] = 'STABLE'

        return results
