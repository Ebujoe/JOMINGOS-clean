"""
INTEGRATION LAYER FOR WEEK 1 COMPONENTS
========================================

Ties together:
- DataQualityValidator
- AuditTrail
- BaselineCalculator
- Django VitalSigns model

Provides:
- Automated validation pipeline
- Audit logging on all vitals
- Baseline calculation and storage
- Quality reporting
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
import logging

from django.db.models import Q, Avg
from patients.models import Patient
from vitals.models import VitalSigns, PatientBaselineData

from .data_quality_validator import DataQualityValidator, QualityCheckResult
from .audit_trail import AuditTrail, AuditAction
from .baseline_calculator import BaselineCalculator, PatientBaseline

logger = logging.getLogger(__name__)


class VitalSignsIntegration:
    """
    Integration layer for vital signs data pipeline.

    Coordinates:
    1. Recording of vitals
    2. Quality validation
    3. Audit logging
    4. Baseline calculation
    5. Report generation
    """

    def __init__(self):
        """Initialize integration components."""
        self.validator = DataQualityValidator()
        self.audit_trail = AuditTrail()
        self.baseline_calculator = BaselineCalculator()
        logger.info("VitalSignsIntegration initialized")

    def record_and_validate_vital(
        self,
        patient_id: int,
        vital_name: str,
        value: float,
        recorded_by_user: Optional[str] = None,
        device_id: Optional[str] = None,
        clinical_context: Optional[str] = None,
    ) -> Tuple[VitalSigns, QualityCheckResult, str]:
        """
        Record vital sign with automatic validation and audit logging.

        Args:
            patient_id: Patient ID
            vital_name: Type of vital (heart_rate, respiratory_rate, etc)
            value: Measured value
            recorded_by_user: User who recorded (optional)
            device_id: Device/sensor ID (optional)
            clinical_context: Clinical notes (optional)

        Returns:
            (vital_record, quality_check, audit_entry_id)
        """

        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            logger.error(f"Patient {patient_id} not found")
            raise ValueError(f"Patient {patient_id} not found")

        # Step 1: Create vital record
        vital_record = VitalSigns.objects.create(
            patient=patient,
            vital_name=vital_name,
            value=Decimal(str(value)),
            recorded_at=datetime.now(),
            recorded_by=recorded_by_user,
        )

        logger.info(f"Created vital record {vital_record.id}: {vital_name}={value}")

        # Step 2: Log recording
        audit_id = self.audit_trail.log_vital_recorded(
            patient_id=patient_id,
            vital_name=vital_name,
            value=value,
            timestamp=vital_record.recorded_at,
            recorded_by_user=recorded_by_user,
            device_id=device_id,
            clinical_context=clinical_context,
        )

        # Step 3: Get patient baseline
        patient_baseline = self._get_or_calculate_baseline(patient_id, vital_name)
        patient_baseline_dict = patient_baseline.to_dict() if patient_baseline else None

        # Step 4: Get recent measurements for context
        previous_measurements = self._get_recent_measurements(patient_id, vital_name, limit=10)

        # Step 5: Validate measurement
        quality_check = self.validator.validate_measurement(
            vital_id=vital_record.id,
            patient_id=patient_id,
            vital_name=vital_name,
            value=value,
            timestamp=vital_record.recorded_at,
            patient_baseline=patient_baseline_dict,
            previous_measurements=previous_measurements,
        )

        # Step 6: Log validation
        validation_audit_id = self.audit_trail.log_validation(
            patient_id=patient_id,
            vital_name=vital_name,
            value=value,
            validation_result={
                'issues': quality_check.issues,
                'warnings': quality_check.warnings,
            },
            quality_score=quality_check.quality_score,
            approved=quality_check.approved,
        )

        # Step 7: Update vital record with validation result
        vital_record.quality_score = quality_check.quality_score
        vital_record.is_approved = quality_check.approved
        vital_record.quality_check_timestamp = quality_check.check_timestamp
        vital_record.quality_check_notes = '\n'.join(quality_check.issues + quality_check.warnings)
        vital_record.save()

        logger.info(
            f"Validated {vital_name}: approved={quality_check.approved}, "
            f"score={quality_check.quality_score:.1f}"
        )

        return vital_record, quality_check, audit_id

    def calculate_patient_baselines(self, patient_id: int) -> Dict[str, PatientBaseline]:
        """
        Calculate baselines for all vitals for a patient.

        Args:
            patient_id: Patient ID

        Returns:
            Dict of vital_name -> PatientBaseline
        """

        # Get all approved measurements for patient
        approved_vitals = VitalSigns.objects.filter(
            patient_id=patient_id,
            is_approved=True,
        ).order_by('recorded_at')

        if not approved_vitals.exists():
            logger.warning(f"No approved vitals for patient {patient_id}")
            return {}

        # Group by vital name
        vital_measurements = {}

        for vital in approved_vitals:
            vital_name = vital.vital_name

            if vital_name not in vital_measurements:
                vital_measurements[vital_name] = []

            vital_measurements[vital_name].append(
                (vital.recorded_at, float(vital.value))
            )

        # Calculate baselines
        baselines = self.baseline_calculator.calculate_all_baselines(
            patient_id=patient_id,
            vital_measurements=vital_measurements,
        )

        # Store in database
        for vital_name, baseline in baselines.items():
            self._store_baseline(patient_id, vital_name, baseline)

        logger.info(f"Calculated {len(baselines)} baselines for patient {patient_id}")

        return baselines

    def _get_or_calculate_baseline(
        self, patient_id: int, vital_name: str
    ) -> Optional[PatientBaseline]:
        """Get baseline from database or calculate if needed."""

        try:
            baseline_record = PatientBaselineData.objects.get(
                patient_id=patient_id,
                vital_name=vital_name,
            )

            return PatientBaseline(
                patient_id=patient_id,
                vital_name=vital_name,
                mean_value=float(baseline_record.mean_value),
                std_dev=float(baseline_record.std_dev),
                min_value=float(baseline_record.min_value),
                max_value=float(baseline_record.max_value),
                median_value=float(baseline_record.median_value),
                percentile_5=float(baseline_record.percentile_5),
                percentile_25=float(baseline_record.percentile_25),
                percentile_75=float(baseline_record.percentile_75),
                percentile_95=float(baseline_record.percentile_95),
                normal_range_lower=float(baseline_record.normal_range_lower),
                normal_range_upper=float(baseline_record.normal_range_upper),
                n_samples=baseline_record.n_samples,
                last_updated=baseline_record.updated_at,
                data_source="database",
            )

        except PatientBaselineData.DoesNotExist:
            return None

    def _store_baseline(
        self, patient_id: int, vital_name: str, baseline: PatientBaseline
    ):
        """Store baseline in database."""

        PatientBaselineData.objects.update_or_create(
            patient_id=patient_id,
            vital_name=vital_name,
            defaults={
                'mean_value': Decimal(str(baseline.mean_value)),
                'std_dev': Decimal(str(baseline.std_dev)),
                'min_value': Decimal(str(baseline.min_value)),
                'max_value': Decimal(str(baseline.max_value)),
                'median_value': Decimal(str(baseline.median_value)),
                'percentile_5': Decimal(str(baseline.percentile_5)),
                'percentile_25': Decimal(str(baseline.percentile_25)),
                'percentile_75': Decimal(str(baseline.percentile_75)),
                'percentile_95': Decimal(str(baseline.percentile_95)),
                'normal_range_lower': Decimal(str(baseline.normal_range_lower)),
                'normal_range_upper': Decimal(str(baseline.normal_range_upper)),
                'n_samples': baseline.n_samples,
                'clinical_notes': baseline.clinical_notes,
            },
        )

        logger.info(f"Stored baseline for {vital_name}: patient {patient_id}")

    def _get_recent_measurements(
        self,
        patient_id: int,
        vital_name: str,
        limit: int = 10,
        hours: int = 168,  # 1 week
    ) -> List[Tuple[datetime, float]]:
        """Get recent measurements for a vital."""

        cutoff = datetime.now() - timedelta(hours=hours)

        measurements = VitalSigns.objects.filter(
            patient_id=patient_id,
            vital_name=vital_name,
            recorded_at__gte=cutoff,
            is_approved=True,
        ).order_by('recorded_at').values_list('recorded_at', 'value')[:limit]

        return [(ts, float(val)) for ts, val in measurements]

    def generate_quality_report(self, patient_id: int) -> Dict:
        """
        Generate quality report for patient.

        Returns:
            Report dict with approval rates, issues, baselines
        """

        all_vitals = VitalSigns.objects.filter(patient_id=patient_id)
        approved = all_vitals.filter(is_approved=True).count()
        rejected = all_vitals.filter(is_approved=False).count()
        total = all_vitals.count()

        # Quality metrics
        avg_quality = (
            all_vitals.filter(quality_score__isnull=False).aggregate(
                avg=Avg('quality_score')
            )['avg'] or 0
        )

        # Issues
        issues = all_vitals.filter(is_approved=False).values_list(
            'vital_name', 'value', 'quality_check_notes'
        )

        # Baselines
        baselines = PatientBaselineData.objects.filter(patient_id=patient_id)

        baseline_summary = {
            baseline.vital_name: {
                'mean': float(baseline.mean_value),
                'std_dev': float(baseline.std_dev),
                'samples': baseline.n_samples,
            }
            for baseline in baselines
        }

        report = {
            'patient_id': patient_id,
            'report_generated': datetime.now().isoformat(),
            'total_measurements': total,
            'approved': approved,
            'rejected': rejected,
            'approval_rate': approved / total if total > 0 else 0,
            'average_quality_score': avg_quality,
            'rejected_measurements': [
                {
                    'vital': issue[0],
                    'value': float(issue[1]),
                    'reason': issue[2],
                }
                for issue in issues
            ],
            'baselines': baseline_summary,
            'weeks_of_data': self._calculate_weeks_of_data(patient_id),
        }

        logger.info(f"Generated quality report for patient {patient_id}")

        return report

    def _calculate_weeks_of_data(self, patient_id: int) -> float:
        """Calculate how many weeks of data patient has."""

        vitals = VitalSigns.objects.filter(
            patient_id=patient_id,
            is_approved=True,
        ).order_by('recorded_at')

        if vitals.count() < 2:
            return 0

        first = vitals.first().recorded_at
        last = vitals.last().recorded_at
        days = (last - first).days
        weeks = days / 7

        return weeks

    def get_audit_log(self, patient_id: int) -> List[Dict]:
        """Get audit log for patient."""
        entries = self.audit_trail.get_patient_audit_log(patient_id)
        return [entry.to_dict() for entry in entries]

    def generate_compliance_report(self, patient_id: int) -> Dict:
        """Generate compliance report for auditing."""
        return self.audit_trail.generate_compliance_report(patient_id)
