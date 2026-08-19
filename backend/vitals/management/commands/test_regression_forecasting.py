"""
TEST REGRESSION & EXPLAINABLE AI FORECASTING

This management command tests the complete regression + XAI system
with actual patient vital signs data from the database.

Usage:
    python manage.py test_regression_forecasting
    python manage.py test_regression_forecasting --patient=1
    python manage.py test_regression_forecasting --vital=heart_rate
"""

from django.core.management.base import BaseCommand
from django.db.models import Q
import logging

from vitals.models import VitalSigns, Patient
from vitals.regression.vital_forecaster import VitalSignsForecaster, BatchForecastor

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Test regression forecasting on real patient data."""

    help = 'Test regression and explainable AI forecasting with real patient vital signs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--patient',
            type=int,
            help='Patient ID to test (default: all patients)',
        )
        parser.add_argument(
            '--vital',
            type=str,
            help='Vital type to test (heart_rate, blood_glucose, bp_systolic, etc.)',
        )
        parser.add_argument(
            '--min-measurements',
            type=int,
            default=10,
            help='Minimum measurements required (default: 10)',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed calculation steps',
        )

    def handle(self, *args, **options):
        """Execute the test."""
        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write(self.style.SUCCESS('REGRESSION & EXPLAINABLE AI FORECASTING TEST'))
        self.stdout.write(self.style.SUCCESS('='*80 + '\n'))

        # Get configuration
        patient_id = options.get('patient')
        vital_type = options.get('vital')
        min_measurements = options.get('min_measurements', 10)
        verbose = options.get('verbose', False)

        try:
            # Query vital signs
            vitals_query = VitalSigns.objects.all()

            if patient_id:
                vitals_query = vitals_query.filter(patient_id=patient_id)

            # Group by vital type
            vital_types = [vital_type] if vital_type else self._get_vital_types(vitals_query)

            if not vital_types:
                self.stdout.write(self.style.WARNING('No vital types found'))
                return

            # Test each vital type
            batch = BatchForecastor()
            total_forecasts = 0

            for vtype in vital_types:
                self.stdout.write(self.style.HTTP_INFO(f'\n[TESTING: {vtype.upper()}]'))
                self.stdout.write('-' * 80)

                # Get vitals for this type
                vitals = vitals_query.filter(**{f'{vtype}__isnull': False}).order_by('recorded_at')

                # Group by patient
                patients_dict = {}
                for vital in vitals:
                    if vital.patient_id not in patients_dict:
                        patients_dict[vital.patient_id] = []
                    patients_dict[vital.patient_id].append(vital)

                # Test each patient
                for patient_id_test, patient_vitals in patients_dict.items():
                    if len(patient_vitals) < min_measurements:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  Skipping Patient {patient_id_test}: "
                                f"Only {len(patient_vitals)} measurements (need {min_measurements})"
                            )
                        )
                        continue

                    try:
                        patient = Patient.objects.get(id=patient_id_test)
                        result = self._test_patient_vital(
                            patient, vtype, patient_vitals, verbose
                        )

                        if result:
                            batch.forecast_vital_for_patient(
                                patient_id_test, vtype, result['measurements']
                            )
                            total_forecasts += 1

                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"  Error testing patient {patient_id_test}: {e}"))

            # Summary report
            self._print_summary_report(batch, total_forecasts)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {e}'))
            import traceback
            traceback.print_exc()

    def _get_vital_types(self, vitals_query):
        """Get list of vital types with data."""
        vital_fields = [
            'heart_rate', 'blood_glucose', 'bp_systolic', 'bp_diastolic',
            'temperature', 'respiratory_rate', 'oxygen_saturation'
        ]

        available = []
        for field in vital_fields:
            if vitals_query.filter(**{f'{field}__isnull': False}).exists():
                available.append(field)

        return available

    def _test_patient_vital(self, patient, vital_type, vitals, verbose):
        """Test forecasting for one patient vital."""
        try:
            # Extract measurements
            measurements = []
            for vital in vitals:
                value = getattr(vital, vital_type)
                if value is not None:
                    measurements.append(float(value))

            if len(measurements) < 2:
                return None

            # Create forecaster
            forecaster = VitalSignsForecaster(vital_type)

            # Generate forecast
            result = forecaster.forecast(measurements)

            # Display result
            patient_name = f"{patient.first_name} {patient.last_name}"
            self.stdout.write(self.style.SUCCESS(f'\n  Patient: {patient_name} (ID: {patient.id})'))
            self.stdout.write(f'  Measurements: {len(measurements)}')
            self.stdout.write(f'  Mean: {result.measurement_mean:.2f}')
            self.stdout.write(f'  Std Dev: {result.measurement_std:.2f}')

            # Forecast result
            self.stdout.write(self.style.HTTP_SUCCESS(f'\n  [FORECAST]'))
            self.stdout.write(f'  Next {vital_type}: {result.forecast_value:.2f}')
            self.stdout.write(f'  90% PI: [{result.prediction_interval_90[0]:.2f}, {result.prediction_interval_90[1]:.2f}]')
            self.stdout.write(f'  95% PI: [{result.prediction_interval_95[0]:.2f}, {result.prediction_interval_95[1]:.2f}]')

            # Confidence
            self.stdout.write(self.style.HTTP_SUCCESS(f'\n  [CONFIDENCE: {result.confidence}% - {result.confidence_level}]'))
            self.stdout.write(f'  Data Volume:        {result.confidence_factors["data_volume"]}%')
            self.stdout.write(f'  Model Agreement:    {result.confidence_factors["model_agreement"]}%')
            self.stdout.write(f'  Extrapolation:      {result.confidence_factors["extrapolation_distance"]}%')
            self.stdout.write(f'  Stability:          {result.confidence_factors["stability"]}%')

            # Individual predictions
            if verbose:
                self.stdout.write(self.style.HTTP_INFO(f'\n  [INDIVIDUAL METHODS]'))
                for method, weight in result.individual_weights.items():
                    pred = result.individual_predictions.get(method, 0)
                    self.stdout.write(
                        f'    {method.upper():<20} {pred:>7.2f}  '
                        f'(weight: {weight:.1%}, contribution: {weight*pred:.2f})'
                    )

            # Clinical action
            if result.confidence_level == 'HIGH':
                action = '[ALERT ALLOWED] Can use as automatic alert trigger'
                style = self.style.SUCCESS
            elif result.confidence_level == 'MEDIUM':
                action = '[REVIEW NEEDED] Manual review recommended before alert'
                style = self.style.WARNING
            else:
                action = '[INFO ONLY] No automatic alert, manual assessment required'
                style = self.style.ERROR

            self.stdout.write(style(f'\n  Clinical Action: {action}'))

            return {
                'measurements': measurements,
                'result': result
            }

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  Error forecasting: {e}'))
            return None

    def _print_summary_report(self, batch, total_forecasts):
        """Print summary report."""
        self.stdout.write('\n' + '='*80)
        self.stdout.write(self.style.SUCCESS('TEST SUMMARY'))
        self.stdout.write('='*80)

        if total_forecasts == 0:
            self.stdout.write(self.style.WARNING('No forecasts generated'))
            return

        self.stdout.write(f'Total forecasts: {total_forecasts}')

        # Get batch summary
        if batch.results:
            high = sum(1 for r in batch.results.values() if r.confidence_level == 'HIGH')
            medium = sum(1 for r in batch.results.values() if r.confidence_level == 'MEDIUM')
            low = sum(1 for r in batch.results.values() if r.confidence_level == 'LOW')

            self.stdout.write(f'\nConfidence Distribution:')
            self.stdout.write(self.style.SUCCESS(f'  HIGH ({high}):   {high/total_forecasts*100:.1f}%'))
            self.stdout.write(self.style.WARNING(f'  MEDIUM ({medium}): {medium/total_forecasts*100:.1f}%'))
            self.stdout.write(self.style.ERROR(f'  LOW ({low}):    {low/total_forecasts*100:.1f}%'))

            # Average confidence
            avg_conf = sum(r.confidence for r in batch.results.values()) / len(batch.results)
            self.stdout.write(f'\nAverage Confidence: {avg_conf:.1f}%')

        self.stdout.write('\n' + '='*80)
        self.stdout.write(self.style.SUCCESS('TEST COMPLETE'))
        self.stdout.write('='*80 + '\n')
