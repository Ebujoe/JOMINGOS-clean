"""
Management command: Train forecasting models on vital signs data

Trains ensemble forecasting models on historical patient data and
generates 24-hour forecasts with uncertainty quantification.

This is the data-driven approach: models are fitted to actual patient data,
not abstract test cases.

Usage:
    python manage.py train_models_on_data
    python manage.py train_models_on_data --patient=1
"""

from django.core.management.base import BaseCommand
from patients.models import Patient
from vitals.models import VitalSigns, PatientForecast
from vitals.utils.model_training import ModelTrainer
from datetime import datetime
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Train forecasting models on actual patient vital signs data"

    def add_arguments(self, parser):
        parser.add_argument('--patient', type=int, help='Specific patient ID')

    def handle(self, *args, **options):
        """Main command handler."""

        self.stdout.write(self.style.SUCCESS(f"\n{'='*70}"))
        self.stdout.write(self.style.SUCCESS("TRAINING FORECASTING MODELS ON PATIENT DATA"))
        self.stdout.write(self.style.SUCCESS(f"{'='*70}\n"))

        # Get patients
        if options['patient']:
            patients = Patient.objects.filter(id=options['patient'])
        else:
            patients = Patient.objects.all()

        if not patients.exists():
            self.stdout.write(self.style.ERROR("No patients found"))
            return

        vital_names = ['heart_rate', 'respiratory_rate', 'oxygen_saturation', 'temperature']
        total_forecasts = 0
        successful = 0

        for patient in patients:
            self.stdout.write(f"\nPatient: {patient.get_full_name()}")
            self.stdout.write("=" * 70)

            # Check data availability
            vitals_count = VitalSigns.objects.filter(patient=patient).count()
            self.stdout.write(f"  Historical data: {vitals_count} vital sign records")

            for vital_name in vital_names:
                # Train model on this vital
                result = ModelTrainer.train_patient_models(patient, vital_name)

                if result.get('status') != 'success':
                    self.stdout.write(
                        f"  {vital_name}: SKIP ({result.get('status')}, "
                        f"{result.get('n_points', 0)} points)"
                    )
                    continue

                # Create forecast record
                try:
                    forecast = PatientForecast.objects.create(
                        patient=patient,
                        vital_name=vital_name,
                        forecast_value=Decimal(str(result['forecast_value'])),
                        confidence_score=result['confidence_score'],
                        prediction_interval_90_lower=Decimal(
                            str(result['prediction_interval_90_lower'])
                        ),
                        prediction_interval_90_upper=Decimal(
                            str(result['prediction_interval_90_upper'])
                        ),
                        prediction_interval_95_lower=Decimal(
                            str(result['prediction_interval_95_lower'])
                        ),
                        prediction_interval_95_upper=Decimal(
                            str(result['prediction_interval_95_upper'])
                        ),
                        forecast_reliability=result['forecast_reliability'],
                        recommendation=result['recommendation'],
                        horizon_hours=24,
                        forecast_timestamp=datetime.now(),
                    )

                    self.stdout.write(
                        f"  {vital_name}: TRAINED & FORECASTED"
                    )
                    self.stdout.write(
                        f"    Training points: {result['n_training_points']}"
                    )
                    self.stdout.write(
                        f"    Forecast: {result['forecast_value']:.1f} "
                        f"(±{result['uncertainty']:.1f})"
                    )
                    self.stdout.write(
                        f"    Confidence: {result['confidence_score']:.0f}%"
                    )
                    self.stdout.write(
                        f"    95% PI: [{result['prediction_interval_95_lower']:.1f}, "
                        f"{result['prediction_interval_95_upper']:.1f}]"
                    )
                    self.stdout.write(
                        f"    Status: {result['forecast_reliability']}"
                    )

                    successful += 1

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"  {vital_name}: ERROR - {str(e)}")
                    )

                total_forecasts += 1

        # Summary
        self.stdout.write(f"\n{'='*70}")
        self.stdout.write("TRAINING COMPLETE")
        self.stdout.write(f"{'='*70}")

        self.stdout.write(f"\nSummary:")
        self.stdout.write(f"  Total vital forecasts: {total_forecasts}")
        self.stdout.write(f"  Successful models: {successful}")
        self.stdout.write(f"  Success rate: {successful/max(total_forecasts,1)*100:.0f}%")

        self.stdout.write(f"\nModels:")
        self.stdout.write(f"  - Trained on actual patient data")
        self.stdout.write(f"  - Ensemble of 4 time-series methods")
        self.stdout.write(f"  - 24-hour forecasts with 90%/95% PIs")
        self.stdout.write(f"  - Uncertainty quantified from data")
        self.stdout.write(f"  - Confidence scores calibrated to data quality")

        self.stdout.write(f"\n[OK] Models are now ready for validation")
        self.stdout.write(f"  Run: python manage.py week6_clinical_prep")
        self.stdout.write(f"\n{'='*70}\n")
