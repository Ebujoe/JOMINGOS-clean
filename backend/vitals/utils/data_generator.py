"""
REALISTIC VITAL DATA GENERATOR
===============================

Week 2 Deliverable: Generate realistic vital sign data for testing.

Used to:
1. Quickly reach 30+ readings per patient for baseline calculation
2. Test forecasting models
3. Simulate patient behavior patterns
4. Create test datasets for validation

IMPORTANT: Data is synthetic for testing only. DO NOT use in production.
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import math
import logging

logger = logging.getLogger(__name__)


class PatientVitalSimulator:
    """
    Simulate realistic vital sign patterns for a patient.

    Each patient has:
    - Baseline values (patient-specific normals)
    - Circadian rhythm (time-of-day variation)
    - Activity effects (varies by time)
    - Random noise (measurement variation)
    """

    def __init__(self, patient_id: int, patient_name: str = "Test Patient"):
        """Initialize simulator for a patient."""
        self.patient_id = patient_id
        self.patient_name = patient_name

        # Define patient-specific baselines
        self.baselines = {
            'heart_rate': {
                'mean': 72,
                'std_dev': 8,
                'min': 60,
                'max': 90,
            },
            'respiratory_rate': {
                'mean': 16,
                'std_dev': 2,
                'min': 12,
                'max': 20,
            },
            'oxygen_saturation': {
                'mean': 97.5,
                'std_dev': 1.0,
                'min': 95,
                'max': 100,
            },
            'temperature': {
                'mean': 37.0,
                'std_dev': 0.3,
                'min': 36.5,
                'max': 37.5,
            },
            'bp_systolic': {
                'mean': 120,
                'std_dev': 8,
                'min': 110,
                'max': 135,
            },
            'bp_diastolic': {
                'mean': 75,
                'std_dev': 5,
                'min': 68,
                'max': 85,
            },
        }

        logger.info(f"Initialized simulator for patient {patient_id}")

    def generate_vital(
        self,
        vital_name: str,
        timestamp: datetime,
        activity_level: str = 'rest',  # rest, mild, moderate, vigorous
    ) -> float:
        """
        Generate realistic vital value for given timestamp.

        Args:
            vital_name: Type of vital (heart_rate, etc)
            timestamp: When measurement was taken
            activity_level: Current activity level

        Returns:
            Realistic vital value
        """

        if vital_name not in self.baselines:
            raise ValueError(f"Unknown vital: {vital_name}")

        baseline = self.baselines[vital_name]
        mean = baseline['mean']
        std_dev = baseline['std_dev']

        # Circadian adjustment (time-of-day effect)
        circadian = self._circadian_adjustment(vital_name, timestamp.hour)

        # Activity adjustment
        activity_mult = self._activity_adjustment(vital_name, activity_level)

        # Random noise (measurement variation)
        noise = random.gauss(0, std_dev * 0.3)

        # Combine all factors
        value = mean + circadian + noise
        value *= activity_mult

        # Enforce bounds
        value = max(baseline['min'], min(baseline['max'], value))

        return round(value, 1)

    def _circadian_adjustment(self, vital_name: str, hour: int) -> float:
        """
        Apply circadian (time-of-day) rhythm adjustment.

        Most vitals vary by time of day:
        - Heart rate: Higher during day, lower at night
        - Temperature: Peaks in afternoon, lowest in morning
        - Blood pressure: Higher in morning
        """

        # Normalize hour to 0-1 (24h cycle)
        hour_norm = (hour + random.uniform(-0.5, 0.5)) / 24.0

        if vital_name in ['heart_rate', 'respiratory_rate']:
            # Higher during day, lower at night
            return math.sin(hour_norm * 2 * math.pi) * 5

        elif vital_name == 'temperature':
            # Peak in afternoon (14-16h), low in early morning
            peak_hour = 15
            adjustment = 10 * math.cos((hour - peak_hour) / 24.0 * 2 * math.pi)
            return adjustment * 0.3

        elif vital_name in ['bp_systolic', 'bp_diastolic']:
            # Higher in morning, lower at night
            return math.cos(hour_norm * 2 * math.pi) * 8

        elif vital_name == 'oxygen_saturation':
            # Relatively stable
            return random.gauss(0, 0.2)

        return 0

    def _activity_adjustment(self, vital_name: str, activity_level: str) -> float:
        """
        Adjust vital based on activity level.

        Activity increases heart rate and respiratory rate,
        decreases oxygen saturation slightly.
        """

        activity_mults = {
            'rest': 1.0,
            'mild': 1.05,        # Light activity
            'moderate': 1.15,    # Walking
            'vigorous': 1.35,    # Exercise
        }

        mult = activity_mults.get(activity_level, 1.0)

        # Different vitals respond differently to activity
        if vital_name in ['heart_rate', 'respiratory_rate']:
            return mult
        elif vital_name == 'oxygen_saturation':
            # Slight decrease during vigorous activity
            if activity_level == 'vigorous':
                return 0.98
            return 1.0
        else:
            # BP increases slightly with activity
            if vital_name in ['bp_systolic', 'bp_diastolic']:
                return mult * 0.95  # Slight effect
            return 1.0

    def generate_sequence(
        self,
        count: int = 30,
        start_date: datetime = None,
        interval_hours: float = 6.0,
    ) -> List[Dict]:
        """
        Generate sequence of realistic vitals.

        Args:
            count: Number of vitals to generate
            start_date: When to start generating (default: today)
            interval_hours: Hours between measurements (default: 6)

        Returns:
            List of vital dicts ready for recording
        """

        if start_date is None:
            start_date = datetime.now() - timedelta(days=14)

        vitals = []
        current_time = start_date

        for i in range(count):
            # Vary interval slightly (±1 hour)
            actual_interval = interval_hours + random.uniform(-1, 1)
            current_time += timedelta(hours=actual_interval)

            # Determine activity based on time of day
            hour = current_time.hour
            if 22 <= hour or hour < 7:
                activity = 'rest'  # Night sleep
            elif 8 <= hour < 9 or 12 <= hour < 13:
                activity = 'moderate'  # Morning routine, lunch
            elif 14 <= hour < 17:
                activity = 'mild'  # Afternoon
            else:
                activity = 'rest'  # Evening

            # Generate all vitals for this timestamp
            vital_set = {
                'timestamp': current_time,
                'heart_rate': self.generate_vital('heart_rate', current_time, activity),
                'respiratory_rate': self.generate_vital('respiratory_rate', current_time, activity),
                'oxygen_saturation': self.generate_vital('oxygen_saturation', current_time, activity),
                'temperature': self.generate_vital('temperature', current_time, activity),
                'bp_systolic': self.generate_vital('bp_systolic', current_time, activity),
                'bp_diastolic': self.generate_vital('bp_diastolic', current_time, activity),
            }

            vitals.append(vital_set)

        logger.info(f"Generated {count} vital measurements for patient {self.patient_id}")
        return vitals

    @staticmethod
    def generate_deteriorating_sequence(
        patient_id: int,
        count: int = 30,
        start_date: datetime = None,
        deterioration_rate: float = 0.1,
    ) -> List[Dict]:
        """
        Generate sequence showing patient deterioration.

        Useful for testing alert systems.

        Args:
            patient_id: Patient ID
            count: Number of readings
            start_date: Start date
            deterioration_rate: How much worse per reading (0-1)

        Returns:
            List of vitals showing progressive deterioration
        """

        if start_date is None:
            start_date = datetime.now() - timedelta(days=7)

        simulator = PatientVitalSimulator(patient_id)

        # Start with normal baseline
        vitals = []
        current_time = start_date

        for i in range(count):
            actual_interval = 6 + random.uniform(-1, 1)
            current_time += timedelta(hours=actual_interval)

            # Progressive deterioration
            deterioration_factor = 1 - (deterioration_rate * (i / count))

            vital_set = {
                'timestamp': current_time,
                'heart_rate': int(72 + (10 * (1 - deterioration_factor)) + random.gauss(0, 3)),
                'respiratory_rate': int(16 + (8 * (1 - deterioration_factor)) + random.gauss(0, 1)),
                'oxygen_saturation': max(90, 97.5 - (5 * (1 - deterioration_factor)) + random.gauss(0, 0.5)),
                'temperature': 37.0 + (1.5 * (1 - deterioration_factor)) + random.gauss(0, 0.1),
                'bp_systolic': int(120 + (15 * (1 - deterioration_factor)) + random.gauss(0, 4)),
                'bp_diastolic': int(75 + (10 * (1 - deterioration_factor)) + random.gauss(0, 3)),
            }

            vitals.append(vital_set)

        logger.info(f"Generated deteriorating sequence for patient {patient_id}")
        return vitals


class BulkDataGenerator:
    """Generate data for multiple patients at once."""

    @staticmethod
    def generate_for_patient(
        patient_id: int,
        patient_name: str,
        count: int = 30,
    ) -> List[Dict]:
        """
        Generate vital sequence for a single patient.

        Returns:
            List of vital dicts ready to store
        """

        simulator = PatientVitalSimulator(patient_id, patient_name)
        vitals = simulator.generate_sequence(count=count)

        return vitals

    @staticmethod
    def generate_for_multiple_patients(
        patient_ids: List[int],
        count_per_patient: int = 30,
    ) -> Dict[int, List[Dict]]:
        """
        Generate vitals for multiple patients.

        Returns:
            Dict of patient_id -> list of vital dicts
        """

        all_data = {}

        for patient_id in patient_ids:
            all_data[patient_id] = BulkDataGenerator.generate_for_patient(
                patient_id=patient_id,
                patient_name=f"Patient {patient_id}",
                count=count_per_patient,
            )

        logger.info(f"Generated data for {len(patient_ids)} patients")
        return all_data


class DataQualitySimulator:
    """Simulate data quality issues for testing validator."""

    @staticmethod
    def add_quality_issues(
        vital_sequence: List[Dict],
        issue_rate: float = 0.1,
    ) -> List[Dict]:
        """
        Introduce quality issues into a vital sequence.

        Args:
            vital_sequence: Original vitals
            issue_rate: % of readings to corrupt (0-1)

        Returns:
            Corrupted vital sequence
        """

        corrupted = []
        issue_count = int(len(vital_sequence) * issue_rate)

        # Randomly select which vitals to corrupt
        issue_indices = random.sample(range(len(vital_sequence)), min(issue_count, len(vital_sequence)))

        for i, vital in enumerate(vital_sequence):
            if i in issue_indices:
                issue_type = random.choice(['outlier', 'duplicate', 'invalid_range'])

                if issue_type == 'outlier':
                    # Create extreme value
                    vital_copy = vital.copy()
                    vital_copy['heart_rate'] = random.choice([30, 180, 200])
                    corrupted.append(vital_copy)

                elif issue_type == 'duplicate':
                    # Add same value twice
                    corrupted.append(vital)
                    corrupted.append(vital)

                elif issue_type == 'invalid_range':
                    # Impossible value
                    vital_copy = vital.copy()
                    vital_copy['temperature'] = random.choice([20, 50])
                    corrupted.append(vital_copy)
            else:
                corrupted.append(vital)

        logger.info(f"Introduced {len(issue_indices)} quality issues")
        return corrupted
