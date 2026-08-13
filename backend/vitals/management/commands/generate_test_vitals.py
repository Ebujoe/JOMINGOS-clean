"""
Django management command to generate realistic test vital data.

Usage:
    python manage.py generate_test_vitals                    # 30 vitals per patient
    python manage.py generate_test_vitals --count=50         # 50 vitals per patient
    python manage.py generate_test_vitals --patient=1        # Specific patient
    python manage.py generate_test_vitals --deteriorating    # Deterioration pattern
    python manage.py generate_test_vitals --validate         # Auto-validate after recording
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from patients.models import Patient
from vitals.models import VitalSigns
from vitals.utils.data_generator import (
    PatientVitalSimulator,
    BulkDataGenerator,
    DataQualitySimulator,
)
from vitals.utils.integration import VitalSignsIntegration
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Generate realistic test vital data for patients"

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=30,
            help='Number of vitals per patient (default: 30)',
        )
        parser.add_argument(
            '--patient',
            type=int,
            help='Specific patient ID (default: all)',
        )
        parser.add_argument(
            '--deteriorating',
            action='store_true',
            help='Generate deteriorating pattern (testing)',
        )
        parser.add_argument(
            '--validate',
            action='store_true',
            help='Auto-validate after recording',
        )
        parser.add_argument(
            '--with-issues',
            action='store_true',
            help='Introduce quality issues (10%)',
        )

    def handle(self, *args, **options):
        """Main command handler."""

        count = options['count']
        validate = options['validate']
        deteriorating = options['deteriorating']
        with_issues = options['with_issues']

        # Determine patients
        if options['patient']:
            patients = Patient.objects.filter(id=options['patient'])
        else:
            patients = Patient.objects.all()

        if not patients.exists():
            self.stdout.write(self.style.ERROR("No patients found"))
            return

        self.stdout.write(self.style.SUCCESS(f"Generating {count} vitals per patient..."))

        integration = VitalSignsIntegration() if validate else None

        total_created = 0
        total_validated = 0

        for patient in patients:
            self.stdout.write(f"\n{'='*70}")
            self.stdout.write(f"Patient: {patient.get_full_name()} (ID: {patient.id})")
            self.stdout.write(f"{'='*70}")

            # Generate vital sequence
            if deteriorating:
                self.stdout.write("  [MODE] Deteriorating pattern")
                vitals_data = PatientVitalSimulator.generate_deteriorating_sequence(
                    patient_id=patient.id,
                    count=count,
                )
            else:
                self.stdout.write("  [MODE] Normal variation")
                vitals_data = BulkDataGenerator.generate_for_patient(
                    patient_id=patient.id,
                    patient_name=patient.get_full_name(),
                    count=count,
                )

            # Add quality issues if requested
            if with_issues:
                self.stdout.write("  [ISSUES] Adding 10% quality issues")
                vitals_data = DataQualitySimulator.add_quality_issues(
                    vitals_data,
                    issue_rate=0.1,
                )

            # Record vitals
            self.stdout.write(f"  Recording {len(vitals_data)} vitals...")

            created = 0
            validated = 0

            for vital_data in vitals_data:
                try:
                    # Create vital record
                    vital = VitalSigns.objects.create(
                        patient=patient,
                        heart_rate=int(vital_data.get('heart_rate', 0)) if vital_data.get('heart_rate') else None,
                        respiratory_rate=int(vital_data.get('respiratory_rate', 0)) if vital_data.get('respiratory_rate') else None,
                        oxygen_saturation=Decimal(str(vital_data.get('oxygen_saturation', 0))) if vital_data.get('oxygen_saturation') else None,
                        temperature=Decimal(str(vital_data.get('temperature', 0))) if vital_data.get('temperature') else None,
                        bp_systolic=int(vital_data.get('bp_systolic', 0)) if vital_data.get('bp_systolic') else None,
                        bp_diastolic=int(vital_data.get('bp_diastolic', 0)) if vital_data.get('bp_diastolic') else None,
                        recorded_at=vital_data['timestamp'],
                        notes='Generated test data',
                    )

                    created += 1

                    # Validate if requested
                    if validate and integration:
                        # Determine which vital to validate
                        vital_name = None
                        value = None

                        if vital_data.get('heart_rate'):
                            vital_name = 'heart_rate'
                            value = vital_data['heart_rate']
                        elif vital_data.get('respiratory_rate'):
                            vital_name = 'respiratory_rate'
                            value = vital_data['respiratory_rate']

                        if vital_name and value:
                            try:
                                _, quality_check, _ = integration.record_and_validate_vital(
                                    patient_id=patient.id,
                                    vital_name=vital_name,
                                    value=value,
                                    recorded_by_user='system',
                                    device_id='simulator',
                                    clinical_context='Test data generation',
                                )

                                if quality_check.approved:
                                    validated += 1

                            except Exception as e:
                                logger.error(f"Validation error: {e}")

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"    Error creating vital: {e}")
                    )

            total_created += created
            total_validated += validated

            self.stdout.write(
                self.style.SUCCESS(
                    f"  ✓ Created {created} vitals"
                    f"{f' ({validated} validated)' if validate else ''}"
                )
            )

            # Calculate baselines if we have enough data
            total_vitals = VitalSigns.objects.filter(
                patient=patient,
                is_approved=True,
            ).count()

            if total_vitals >= 5:
                self.stdout.write("  Calculating baselines...")
                baselines = integration.calculate_patient_baselines(patient.id) if integration else {}

                if baselines:
                    self.stdout.write(
                        self.style.SUCCESS(f"  ✓ Calculated {len(baselines)} baselines")
                    )
                    for vital_name, baseline in baselines.items():
                        self.stdout.write(
                            f"    - {vital_name}: {baseline.mean_value:.1f}±{baseline.std_dev:.1f} "
                            f"(n={baseline.n_samples})"
                        )

        # Summary
        self.stdout.write(f"\n{'='*70}")
        self.stdout.write(self.style.SUCCESS("DATA GENERATION COMPLETE"))
        self.stdout.write(f"{'='*70}")
        self.stdout.write(f"Total vitals created: {total_created}")
        if validate:
            self.stdout.write(f"Total validated: {total_validated}")
            if total_created > 0:
                approval_rate = total_validated / total_created * 100
                self.stdout.write(f"Approval rate: {approval_rate:.1f}%")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nGenerated data is ready for testing. "
                f"Run: python manage.py validate_and_calculate_baselines"
            )
        )
