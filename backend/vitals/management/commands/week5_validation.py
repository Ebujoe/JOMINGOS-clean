"""
Django management command for Week 5 comprehensive validation.

Generates calibration curves, cross-validation reports, and clinical summaries.

Usage:
    python manage.py week5_validation                           # Complete validation
    python manage.py week5_validation --calibration-curves      # Plot data
    python manage.py week5_validation --horizon-analysis        # By horizon
    python manage.py week5_validation --vital-analysis          # By vital
    python manage.py week5_validation --clinical-summary        # Clinical review
    python manage.py week5_validation --patient=1               # Single patient
"""

from django.core.management.base import BaseCommand
from patients.models import Patient
from vitals.models import PatientForecast
from vitals.utils.calibration_curves import (
    CalibrationCurveGenerator,
    HorizonCalibrationAnalyzer,
    VitalCalibrationAnalyzer,
    CalibrationSummary,
)
from datetime import datetime
from typing import Dict
import json
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Week 5 comprehensive validation with calibration curves"

    def add_arguments(self, parser):
        parser.add_argument(
            '--patient',
            type=int,
            help='Specific patient ID',
        )
        parser.add_argument(
            '--calibration-curves',
            action='store_true',
            help='Generate calibration curve data',
        )
        parser.add_argument(
            '--horizon-analysis',
            action='store_true',
            help='Analyze calibration by horizon',
        )
        parser.add_argument(
            '--vital-analysis',
            action='store_true',
            help='Analyze calibration by vital type',
        )
        parser.add_argument(
            '--clinical-summary',
            action='store_true',
            help='Generate clinical summary for deployment',
        )
        parser.add_argument(
            '--report',
            action='store_true',
            help='Export JSON report',
        )

    def handle(self, *args, **options):
        """Main command handler."""

        self.stdout.write(self.style.SUCCESS(f"\n{'='*70}"))
        self.stdout.write(self.style.SUCCESS("WEEK 5 COMPREHENSIVE VALIDATION"))
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
            self.stdout.write(f"\nPatient: {patient.get_full_name()} (ID: {patient.id})")
            self.stdout.write("=" * 70)

            # Get all forecasts for patient
            forecasts = list(
                PatientForecast.objects.filter(patient=patient).values()
            )

            if not forecasts:
                self.stdout.write(self.style.WARNING("  No forecasts found"))
                continue

            # Convert Decimal to float
            for f in forecasts:
                if f.get('forecast_value'):
                    f['forecast_value'] = float(f['forecast_value'])
                if f.get('actual_value'):
                    f['actual_value'] = float(f['actual_value'])
                if f.get('prediction_interval_90_lower'):
                    f['prediction_interval_90_lower'] = float(f['prediction_interval_90_lower'])
                if f.get('prediction_interval_90_upper'):
                    f['prediction_interval_90_upper'] = float(f['prediction_interval_90_upper'])
                if f.get('prediction_interval_95_lower'):
                    f['prediction_interval_95_lower'] = float(f['prediction_interval_95_lower'])
                if f.get('prediction_interval_95_upper'):
                    f['prediction_interval_95_upper'] = float(f['prediction_interval_95_upper'])

            patient_data = {
                'patient_id': patient.id,
                'patient_name': patient.get_full_name(),
                'total_forecasts': len(forecasts),
            }

            # Horizon analysis
            if options['horizon_analysis'] or options['clinical_summary']:
                self.stdout.write("\nCalibration by Horizon:")
                self.stdout.write("-" * 50)

                horizon_results = HorizonCalibrationAnalyzer.analyze_by_horizon(forecasts)

                for horizon in sorted(horizon_results.keys()):
                    h = horizon_results[horizon]
                    status = "✓" if h['well_calibrated'] else "✗"
                    self.stdout.write(
                        f"  {horizon:3d}h: {status} "
                        f"MAE={h['mae']:.2f} | "
                        f"PI95 coverage={h['pi_95_coverage']*100:.0f}% | "
                        f"n={h['n_forecasts']}"
                    )

                patient_data['by_horizon'] = horizon_results

            # Vital analysis
            if options['vital_analysis'] or options['clinical_summary']:
                self.stdout.write("\nCalibration by Vital Type:")
                self.stdout.write("-" * 50)

                vital_results = VitalCalibrationAnalyzer.analyze_by_vital(forecasts)

                for vital_name in sorted(vital_results.keys()):
                    v = vital_results[vital_name]
                    status = "✓" if v['accuracy'] >= 0.75 else "✗"
                    self.stdout.write(
                        f"  {vital_name}: {status} "
                        f"Accuracy={v['accuracy']*100:.0f}% | "
                        f"MAE={v['mae']:.2f} | "
                        f"n={v['n_forecasts']}"
                    )

                patient_data['by_vital'] = vital_results

            # Calibration curves
            if options['calibration_curves']:
                self.stdout.write("\nGenerating Calibration Curves...")
                self.stdout.write("-" * 50)

                conf_curve = CalibrationCurveGenerator.generate_confidence_calibration_curve(forecasts)
                pi_curve = CalibrationCurveGenerator.generate_pi_coverage_curve(forecasts)
                error_curve = CalibrationCurveGenerator.generate_error_by_confidence_curve(forecasts)

                if conf_curve.get('curve_data'):
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✓ Confidence calibration curve ({len(conf_curve['curve_data'])} points)"
                        )
                    )
                    patient_data['calibration_curve'] = conf_curve

                if pi_curve.get('pi_90'):
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✓ PI coverage curves ({len(pi_curve['pi_90'])} points)"
                        )
                    )
                    patient_data['pi_coverage_curve'] = pi_curve

                if error_curve.get('error_data'):
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✓ Error by confidence curve ({len(error_curve['error_data'])} points)"
                        )
                    )
                    patient_data['error_curve'] = error_curve

            # Clinical summary
            if options['clinical_summary']:
                self.stdout.write("\nClinical Deployment Summary:")
                self.stdout.write("-" * 50)

                horizon_results = HorizonCalibrationAnalyzer.analyze_by_horizon(forecasts)
                vital_results = VitalCalibrationAnalyzer.analyze_by_vital(forecasts)

                summary = CalibrationSummary.generate_clinical_summary(
                    validation_results={},
                    by_horizon=horizon_results,
                    by_vital=vital_results,
                )

                self.stdout.write(
                    f"Overall Readiness: {summary['overall_readiness']}"
                )
                self.stdout.write(
                    f"Deployment Confidence: {summary['deployment_confidence']}"
                )
                self.stdout.write(
                    f"Recommendation: {summary['recommendation']}"
                )
                self.stdout.write(
                    f"\nHorizon Status: {summary['horizons']['well_calibrated']}/{summary['horizons']['total']} "
                    f"({summary['horizons']['pct']:.0f}%) well-calibrated"
                )
                self.stdout.write(
                    f"Vital Status: {summary['vitals']['acceptable']}/{summary['vitals']['total']} "
                    f"({summary['vitals']['pct']:.0f}%) acceptable accuracy"
                )

                patient_data['clinical_summary'] = summary

            report_data['patients'][patient.id] = patient_data

        # Export report if requested
        if options['report']:
            filename = f"week5_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            self.stdout.write(
                self.style.SUCCESS(f"\n✓ Report exported to: {filename}")
            )

        # Overall summary
        self._print_summary(report_data)

    def _print_summary(self, report_data: Dict):
        """Print overall summary."""

        self.stdout.write(f"\n{'='*70}")
        self.stdout.write("WEEK 5 VALIDATION COMPLETE")
        self.stdout.write(f"{'='*70}\n")

        total_patients = len(report_data.get('patients', {}))
        total_forecasts = sum(
            p.get('total_forecasts', 0)
            for p in report_data.get('patients', {}).values()
        )

        self.stdout.write(f"Patients analyzed: {total_patients}")
        self.stdout.write(f"Total forecasts evaluated: {total_forecasts}")

        # Check if ready for clinical validation
        ready_count = 0
        for patient_data in report_data.get('patients', {}).values():
            if patient_data.get('clinical_summary', {}).get('overall_readiness') == 'READY_FOR_CLINICAL_DEPLOYMENT':
                ready_count += 1

        self.stdout.write(f"Ready for clinical validation: {ready_count}/{total_patients}")

        if ready_count == total_patients:
            self.stdout.write(
                self.style.SUCCESS(
                    "\n✓ ALL SYSTEMS READY FOR WEEK 6\n"
                    "  Proceed with clinical expert review"
                )
            )
        elif ready_count > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"\n⚠ PARTIAL READINESS ({ready_count}/{total_patients})\n"
                    "  Review issues by patient before Week 6"
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    "\n✗ NOT READY FOR CLINICAL VALIDATION\n"
                    "  Continue development work"
                )
            )
