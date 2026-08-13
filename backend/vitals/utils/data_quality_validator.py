"""
DATA QUALITY VALIDATION SYSTEM
==============================

Week 1 Deliverable: Automated quality validation for all vital measurements.

Implements:
1. Range validation (physiological bounds)
2. Duplicate detection
3. Temporal validation (chronological order)
4. Outlier detection (>3 SD)
5. Quality scoring
6. Audit logging
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging
import json

logger = logging.getLogger(__name__)


@dataclass
class QualityCheckResult:
    """Result of a single quality check."""
    vital_id: int
    patient_id: int
    vital_name: str
    value: float
    timestamp: datetime

    # Validation results
    passes_range_check: bool
    passes_temporal_check: bool
    passes_outlier_check: bool
    is_duplicate: bool
    quality_score: float  # 0-100

    # Details
    issues: List[str]
    warnings: List[str]
    metadata: Dict

    # Decision
    approved: bool
    rejection_reason: Optional[str]

    # Audit
    check_timestamp: datetime
    checked_by_system: str = "DataQualityValidator"


class DataQualityValidator:
    """
    Comprehensive data quality validation system.

    Philosophy: Catch issues early, document everything, be conservative.
    """

    def __init__(self):
        """Initialize validator with physiological bounds."""

        # Physiological bounds (hard limits - values outside are rejected)
        self.physiological_bounds = {
            'heart_rate': {
                'min': 20,
                'max': 180,
                'normal_range': (60, 100),
            },
            'respiratory_rate': {
                'min': 5,
                'max': 50,
                'normal_range': (12, 20),
            },
            'oxygen_saturation': {
                'min': 50,  # Allow lower for acute patients
                'max': 100,
                'normal_range': (95, 100),
            },
            'temperature': {
                'min': 35.0,
                'max': 42.0,
                'normal_range': (36.5, 37.5),
            },
            'bp_systolic': {
                'min': 60,
                'max': 250,
                'normal_range': (90, 140),
            },
            'bp_diastolic': {
                'min': 40,
                'max': 150,
                'normal_range': (60, 90),
            },
            'blood_glucose': {
                'min': 40,
                'max': 600,
                'normal_range': (70, 100),
            },
        }

        logger.info("DataQualityValidator initialized")

    def validate_measurement(
        self,
        vital_id: int,
        patient_id: int,
        vital_name: str,
        value: float,
        timestamp: datetime,
        patient_baseline: Optional[Dict] = None,
        previous_measurements: Optional[List[Tuple[datetime, float]]] = None,
    ) -> QualityCheckResult:
        """
        Validate a single vital measurement.

        Args:
            vital_id: Unique measurement ID
            patient_id: Patient ID
            vital_name: Type of vital (heart_rate, etc)
            value: Measured value
            timestamp: When measurement was taken
            patient_baseline: Patient's historical baseline (mean, std dev)
            previous_measurements: Recent measurements for comparison

        Returns:
            QualityCheckResult with validation details
        """

        logger.info(f"Validating {vital_name}={value} for patient {patient_id}")

        issues = []
        warnings = []

        # Check 1: Range validation
        passes_range, range_issues, range_warnings = self._check_range(
            vital_name, value
        )
        issues.extend(range_issues)
        warnings.extend(range_warnings)

        # Check 2: Temporal validation
        passes_temporal, temporal_issues = self._check_temporal(
            timestamp, previous_measurements
        )
        issues.extend(temporal_issues)

        # Check 3: Outlier detection
        passes_outlier, outlier_issues, outlier_warnings = self._check_outlier(
            vital_name, value, patient_baseline, previous_measurements
        )
        issues.extend(outlier_issues)
        warnings.extend(outlier_warnings)

        # Check 4: Duplicate detection
        is_duplicate, duplicate_issues = self._check_duplicate(
            vital_name, value, timestamp, previous_measurements
        )
        issues.extend(duplicate_issues)

        # Calculate quality score
        quality_score = self._calculate_quality_score(
            passes_range, passes_temporal, passes_outlier, is_duplicate, len(warnings)
        )

        # Approval decision
        approved = passes_range and passes_temporal and (not is_duplicate)
        rejection_reason = None

        if not passes_range:
            rejection_reason = "Value outside physiological bounds"
        elif is_duplicate:
            rejection_reason = "Duplicate measurement detected"
        elif not passes_temporal:
            rejection_reason = "Invalid timestamp"

        result = QualityCheckResult(
            vital_id=vital_id,
            patient_id=patient_id,
            vital_name=vital_name,
            value=value,
            timestamp=timestamp,
            passes_range_check=passes_range,
            passes_temporal_check=passes_temporal,
            passes_outlier_check=passes_outlier,
            is_duplicate=is_duplicate,
            quality_score=quality_score,
            issues=issues,
            warnings=warnings,
            metadata={
                'baseline': patient_baseline,
                'previous_count': len(previous_measurements) if previous_measurements else 0,
            },
            approved=approved,
            rejection_reason=rejection_reason,
            check_timestamp=datetime.now(),
        )

        logger.info(f"Validation result: approved={approved}, score={quality_score:.1f}")

        return result

    def _check_range(self, vital_name: str, value: float) -> Tuple[bool, List[str], List[str]]:
        """Check if value is within physiological bounds."""

        bounds = self.physiological_bounds.get(vital_name)
        if not bounds:
            return True, [], []  # Unknown vital, assume ok

        issues = []
        warnings = []

        if value < bounds['min']:
            issues.append(f"Value {value} below minimum {bounds['min']}")
            return False, issues, warnings

        if value > bounds['max']:
            issues.append(f"Value {value} exceeds maximum {bounds['max']}")
            return False, issues, warnings

        # Check against normal range
        normal_min, normal_max = bounds['normal_range']
        if value < normal_min:
            warnings.append(f"Value {value} below normal range ({normal_min}-{normal_max})")
        elif value > normal_max:
            warnings.append(f"Value {value} above normal range ({normal_min}-{normal_max})")

        return True, issues, warnings

    def _check_temporal(
        self, timestamp: datetime, previous_measurements: Optional[List]
    ) -> Tuple[bool, List[str]]:
        """Check timestamp is valid and chronologically ordered."""

        issues = []

        # Check 1: Not in future
        if timestamp > datetime.now():
            issues.append(f"Timestamp {timestamp} is in the future")
            return False, issues

        # Check 2: Not too old (>1 year)
        one_year_ago = datetime.now() - timedelta(days=365)
        if timestamp < one_year_ago:
            issues.append(f"Timestamp {timestamp} is >1 year old")
            return False, issues

        # Check 3: Chronological order with previous
        if previous_measurements and len(previous_measurements) > 0:
            last_timestamp = previous_measurements[-1][0]
            if timestamp < last_timestamp:
                issues.append(f"Timestamp {timestamp} is before previous {last_timestamp}")
                return False, issues

        return True, issues

    def _check_outlier(
        self, vital_name: str, value: float,
        patient_baseline: Optional[Dict],
        previous_measurements: Optional[List]
    ) -> Tuple[bool, List[str], List[str]]:
        """Detect outliers (>3 SD from baseline or recent history)."""

        issues = []
        warnings = []

        if not patient_baseline:
            # Can't check without baseline
            return True, issues, warnings

        mean = patient_baseline.get('mean_value')
        std_dev = patient_baseline.get('std_dev', 0)

        if not mean or std_dev == 0:
            return True, issues, warnings

        # Z-score
        z_score = (value - mean) / std_dev

        if abs(z_score) > 3:
            warnings.append(f"Potential outlier: Z-score = {z_score:.2f} (>3 SD from baseline)")
            # Still allow it (user can review), but flag it

        if abs(z_score) > 4:
            issues.append(f"Extreme outlier: Z-score = {z_score:.2f} (>4 SD from baseline)")
            return False, issues, warnings

        return True, issues, warnings

    def _check_duplicate(
        self, vital_name: str, value: float,
        timestamp: datetime,
        previous_measurements: Optional[List]
    ) -> Tuple[bool, List[str]]:
        """Detect duplicate measurements (same value within 10 minutes)."""

        issues = []

        if not previous_measurements or len(previous_measurements) == 0:
            return False, issues

        # Check last 3 measurements
        for prev_timestamp, prev_value in previous_measurements[-3:]:
            time_diff = (timestamp - prev_timestamp).total_seconds() / 60

            # Same value within 10 minutes = likely duplicate
            if abs(prev_value - value) < 0.1 and time_diff < 10:
                issues.append(
                    f"Duplicate: same value {value} recorded {time_diff:.0f} min ago"
                )
                return True, issues

        return False, issues

    def _calculate_quality_score(
        self, range_ok: bool, temporal_ok: bool,
        outlier_ok: bool, is_duplicate: bool, warning_count: int
    ) -> float:
        """Calculate 0-100 quality score."""

        score = 100.0

        if not range_ok:
            score -= 50
        if not temporal_ok:
            score -= 50
        if is_duplicate:
            score -= 30
        if not outlier_ok:
            score -= 10

        # Penalize warnings
        score -= min(warning_count * 5, 15)

        return max(score, 0.0)

    def batch_validate(
        self,
        measurements: List[Dict],
        patient_baselines: Dict[int, Dict] = None,
        patient_history: Dict[int, List] = None,
    ) -> List[QualityCheckResult]:
        """
        Validate multiple measurements.

        Args:
            measurements: List of measurement dicts with:
                - vital_id, patient_id, vital_name, value, timestamp
            patient_baselines: Dict of patient_id -> baseline stats
            patient_history: Dict of patient_id -> list of (timestamp, value)

        Returns:
            List of QualityCheckResult objects
        """

        results = []

        for measurement in measurements:
            patient_id = measurement['patient_id']

            baseline = patient_baselines.get(patient_id) if patient_baselines else None
            history = patient_history.get(patient_id) if patient_history else None

            result = self.validate_measurement(
                vital_id=measurement.get('vital_id'),
                patient_id=patient_id,
                vital_name=measurement['vital_name'],
                value=measurement['value'],
                timestamp=measurement['timestamp'],
                patient_baseline=baseline,
                previous_measurements=history,
            )

            results.append(result)

        return results

    def generate_validation_report(self, results: List[QualityCheckResult]) -> Dict:
        """Generate summary report of validation results."""

        total = len(results)
        approved = sum(1 for r in results if r.approved)
        rejected = sum(1 for r in results if not r.approved)
        duplicates = sum(1 for r in results if r.is_duplicate)
        outliers = sum(1 for r in results if not r.passes_outlier_check)

        avg_quality = sum(r.quality_score for r in results) / total if total > 0 else 0

        return {
            'timestamp': datetime.now().isoformat(),
            'total_measurements': total,
            'approved': approved,
            'rejected': rejected,
            'approval_rate': approved / total if total > 0 else 0,
            'duplicates_detected': duplicates,
            'outliers_detected': outliers,
            'average_quality_score': avg_quality,
            'rejected_details': [
                {
                    'vital': r.vital_name,
                    'value': r.value,
                    'reason': r.rejection_reason,
                }
                for r in results if not r.approved
            ],
        }
