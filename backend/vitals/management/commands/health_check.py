"""
System Health Check CLI

Quick verification of system status across all deployment tiers.
Provides instant readiness assessment without side effects.

Usage:
    python manage.py health_check
    python manage.py health_check --verbose
    python manage.py health_check --json
    python manage.py health_check --wave1
    python manage.py health_check --wave2
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import connections
from django.db.utils import OperationalError
from patients.models import Patient
from vitals.models import VitalSigns, PatientForecast
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)


class HealthStatus:
    """Track health status with weighted scoring."""

    def __init__(self):
        self.checks = {}
        self.critical_failures = []
        self.warnings = []

    def add_check(self, name, status, weight=1.0, details=None):
        """Add a health check result (True=pass, False=fail)."""
        self.checks[name] = {
            'status': status,
            'weight': weight,
            'details': details or '',
        }
        if not status and weight >= 1.0:
            self.critical_failures.append(name)
        elif not status:
            self.warnings.append(name)

    def get_score(self):
        """Calculate weighted health score (0-100)."""
        if not self.checks:
            return 0

        total_weight = sum(c['weight'] for c in self.checks.values())
        passed_weight = sum(
            c['weight'] for c in self.checks.values() if c['status']
        )

        if total_weight == 0:
            return 0

        return int((passed_weight / total_weight) * 100)

    def get_status(self):
        """Get overall status indicator."""
        score = self.get_score()
        if score >= 90:
            return 'HEALTHY'
        elif score >= 70:
            return 'DEGRADED'
        elif score >= 50:
            return 'CRITICAL'
        else:
            return 'OFFLINE'

    def to_dict(self):
        """Export as dictionary."""
        return {
            'timestamp': timezone.now().isoformat(),
            'status': self.get_status(),
            'score': self.get_score(),
            'checks': self.checks,
            'critical_failures': self.critical_failures,
            'warnings': self.warnings,
        }


class Command(BaseCommand):
    help = "Check system health and readiness"

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed check information',
        )
        parser.add_argument(
            '--json',
            action='store_true',
            help='Output as JSON',
        )
        parser.add_argument(
            '--wave1',
            action='store_true',
            help='Check Wave 1 pilot deployment status',
        )
        parser.add_argument(
            '--wave2',
            action='store_true',
            help='Check Wave 2 expansion readiness',
        )

    def handle(self, *args, **options):
        verbose = options.get('verbose')
        output_json = options.get('json')
        check_wave1 = options.get('wave1')
        check_wave2 = options.get('wave2')

        health = HealthStatus()

        # Always run core checks
        self._check_infrastructure(health)
        self._check_data_availability(health)
        self._check_models_and_forecasts(health)

        # Optional wave-specific checks
        if check_wave1:
            self._check_wave1_status(health)
        if check_wave2:
            self._check_wave2_readiness(health)

        # If no specific wave requested, check both
        if not check_wave1 and not check_wave2:
            self._check_wave1_status(health)
            self._check_wave2_readiness(health)

        # Output results
        if output_json:
            self._output_json(health)
        else:
            self._output_human(health, verbose)

    def _check_infrastructure(self, health):
        """Check core infrastructure components."""
        # Database connectivity
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            health.add_check(
                'Database Connectivity',
                True,
                weight=2.0,
                details='PostgreSQL responding'
            )
        except OperationalError as e:
            health.add_check(
                'Database Connectivity',
                False,
                weight=2.0,
                details=f'Error: {str(e)[:50]}'
            )

        # Django ORM functionality
        try:
            Patient.objects.count()
            health.add_check(
                'Django ORM',
                True,
                weight=1.5,
                details='ORM queries working'
            )
        except Exception as e:
            health.add_check(
                'Django ORM',
                False,
                weight=1.5,
                details=f'Error: {str(e)[:50]}'
            )

        # Table accessibility
        try:
            tables_exist = (
                Patient.objects.count() >= 0 and
                VitalSigns.objects.count() >= 0 and
                PatientForecast.objects.count() >= 0
            )
            health.add_check(
                'Core Tables Accessible',
                tables_exist,
                weight=1.5,
                details='patients, vitals, forecasts tables OK'
            )
        except Exception as e:
            health.add_check(
                'Core Tables Accessible',
                False,
                weight=1.5,
                details=f'Error: {str(e)[:50]}'
            )

    def _check_data_availability(self, health):
        """Check patient data and vital signs availability."""
        try:
            patient_count = Patient.objects.count()
            health.add_check(
                'Patient Data Available',
                patient_count > 0,
                weight=1.5,
                details=f'{patient_count} patients in system'
            )
        except Exception:
            health.add_check(
                'Patient Data Available',
                False,
                weight=1.5,
                details='Cannot query patients'
            )

        try:
            vital_count = VitalSigns.objects.count()
            health.add_check(
                'Vital Signs Recorded',
                vital_count > 100,
                weight=1.0,
                details=f'{vital_count} vital measurements'
            )
        except Exception:
            health.add_check(
                'Vital Signs Recorded',
                False,
                weight=1.0,
                details='Cannot query vital signs'
            )

        # Data recency (should have vitals from last 24 hours)
        try:
            cutoff = timezone.now() - timedelta(hours=24)
            recent_vitals = VitalSigns.objects.filter(recorded_at__gte=cutoff).count()
            is_recent = recent_vitals > 0
            health.add_check(
                'Recent Vital Signs (24h)',
                is_recent,
                weight=1.0,
                details=f'{recent_vitals} measurements in last 24h'
            )
        except Exception:
            health.add_check(
                'Recent Vital Signs (24h)',
                False,
                weight=1.0,
                details='Cannot check recency'
            )

    def _check_models_and_forecasts(self, health):
        """Check forecasting models and predictions."""
        try:
            forecast_count = PatientForecast.objects.count()
            health.add_check(
                'Forecasts Generated',
                forecast_count > 0,
                weight=1.5,
                details=f'{forecast_count} forecasts in database'
            )
        except Exception:
            health.add_check(
                'Forecasts Generated',
                False,
                weight=1.5,
                details='Cannot query forecasts'
            )

        # Forecast recency (should have forecasts from last 24 hours)
        try:
            cutoff = timezone.now() - timedelta(hours=24)
            recent_forecasts = PatientForecast.objects.filter(
                forecast_timestamp__gte=cutoff
            ).count()
            is_fresh = recent_forecasts > 0
            health.add_check(
                'Recent Forecasts (24h)',
                is_fresh,
                weight=1.0,
                details=f'{recent_forecasts} forecasts generated in last 24h'
            )
        except Exception:
            health.add_check(
                'Recent Forecasts (24h)',
                False,
                weight=1.0,
                details='Cannot check forecast recency'
            )

        # Model framework availability
        try:
            from vitals.utils.model_training import ModelTrainer
            ModelTrainer()
            health.add_check(
                'Model Training Framework',
                True,
                weight=1.0,
                details='ModelTrainer class available'
            )
        except Exception as e:
            health.add_check(
                'Model Training Framework',
                False,
                weight=1.0,
                details=f'Error: {str(e)[:50]}'
            )

    def _check_wave1_status(self, health):
        """Check Wave 1 pilot deployment status."""
        # Wave 1 pilot patients
        wave1_patients = [
            ('Richard', 'Anderson'),
            ('James', 'Brown'),
            ('Michael', 'Brown'),
            ('James', 'Wilson'),
        ]

        found_count = 0
        for first_name, last_name in wave1_patients:
            try:
                patient = Patient.objects.get(
                    first_name=first_name,
                    last_name=last_name
                )
                found_count += 1
            except Patient.DoesNotExist:
                pass

        health.add_check(
            'Wave 1 Pilot Patients',
            found_count == 4,
            weight=1.5,
            details=f'{found_count}/4 pilot patients found'
        )

        # Wave 1 forecast coverage
        try:
            wave1_patient_ids = Patient.objects.filter(
                first_name__in=['Richard', 'James', 'Michael']
            ).values_list('id', flat=True)

            forecasts = PatientForecast.objects.filter(
                patient_id__in=wave1_patient_ids
            ).count()

            expected_min = 20  # At least some forecasts
            health.add_check(
                'Wave 1 Forecasts',
                forecasts >= expected_min,
                weight=1.0,
                details=f'{forecasts} forecasts for Wave 1 patients'
            )
        except Exception:
            health.add_check(
                'Wave 1 Forecasts',
                False,
                weight=1.0,
                details='Cannot query Wave 1 forecasts'
            )

    def _check_wave2_readiness(self, health):
        """Check Wave 2 expansion preparation status."""
        try:
            total_patients = Patient.objects.count()
            wave2_ready = total_patients >= 50

            health.add_check(
                'Wave 2 Patient Base',
                wave2_ready,
                weight=1.5,
                details=f'{total_patients} total patients (target: 50-100)'
            )
        except Exception:
            health.add_check(
                'Wave 2 Patient Base',
                False,
                weight=1.5,
                details='Cannot query patient count'
            )

        try:
            vital_count = VitalSigns.objects.count()
            wave2_data_ready = vital_count >= 500

            health.add_check(
                'Wave 2 Data Volume',
                wave2_data_ready,
                weight=1.0,
                details=f'{vital_count} vital measurements (target: 500+)'
            )
        except Exception:
            health.add_check(
                'Wave 2 Data Volume',
                False,
                weight=1.0,
                details='Cannot query vital signs count'
            )

        try:
            forecast_count = PatientForecast.objects.count()
            wave2_forecast_ready = forecast_count >= 100

            health.add_check(
                'Wave 2 Forecast Capacity',
                wave2_forecast_ready,
                weight=1.0,
                details=f'{forecast_count} forecasts ready (target: 100+)'
            )
        except Exception:
            health.add_check(
                'Wave 2 Forecast Capacity',
                False,
                weight=1.0,
                details='Cannot query forecast count'
            )

    def _output_human(self, health, verbose):
        """Output human-readable health report."""
        status = health.get_status()
        score = health.get_score()

        # Status indicator
        if status == 'HEALTHY':
            status_symbol = "[OK]"
            status_style = self.style.SUCCESS
        elif status == 'DEGRADED':
            status_symbol = "[WARN]"
            status_style = self.style.WARNING
        elif status == 'CRITICAL':
            status_symbol = "[FAIL]"
            status_style = self.style.ERROR
        else:
            status_symbol = "[OFFLINE]"
            status_style = self.style.ERROR

        self.stdout.write(self.style.SUCCESS(f"\n{'='*70}"))
        self.stdout.write(self.style.SUCCESS("SYSTEM HEALTH CHECK"))
        self.stdout.write(self.style.SUCCESS(f"{'='*70}\n"))

        self.stdout.write(status_style(f"{status_symbol} Status: {status}"))
        self.stdout.write(f"Health Score: {score}/100")
        self.stdout.write(f"Timestamp: {timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")

        # Health meter
        meter_length = 40
        filled = int((score / 100) * meter_length)
        meter = "[" + "=" * filled + "-" * (meter_length - filled) + "]"
        self.stdout.write(f"Progress: {meter}\n")

        # Individual checks
        self.stdout.write("Component Status:")
        self.stdout.write("-" * 70)

        for check_name, check_data in health.checks.items():
            status_str = "[OK]" if check_data['status'] else "[FAIL]"
            style = self.style.SUCCESS if check_data['status'] else self.style.ERROR
            details = f" — {check_data['details']}" if check_data['details'] else ""
            self.stdout.write(style(f"  {status_str} {check_name}{details}"))

        # Summary
        self.stdout.write(f"\n{'='*70}")
        if health.critical_failures:
            self.stdout.write(
                self.style.ERROR(f"Critical Issues: {', '.join(health.critical_failures)}")
            )
        if health.warnings:
            self.stdout.write(
                self.style.WARNING(f"Warnings: {', '.join(health.warnings)}")
            )

        if not health.critical_failures and not health.warnings:
            self.stdout.write(
                self.style.SUCCESS("All systems operational")
            )

        self.stdout.write(f"{'='*70}\n")

        # Readiness assessment
        if score >= 90:
            self.stdout.write(
                self.style.SUCCESS("[OK] READY FOR PRODUCTION DEPLOYMENT")
            )
        elif score >= 70:
            self.stdout.write(
                self.style.WARNING("[WARN] Proceed with caution - some issues detected")
            )
        else:
            self.stdout.write(
                self.style.ERROR("[FAIL] NOT READY - address critical issues first")
            )

        self.stdout.write()

    def _output_json(self, health):
        """Output machine-readable JSON health report."""
        output = health.to_dict()
        self.stdout.write(json.dumps(output, indent=2))
