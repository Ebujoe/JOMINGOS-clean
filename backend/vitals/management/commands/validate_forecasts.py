"""
Django management command for Week 4 comprehensive validation.

Usage:
    python manage.py validate_forecasts                      # Validate all
    python manage.py validate_forecasts --patient=1          # Single patient
    python manage.py validate_forecasts --vital=heart_rate   # Single vital
    python manage.py validate_forecasts --calibration        # Detailed calibration
    python manage.py validate_forecasts --report             # Generate report
"""

from django.core.management.base import BaseCommand
from patients.models import Patient
from vitals.models import PatientForecast
from vitals.utils.forecast_validation import (
    ComprehensiveValidator,
    validation_to_dict,
)
from datetime import datetime
from typing import Dict
import json
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Comprehensive forecast validation for Week 4"

    def add_arguments(self, parser):
        parser.add_argument(
            '--patient',
            type=int,
            help='Specific patient ID',
        )
        parser.add_argument(
            '--vital',
            type=str,
            help='Specific vital name',
        )
        parser.add_argument(
            '--calibration',
            action='store_true',
            help='Show detailed calibration analysis',
        )
        parser.add_argument(
            '--report',
            action='store_true',
            help='Generate JSON report',
        )

    def handle(self, *args, **options):
        """Main command handler."""

        self.stdout.write(self.style.SUCCESS(f"\n{'='*70}"))
        self.stdout.write(self.style.SUCCESS("WEEK 4 FORECAST VALIDATION"))
        self.stdout.write(self.style.SUCCESS(f"{'='*70}\n"))

        # Determine patients
        if options['patient']:
            patients = Patient.objects.filter(id=options['patient'])
        else:
            patients = Patient.objects.all()

        if not patients.exists():
            self.stdout.write(self.style.ERROR("No patients found"))
            return

        report_data = {
            'validation_timestamp': str(datetime.now()),
            'patients': {},
        }

        for patient in patients:
            self.stdout.write(f"\n{'='*70}")
            self.stdout.write(f"Patient: {patient.get_full_name()} (ID: {patient.id})")
            self.stdout.write(f"{'='*70}\n")

            # Get vital types
            vitals_qs = PatientForecast.objects.filter(patient=patient)

            if options['vital']:
                vitals_qs = vitals_qs.filter(vital_name=options['vital'])

            vital_types = vitals_qs.values_list('vital_name', flat=True).distinct()

            if not vital_types:
                self.stdout.write(self.style.WARNING("  No forecasts found"))
                continue

            patient_data = {
                'patient_id': patient.id,
                'patient_name': patient.get_full_name(),
                'vitals': {},
            }

            for vital_name in vital_types:
                self.stdout.write(f"\n{vital_name.replace('_', ' ').title()}")
                self.stdout.write("-" * 50)

                # Validate all horizons
                horizon_results = ComprehensiveValidator.validate_all_horizons(
                    patient_id=patient.id,
                    vital_name=vital_name,
                )

                vital_data = {}

                for horizon, metrics in horizon_results.items():
                    if not metrics:
                        continue

                    # Display results
                    score = metrics.overall_validation_score
                    accuracy = (
                        metrics.n_accurate / metrics.n_forecasts * 100
                        if metrics.n_forecasts > 0 else 0
                    )

                    # Score color coding
                    if score >= 80:
                        score_style = self.style.SUCCESS
                        score_icon = "✓"
                    elif score >= 60:
                        score_style = self.style.WARNING
                        score_icon = "⚠"
                    else:
                        score_style = self.style.ERROR
                        score_icon = "✗"

                    self.stdout.write(
                        f"  {horizon:3d}h: "
                        f"{score_style(f'{score_icon} {score:.0f}')} "
                        f"| Accuracy: {accuracy:.0f}% "
                        f"| MAE: {metrics.mae:.2f}"
                    )

                    # Calibration details if requested
                    if options['calibration']:
                        cal = metrics.calibration
                        self.stdout.write(
                            f"       Calibration: 90%PI covers {cal.pi_90_coverage*100:.0f}% "
                            f"(target ~90%), "
                            f"95%PI covers {cal.pi_95_coverage*100:.0f}% (target ~95%)"
                        )
                        if cal.is_well_calibrated:
                            self.stdout.write(
                                self.style.SUCCESS("       ✓ Well calibrated")
                            )
                        else:
                            self.stdout.write(
                                self.style.WARNING("       ⚠ Calibration issues")
                            )

                    # Store in report
                    vital_data[horizon] = validation_to_dict(metrics)

                patient_data['vitals'][vital_name] = vital_data

            report_data['patients'][patient.id] = patient_data

            # Summary for patient
            self._print_patient_summary(patient.id, report_data)

        # Overall summary
        self._print_overall_summary(report_data)

        # Export report if requested
        if options['report']:
            filename = f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            self.stdout.write(
                self.style.SUCCESS(f"\n✓ Report exported to: {filename}")
            )

    def _print_patient_summary(self, patient_id: int, report_data: Dict):
        """Print summary for patient."""

        patient_data = report_data['patients'].get(patient_id, {})
        vitals = patient_data.get('vitals', {})

        if not vitals:
            return

        self.stdout.write(f"\n{'='*70}")
        self.stdout.write("PATIENT VALIDATION SUMMARY")
        self.stdout.write(f"{'='*70}\n")

        total_score = 0
        count = 0

        for vital_name, horizons in vitals.items():
            for horizon, metrics in horizons.items():
                score = metrics.get('overall_validation_score', 0)
                total_score += score
                count += 1

        if count > 0:
            avg_score = total_score / count
            if avg_score >= 80:
                status = self.style.SUCCESS("EXCELLENT")
            elif avg_score >= 60:
                status = self.style.WARNING("GOOD")
            else:
                status = self.style.ERROR("FAIR")

            self.stdout.write(f"Average validation score: {status} ({avg_score:.0f}/100)")

    def _print_overall_summary(self, report_data: Dict):
        """Print overall summary."""

        self.stdout.write(f"\n{'='*70}")
        self.stdout.write("OVERALL VALIDATION SUMMARY")
        self.stdout.write(f"{'='*70}\n")

        patients = report_data.get('patients', {})

        if not patients:
            self.stdout.write(self.style.WARNING("No validation data"))
            return

        total_forecasts = 0
        total_accurate = 0
        total_score = 0

        for patient_id, patient_data in patients.items():
            vitals = patient_data.get('vitals', {})
            for vital_name, horizons in vitals.items():
                for horizon, metrics in horizons.items():
                    total_forecasts += metrics.get('n_forecasts', 0)
                    total_accurate += metrics.get('n_accurate', 0)
                    total_score += metrics.get('overall_validation_score', 0)

        n_metrics = sum(
            len(horizons)
            for p in patients.values()
            for v in p.get('vitals', {}).values()
            for horizons in [v]
        )

        if n_metrics > 0:
            avg_score = total_score / n_metrics
            overall_accuracy = total_accurate / total_forecasts if total_forecasts > 0 else 0

            self.stdout.write(f"Total forecasts evaluated: {total_forecasts}")
            self.stdout.write(f"Accurate forecasts (within PI): {total_accurate}")
            self.stdout.write(f"Accuracy rate: {overall_accuracy*100:.1f}%")
            self.stdout.write(f"Average validation score: {avg_score:.0f}/100")

            # Readiness assessment
            self.stdout.write(f"\n{'='*70}")
            self.stdout.write("READINESS FOR CLINICAL VALIDATION")
            self.stdout.write(f"{'='*70}\n")

            if avg_score >= 80 and overall_accuracy >= 0.80:
                self.stdout.write(
                    self.style.SUCCESS(
                        "✓ READY FOR CLINICAL VALIDATION (Week 7)\n"
                        "  All metrics meet requirements for clinical deployment"
                    )
                )
            elif avg_score >= 60:
                self.stdout.write(
                    self.style.WARNING(
                        "⚠ ACCEPTABLE - MINOR IMPROVEMENTS NEEDED\n"
                        f"  Current: {avg_score:.0f}/100 | Target: 80+/100"
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        "✗ NEEDS WORK - CONTINUE DEVELOPMENT\n"
                        f"  Current: {avg_score:.0f}/100 | Target: 80+/100"
                    )
                )
