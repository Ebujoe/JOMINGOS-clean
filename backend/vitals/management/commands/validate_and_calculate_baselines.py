"""
Django management command for Week 1 automated validation pipeline.

Usage:
    python manage.py validate_and_calculate_baselines
    python manage.py validate_and_calculate_baselines --patient=1
    python manage.py validate_and_calculate_baselines --report
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from patients.models import Patient
from vitals.models import VitalSigns
from vitals.utils.integration import VitalSignsIntegration
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run Week 1 validation pipeline: validate all vitals and calculate baselines"

    def add_arguments(self, parser):
        parser.add_argument(
            '--patient',
            type=int,
            help='Specific patient ID to process (default: all)',
        )
        parser.add_argument(
            '--report',
            action='store_true',
            help='Generate quality reports after validation',
        )
        parser.add_argument(
            '--unvalidated-only',
            action='store_true',
            help='Only process vitals that haven\'t been validated yet',
        )

    def handle(self, *args, **options):
        """Main command handler."""

        integration = VitalSignsIntegration()

        # Determine which patients to process
        if options['patient']:
            patients = Patient.objects.filter(id=options['patient'])
        else:
            patients = Patient.objects.all()

        if not patients.exists():
            self.stdout.write(self.style.ERROR("No patients found"))
            return

        self.stdout.write(self.style.SUCCESS(f"Processing {patients.count()} patient(s)..."))

        total_vitals = 0
        total_approved = 0
        total_rejected = 0

        # Process each patient
        for patient in patients:
            self.stdout.write(f"\n{'='*70}")
            self.stdout.write(f"Patient: {patient.get_full_name()} (ID: {patient.id})")
            self.stdout.write(f"{'='*70}")

            # Get vitals to process
            vitals_qs = VitalSigns.objects.filter(patient=patient).order_by('recorded_at')

            if options['unvalidated_only']:
                vitals_qs = vitals_qs.filter(quality_check_timestamp__isnull=True)

            vitals_to_process = vitals_qs.values_list('id', flat=True)

            if not vitals_to_process:
                self.stdout.write(self.style.WARNING("  No vitals to process"))
                continue

            self.stdout.write(f"  Processing {len(vitals_to_process)} vital measurements...")

            patient_approved = 0
            patient_rejected = 0

            # Process each vital
            for vital_id in vitals_to_process:
                vital = VitalSigns.objects.get(id=vital_id)

                # Extract vital value (handle multiple vital types)
                vital_value = None
                vital_name = None

                if vital.heart_rate is not None:
                    vital_value = vital.heart_rate
                    vital_name = 'heart_rate'
                elif vital.respiratory_rate is not None:
                    vital_value = vital.respiratory_rate
                    vital_name = 'respiratory_rate'
                elif vital.oxygen_saturation is not None:
                    vital_value = vital.oxygen_saturation
                    vital_name = 'oxygen_saturation'
                elif vital.temperature is not None:
                    vital_value = vital.temperature
                    vital_name = 'temperature'
                elif vital.bp_systolic is not None:
                    vital_value = vital.bp_systolic
                    vital_name = 'bp_systolic'
                else:
                    continue

                # Get previous measurements for context
                previous_vitals = VitalSigns.objects.filter(
                    patient=patient,
                    vital_name=vital_name if hasattr(vital, 'vital_name') else None,
                    recorded_at__lt=vital.recorded_at,
                ).order_by('-recorded_at')[:10]

                # Skip if already validated
                if vital.quality_check_timestamp:
                    continue

                # Validate
                try:
                    _, quality_check, _ = integration.record_and_validate_vital(
                        patient_id=patient.id,
                        vital_name=vital_name,
                        value=float(vital_value),
                        recorded_by_user=vital.recorded_by.username if vital.recorded_by else None,
                    )

                    if quality_check.approved:
                        patient_approved += 1
                    else:
                        patient_rejected += 1

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"    Error validating vital {vital_id}: {e}")
                    )

            total_vitals += len(vitals_to_process)
            total_approved += patient_approved
            total_rejected += patient_rejected

            self.stdout.write(
                self.style.SUCCESS(
                    f"  ✓ Validated {len(vitals_to_process)} vitals "
                    f"({patient_approved} approved, {patient_rejected} rejected)"
                )
            )

            # Calculate baselines
            self.stdout.write("  Calculating baselines...")
            baselines = integration.calculate_patient_baselines(patient.id)

            if baselines:
                self.stdout.write(
                    self.style.SUCCESS(f"  ✓ Calculated {len(baselines)} baselines")
                )
                for vital_name, baseline in baselines.items():
                    self.stdout.write(
                        f"    - {vital_name}: {baseline.mean_value:.1f}±{baseline.std_dev:.1f} "
                        f"(n={baseline.n_samples})"
                    )
            else:
                self.stdout.write(self.style.WARNING("  No baselines calculated (insufficient data)"))

            # Generate report if requested
            if options['report']:
                self.stdout.write("  Generating quality report...")
                report = integration.generate_quality_report(patient.id)

                self.stdout.write("\n  Quality Report:")
                self.stdout.write(f"    Total measurements: {report['total_measurements']}")
                self.stdout.write(f"    Approved: {report['approved']}")
                self.stdout.write(f"    Rejected: {report['rejected']}")
                self.stdout.write(f"    Approval rate: {report['approval_rate']*100:.1f}%")
                self.stdout.write(f"    Avg quality score: {report['average_quality_score']:.1f}")
                self.stdout.write(f"    Weeks of data: {report['weeks_of_data']:.1f}")

        # Summary
        self.stdout.write(f"\n{'='*70}")
        self.stdout.write(self.style.SUCCESS("VALIDATION PIPELINE COMPLETE"))
        self.stdout.write(f"{'='*70}")
        self.stdout.write(f"Total vitals processed: {total_vitals}")
        self.stdout.write(self.style.SUCCESS(f"Approved: {total_approved}"))
        self.stdout.write(self.style.WARNING(f"Rejected: {total_rejected}"))

        if total_vitals > 0:
            approval_rate = total_approved / total_vitals * 100
            self.stdout.write(f"Overall approval rate: {approval_rate:.1f}%")

        self.stdout.write(self.style.SUCCESS("\nValidation and baseline calculation complete!"))
