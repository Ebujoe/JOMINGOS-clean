"""
Django management command for Week 3 forecasting operations.

Usage:
    python manage.py generate_forecasts                    # Generate for all patients
    python manage.py generate_forecasts --patient=1        # Specific patient
    python manage.py generate_forecasts --vital=heart_rate # Specific vital type
    python manage.py generate_forecasts --store            # Store in database
    python manage.py generate_forecasts --backtest         # Run backtesting
"""

from django.core.management.base import BaseCommand
from patients.models import Patient
from vitals.models import VitalSigns
from vitals.utils.forecasting_service import ForecastingService, BacktestingService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Generate forecasts using RobustForecastingEngine"

    def add_arguments(self, parser):
        parser.add_argument(
            '--patient',
            type=int,
            help='Specific patient ID',
        )
        parser.add_argument(
            '--vital',
            type=str,
            help='Specific vital name (e.g., heart_rate)',
        )
        parser.add_argument(
            '--horizon',
            type=int,
            default=24,
            help='Forecast horizon in hours (default: 24)',
        )
        parser.add_argument(
            '--store',
            action='store_true',
            help='Store forecasts in database',
        )
        parser.add_argument(
            '--backtest',
            action='store_true',
            help='Run backtesting analysis',
        )
        parser.add_argument(
            '--all-horizons',
            action='store_true',
            help='Generate for all standard horizons (24, 168, 336, 720)',
        )

    def handle(self, *args, **options):
        """Main command handler."""

        self.stdout.write(self.style.SUCCESS(f"\n{'='*70}"))
        self.stdout.write(self.style.SUCCESS("FORECASTING SERVICE - WEEK 3"))
        self.stdout.write(self.style.SUCCESS(f"{'='*70}\n"))

        forecasting_service = ForecastingService()

        # Determine patients
        if options['patient']:
            patients = Patient.objects.filter(id=options['patient'])
        else:
            patients = Patient.objects.all()

        if not patients.exists():
            self.stdout.write(self.style.ERROR("No patients found"))
            return

        # Standard horizons
        horizons = [24, 168, 336, 720] if options['all_horizons'] else [options['horizon']]

        total_forecasts = 0
        total_high_confidence = 0

        for patient in patients:
            self.stdout.write(f"\n{'='*70}")
            self.stdout.write(f"Patient: {patient.get_full_name()} (ID: {patient.id})")
            self.stdout.write(f"{'='*70}\n")

            # Get vital types
            vitals_qs = VitalSigns.objects.filter(patient=patient, is_approved=True)

            if options['vital']:
                vitals_qs = vitals_qs.filter(vital_name=options['vital'])

            vital_types = vitals_qs.values_list('vital_name', flat=True).distinct()

            if not vital_types:
                self.stdout.write(self.style.WARNING("  No approved vitals found"))
                continue

            for vital_name in vital_types:
                self.stdout.write(f"\n{vital_name.replace('_', ' ').title()}")
                self.stdout.write("-" * 50)

                for horizon in horizons:
                    forecast = forecasting_service.generate_forecast_for_patient(
                        patient_id=patient.id,
                        vital_name=vital_name,
                        horizon_hours=horizon,
                    )

                    if forecast.get('status') != 'success':
                        self.stdout.write(
                            self.style.WARNING(
                                f"  {horizon}h: {forecast.get('message', 'Failed')}"
                            )
                        )
                        continue

                    # Display forecast
                    conf = forecast['confidence_score']
                    reliability = forecast['forecast_reliability']
                    value = forecast['forecast_value']

                    # Confidence color coding
                    if conf >= 70:
                        conf_style = self.style.SUCCESS
                        conf_icon = "✓"
                    elif conf >= 40:
                        conf_style = self.style.WARNING
                        conf_icon = "⚠"
                    else:
                        conf_style = self.style.ERROR
                        conf_icon = "✗"

                    self.stdout.write(
                        f"  {horizon:3d}h: {value:6.1f} "
                        f"({conf_style(f'{conf_icon} {conf:.0f}%')}) "
                        f"[{reliability}]"
                    )

                    # Store if requested
                    if options['store']:
                        forecasting_service.store_forecast(patient.id, forecast)

                    total_forecasts += 1
                    if conf >= 70:
                        total_high_confidence += 1

            # Backtest if requested
            if options['backtest']:
                self.stdout.write(f"\n{'='*70}")
                self.stdout.write("BACKTESTING RESULTS")
                self.stdout.write(f"{'='*70}\n")

                for vital_name in vital_types:
                    self.stdout.write(f"{vital_name.replace('_', ' ').title()}")

                    results = BacktestingService.backtest_all_horizons(
                        patient_id=patient.id,
                        vital_name=vital_name,
                    )

                    for horizon_key, result in results.items():
                        if result.get('status') == 'success':
                            mae = result['accuracy_metrics']['mae']
                            rmse = result['accuracy_metrics']['rmse']
                            mape = result['accuracy_metrics']['mape']

                            self.stdout.write(
                                f"  {horizon_key:4s}: MAE={mae:6.2f}, RMSE={rmse:6.2f}, MAPE={mape:5.1f}%"
                            )
                        else:
                            self.stdout.write(f"  {horizon_key:4s}: {result.get('message')}")

                    self.stdout.write()

        # Summary
        self.stdout.write(f"\n{'='*70}")
        self.stdout.write(self.style.SUCCESS("FORECASTING COMPLETE"))
        self.stdout.write(f"{'='*70}\n")

        self.stdout.write(f"Total forecasts generated: {total_forecasts}")
        self.stdout.write(f"High confidence (70%+): {total_high_confidence}")

        if total_forecasts > 0:
            pct_high = (total_high_confidence / total_forecasts * 100)
            self.stdout.write(f"Percentage high confidence: {pct_high:.1f}%")

        if options['store']:
            self.stdout.write(
                self.style.SUCCESS("\n✓ All forecasts stored in database")
            )

        self.stdout.write(
            self.style.SUCCESS(
                "\nReady for backtesting and validation (Week 3-4)"
            )
        )
