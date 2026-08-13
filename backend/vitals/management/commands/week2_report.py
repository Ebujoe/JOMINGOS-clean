"""
Django management command for Week 2 readiness assessment.

Usage:
    python manage.py week2_report                # Full cohort report
    python manage.py week2_report --patient=1   # Single patient
    python manage.py week2_report --stability   # Baseline stability analysis
    python manage.py week2_report --export      # Export to JSON file
"""

from django.core.management.base import BaseCommand
from patients.models import Patient
from vitals.utils.data_quality_report import (
    DataQualityReport,
    BaselineStabilityAnalyzer,
)
import json
import logging
from typing import List

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Generate Week 2 readiness report"

    def add_arguments(self, parser):
        parser.add_argument(
            '--patient',
            type=int,
            help='Specific patient ID',
        )
        parser.add_argument(
            '--stability',
            action='store_true',
            help='Include baseline stability analysis',
        )
        parser.add_argument(
            '--export',
            action='store_true',
            help='Export report to JSON file',
        )

    def handle(self, *args, **options):
        """Main command handler."""

        # Determine patients
        if options['patient']:
            patients = Patient.objects.filter(id=options['patient'])
        else:
            patients = Patient.objects.all()

        if not patients.exists():
            self.stdout.write(self.style.ERROR("No patients found"))
            return

        self.stdout.write(self.style.SUCCESS(f"\n{'='*70}"))
        self.stdout.write(self.style.SUCCESS("WEEK 2 READINESS REPORT"))
        self.stdout.write(self.style.SUCCESS(f"{'='*70}\n"))

        patient_ids = list(patients.values_list('id', flat=True))

        if options['patient']:
            # Single patient report
            self._report_single_patient(
                options['patient'],
                include_stability=options['stability'],
            )
        else:
            # Cohort report
            self._report_cohort(patient_ids)

        if options['export']:
            self._export_reports(patient_ids)

    def _report_single_patient(self, patient_id: int, include_stability: bool = False):
        """Generate report for single patient."""

        report = DataQualityReport.generate_patient_report(patient_id)

        if not report.get('status') == 'DATA_AVAILABLE':
            self.stdout.write(self.style.WARNING(f"No data for patient {patient_id}"))
            return

        self.stdout.write(f"Patient: {report['patient_name']}")
        self.stdout.write(f"{'='*70}\n")

        # Quantity metrics
        self.stdout.write("DATA QUANTITY")
        self.stdout.write(f"  Total measurements: {report['total_measurements']}")
        self.stdout.write(f"  Approved: {report['approved']}")
        self.stdout.write(f"  Rejected: {report['rejected']}")
        self.stdout.write(f"  Approval rate: {report['approval_rate']*100:.1f}%")
        self.stdout.write(f"  Time span: {report['time_span_days']} days")
        self.stdout.write(f"  Rate: {report['measurements_per_day']:.1f} per day\n")

        # Quality metrics
        self.stdout.write("DATA QUALITY")
        self.stdout.write(f"  Average quality score: {report['average_quality_score']:.1f}/100")
        self.stdout.write(f"  Vital types recorded: {report['vital_types_count']}\n")

        # Vital types
        if report['vital_types']:
            self.stdout.write("VITAL TYPE COVERAGE")
            for vital, count in report['vital_types'].items():
                self.stdout.write(f"  {vital}: {count} readings")
            self.stdout.write()

        # Baselines
        if report['baselines_available']:
            self.stdout.write("CALCULATED BASELINES")
            for vital, baseline in report['baselines_available'].items():
                self.stdout.write(
                    f"  {vital}: {baseline['mean']:.1f}±{baseline['std_dev']:.1f} "
                    f"(n={baseline['n_samples']})"
                )
            self.stdout.write()

        # Rejection analysis
        if report['rejection_reasons']:
            self.stdout.write("REJECTION ANALYSIS")
            for reason, count in report['rejection_reasons'].items():
                pct = (count / report['rejected'] * 100) if report['rejected'] > 0 else 0
                self.stdout.write(f"  {reason}: {count} ({pct:.1f}%)")
            self.stdout.write()

        # Week 2 Readiness
        self.stdout.write("WEEK 2 READINESS ASSESSMENT")
        readiness = report['week2_readiness']
        score = report['readiness_score']

        if readiness == 'READY_FOR_PHASE2':
            status_style = self.style.SUCCESS
            status_text = "✓ READY FOR PHASE 2"
        elif readiness == 'IN_PROGRESS':
            status_style = self.style.WARNING
            status_text = "⚠ IN PROGRESS"
        else:
            status_style = self.style.ERROR
            status_text = "✗ NEEDS ATTENTION"

        self.stdout.write(status_style(f"  Status: {status_text}"))
        self.stdout.write(f"  Score: {score}/100\n")

        self.stdout.write("  Details:")
        for detail in report['readiness_details']:
            self.stdout.write(f"    {detail}")

        self.stdout.write("\n  Recommendations:")
        for rec in report['recommendations']:
            self.stdout.write(f"    • {rec}")

        # Stability analysis if requested
        if include_stability:
            self.stdout.write(f"\n{'='*70}")
            self.stdout.write("BASELINE STABILITY ANALYSIS\n")

            stability = BaselineStabilityAnalyzer.analyze_all_baselines(patient_id=report['patient_id'])

            self.stdout.write(f"Overall stability: {stability['overall_stability']}\n")

            if stability['baselines']:
                for vital, analysis in stability['baselines'].items():
                    if analysis['status'] == 'INSUFFICIENT_DATA':
                        self.stdout.write(f"  {vital}: Not enough data ({analysis['samples']} samples)")
                    elif analysis['status'] == 'NO_BASELINE':
                        self.stdout.write(f"  {vital}: No baseline")
                    else:
                        score_str = f"{analysis['stability_score']}/100"
                        self.stdout.write(
                            f"  {vital}: {analysis['status']} ({score_str})"
                        )
                        self.stdout.write(
                            f"    Mean shift: {analysis['mean_shift_percent']:.1f}%"
                        )
                        self.stdout.write(
                            f"    Recommendation: {analysis['recommendation']}"
                        )

    def _report_cohort(self, patient_ids: List[int]):
        """Generate cohort report."""

        report = DataQualityReport.generate_cohort_report(patient_ids)

        self.stdout.write("COHORT SUMMARY")
        self.stdout.write(f"  Patients with data: {report['patients_with_data']}")
        self.stdout.write(f"  Ready for Phase 2: {report['patients_ready_phase2']}")
        self.stdout.write(f"  Progress: {report['progress_percentage']:.1f}%")
        self.stdout.write(f"  Phase 2 readiness: {report['phase2_readiness']}\n")

        self.stdout.write("AGGREGATE METRICS")
        self.stdout.write(f"  Total measurements: {report['total_measurements']}")
        self.stdout.write(f"  Approved: {report['total_approved']}")
        self.stdout.write(f"  Approval rate: {report['overall_approval_rate']*100:.1f}%")
        self.stdout.write(f"  Avg quality score: {report['average_quality_score']:.1f}")
        self.stdout.write(f"  Avg approval rate: {report['average_approval_rate']*100:.1f}%\n")

        # Per-patient summary
        self.stdout.write("PER-PATIENT DETAILS")
        self.stdout.write(f"{'Patient':<30} {'Approved':<12} {'Ready':<10}")
        self.stdout.write("-" * 52)

        for patient_report in report['individual_reports']:
            name = patient_report['patient_name'][:28]
            approved = f"{patient_report['approved']}/{patient_report['total_measurements']}"
            ready = "✓" if patient_report['week2_readiness'] == 'READY_FOR_PHASE2' else "⚠"
            self.stdout.write(f"{name:<30} {approved:<12} {ready:<10}")

        self.stdout.write()

    def _export_reports(self, patient_ids: List[int]):
        """Export reports to JSON."""

        report = DataQualityReport.generate_cohort_report(patient_ids)

        filename = f"week2_report_{report['report_generated'].split('T')[0]}.json"

        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        self.stdout.write(self.style.SUCCESS(f"\nReport exported to: {filename}"))
