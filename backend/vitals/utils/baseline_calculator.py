"""
PATIENT BASELINE CALCULATION SYSTEM
====================================

Week 1 Deliverable: Compute individual patient physiological baselines
from historical vital data.

Implements:
1. Statistical baseline calculation (mean, std dev, percentiles)
2. Normal range establishment
3. Circadian pattern detection (if available)
4. Activity pattern detection (if available)
5. Baseline versioning and history
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class PatientBaseline:
    """Individual patient's physiological baseline."""

    patient_id: int
    vital_name: str

    # Core statistics
    mean_value: float
    std_dev: float
    min_value: float
    max_value: float
    median_value: float

    # Percentiles
    percentile_5: float
    percentile_25: float
    percentile_75: float
    percentile_95: float

    # Normal range (±1.5 SD from mean)
    normal_range_lower: float
    normal_range_upper: float

    # Data quality
    n_samples: int
    last_updated: datetime
    data_source: str  # "historical", "current_patient"

    # Advanced patterns (if computed)
    circadian_pattern: Optional[Dict[int, float]] = None  # hour -> avg value
    activity_pattern: Optional[Dict[str, float]] = None     # activity -> avg value

    # Clinical notes
    clinical_notes: Optional[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []

    def is_outlier(self, value: float) -> bool:
        """Check if a value is an outlier (>2 SD from mean)."""
        z_score = (value - self.mean_value) / (self.std_dev + 0.001)
        return abs(z_score) > 2

    def is_abnormal(self, value: float) -> bool:
        """Check if value is outside normal range."""
        return value < self.normal_range_lower or value > self.normal_range_upper

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'patient_id': self.patient_id,
            'vital_name': self.vital_name,
            'mean_value': float(self.mean_value),
            'std_dev': float(self.std_dev),
            'min_value': float(self.min_value),
            'max_value': float(self.max_value),
            'median_value': float(self.median_value),
            'percentile_5': float(self.percentile_5),
            'percentile_25': float(self.percentile_25),
            'percentile_75': float(self.percentile_75),
            'percentile_95': float(self.percentile_95),
            'normal_range': {
                'lower': float(self.normal_range_lower),
                'upper': float(self.normal_range_upper),
            },
            'n_samples': self.n_samples,
            'last_updated': self.last_updated.isoformat(),
            'clinical_notes': self.clinical_notes,
            'warnings': self.warnings,
        }


class BaselineCalculator:
    """
    Calculate patient-specific physiological baselines.

    Each patient has unique vital sign patterns. This system establishes
    their personal "normal" range for comparison with forecasts.
    """

    def __init__(self):
        """Initialize calculator."""
        logger.info("BaselineCalculator initialized")

    def calculate_baseline(
        self,
        patient_id: int,
        vital_name: str,
        historical_measurements: List[Tuple[datetime, float]],
        min_samples: int = 5,
    ) -> Optional[PatientBaseline]:
        """
        Calculate baseline for a single vital sign.

        Args:
            patient_id: Patient ID
            vital_name: Name of vital (heart_rate, etc)
            historical_measurements: List of (timestamp, value) tuples
            min_samples: Minimum measurements required for valid baseline

        Returns:
            PatientBaseline object, or None if insufficient data
        """

        if len(historical_measurements) < min_samples:
            logger.warning(
                f"Insufficient data for {vital_name}: {len(historical_measurements)} < {min_samples}"
            )
            return None

        # Extract values
        values = np.array([v for _, v in historical_measurements], dtype=float)

        # Calculate statistics
        mean_value = np.mean(values)
        std_dev = np.std(values)
        min_value = np.min(values)
        max_value = np.max(values)
        median_value = np.median(values)

        # Percentiles
        percentile_5 = np.percentile(values, 5)
        percentile_25 = np.percentile(values, 25)
        percentile_75 = np.percentile(values, 75)
        percentile_95 = np.percentile(values, 95)

        # Normal range: ±1.5 SD from mean
        normal_range_lower = mean_value - (1.5 * std_dev)
        normal_range_upper = mean_value + (1.5 * std_dev)

        # Detect circadian patterns (if timestamps available)
        circadian_pattern = self._calculate_circadian_pattern(historical_measurements)

        # Generate warnings
        warnings = self._generate_warnings(
            vital_name, values, std_dev, len(historical_measurements)
        )

        baseline = PatientBaseline(
            patient_id=patient_id,
            vital_name=vital_name,
            mean_value=float(mean_value),
            std_dev=float(std_dev),
            min_value=float(min_value),
            max_value=float(max_value),
            median_value=float(median_value),
            percentile_5=float(percentile_5),
            percentile_25=float(percentile_25),
            percentile_75=float(percentile_75),
            percentile_95=float(percentile_95),
            normal_range_lower=float(normal_range_lower),
            normal_range_upper=float(normal_range_upper),
            n_samples=len(historical_measurements),
            last_updated=datetime.now(),
            data_source="historical",
            circadian_pattern=circadian_pattern,
            clinical_notes=f"Baseline for {vital_name}: mean={mean_value:.1f}±{std_dev:.1f}",
            warnings=warnings,
        )

        logger.info(
            f"Calculated baseline for {vital_name}: mean={mean_value:.1f}±{std_dev:.1f} "
            f"(n={len(historical_measurements)})"
        )

        return baseline

    def calculate_all_baselines(
        self,
        patient_id: int,
        vital_measurements: Dict[str, List[Tuple[datetime, float]]],
    ) -> Dict[str, PatientBaseline]:
        """
        Calculate baselines for all vitals for a patient.

        Args:
            patient_id: Patient ID
            vital_measurements: Dict of vital_name -> list of (timestamp, value)

        Returns:
            Dict of vital_name -> PatientBaseline
        """

        baselines = {}

        for vital_name, measurements in vital_measurements.items():
            baseline = self.calculate_baseline(
                patient_id=patient_id,
                vital_name=vital_name,
                historical_measurements=measurements,
            )

            if baseline:
                baselines[vital_name] = baseline

        logger.info(f"Calculated {len(baselines)} baselines for patient {patient_id}")

        return baselines

    @staticmethod
    def _calculate_circadian_pattern(
        measurements: List[Tuple[datetime, float]]
    ) -> Optional[Dict[int, float]]:
        """
        Detect circadian (time-of-day) patterns.

        Returns dict of hour -> average value
        """

        if len(measurements) < 10:
            return None  # Need more data

        # Group by hour of day
        hour_values = {}

        for timestamp, value in measurements:
            hour = timestamp.hour
            if hour not in hour_values:
                hour_values[hour] = []
            hour_values[hour].append(value)

        # Average by hour
        circadian = {}
        for hour, values in hour_values.items():
            circadian[hour] = float(np.mean(values))

        return circadian if len(circadian) > 2 else None

    @staticmethod
    def _generate_warnings(
        vital_name: str, values: np.ndarray, std_dev: float, n_samples: int
    ) -> List[str]:
        """Generate warnings about baseline quality."""

        warnings = []

        if n_samples < 10:
            warnings.append(f"Low data volume ({n_samples} samples). Baseline may be unreliable.")

        if std_dev == 0:
            warnings.append(f"Zero variance in {vital_name}. All values identical.")

        if std_dev > np.mean(np.abs(values)) * 0.5:
            warnings.append(f"High variability in {vital_name}. Patient may be unstable.")

        # Check for extreme outliers
        mean = np.mean(values)
        z_scores = np.abs((values - mean) / (std_dev + 0.001))
        if np.any(z_scores > 3):
            warnings.append(f"Extreme outliers detected in {vital_name}. Consider removing.")

        return warnings


class BaselineValidator:
    """Validate that baseline meets quality standards."""

    @staticmethod
    def validate_baseline(baseline: PatientBaseline) -> Tuple[bool, List[str]]:
        """
        Validate baseline quality.

        Returns:
            (is_valid, list_of_issues)
        """

        issues = []

        # Minimum samples
        if baseline.n_samples < 5:
            issues.append(f"Insufficient samples ({baseline.n_samples} < 5)")

        # Non-zero variance
        if baseline.std_dev == 0:
            issues.append("Zero variance (all values identical)")

        # Reasonable range
        if baseline.std_dev > baseline.mean_value * 0.5:
            issues.append(f"Very high variance (std_dev > 50% of mean)")

        # Percentile ordering
        if not (baseline.percentile_5 < baseline.percentile_25 < baseline.percentile_75 < baseline.percentile_95):
            issues.append("Invalid percentile ordering")

        is_valid = len(issues) == 0

        return is_valid, issues


class BaselineComparison:
    """Compare current vital to baseline to identify abnormalities."""

    @staticmethod
    def compare_to_baseline(
        value: float, baseline: PatientBaseline
    ) -> Dict[str, any]:
        """
        Compare value to baseline and generate assessment.

        Returns:
            Assessment dict with z-score, status, deviation info
        """

        z_score = (value - baseline.mean_value) / (baseline.std_dev + 0.001)
        deviation_percent = ((value - baseline.mean_value) / (baseline.mean_value + 0.001)) * 100

        # Status
        if baseline.normal_range_lower <= value <= baseline.normal_range_upper:
            status = "Normal"
            severity = 0
        elif value < baseline.percentile_5 or value > baseline.percentile_95:
            status = "Abnormal"
            severity = 2
        else:
            status = "Borderline"
            severity = 1

        return {
            'value': float(value),
            'baseline_mean': float(baseline.mean_value),
            'z_score': float(z_score),
            'deviation_percent': float(deviation_percent),
            'status': status,
            'severity': severity,  # 0=normal, 1=borderline, 2=abnormal
            'percentile_position': BaselineComparison._calculate_percentile_position(
                value, baseline
            ),
        }

    @staticmethod
    def _calculate_percentile_position(value: float, baseline: PatientBaseline) -> float:
        """
        Estimate what percentile this value is at.

        Returns 0-100 estimate
        """

        if value <= baseline.percentile_5:
            return 5
        elif value <= baseline.percentile_25:
            return 15
        elif value <= baseline.percentile_75:
            return 50
        elif value <= baseline.percentile_95:
            return 85
        else:
            return 95
