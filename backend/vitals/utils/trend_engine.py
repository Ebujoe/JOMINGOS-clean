"""
JOMINGOS Trend Analysis Engine

Analyzes vital sign trajectories to detect early deterioration patterns.
Calculates rate of change, trends, and deterioration risk over time.

Reference: Master Build Prompt Section 12-17 (Time-Series Analysis)
"""

from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from vitals.models import VitalSigns


class TrendAnalyzer:
    """
    Analyzes vital sign trends over time windows.

    Core Functionality:
    1. Calculate rate of change (RoC) per hour for each vital
    2. Analyze over multiple windows (4, 8, 12 readings)
    3. Detect trend direction (worsening, improving, stable)
    4. Score trend severity
    5. Identify multi-parameter deterioration patterns
    """

    # Thresholds for trend scoring (per hour)
    CRITICAL_THRESHOLDS = {
        'heart_rate': {
            'increase': 20,      # HR rising ≥20 bpm/hour = critical
            'decrease': 30,      # HR dropping ≥30 bpm/hour = critical
        },
        'respiratory_rate': {
            'increase': 10,      # RR rising ≥10 br/min/hour = critical
            'decrease': 10,      # RR dropping ≥10 br/min/hour = critical
        },
        'oxygen_saturation': {
            'decrease': 5,       # SpO2 dropping ≥5%/hour = critical
            'increase': 0,       # SpO2 increasing not concerning
        },
        'bp_systolic': {
            'decrease': 20,      # Systolic dropping ≥20 mmHg/hour = critical
            'increase': 30,      # Systolic rising ≥30 mmHg/hour = critical
        },
        'temperature': {
            'increase': 2.0,     # Temp rising ≥2°C/hour = critical
            'decrease': 1.5,     # Temp dropping ≥1.5°C/hour = critical
        },
    }

    # Weights for trend scoring (how much each vital contributes)
    TREND_WEIGHTS = {
        'heart_rate': 1.0,
        'respiratory_rate': 1.5,      # RR changes = higher weight
        'oxygen_saturation': 2.0,     # SpO2 changes = highest weight
        'bp_systolic': 1.0,
        'temperature': 0.5,           # Temp changes = lower weight
    }

    @staticmethod
    def get_recent_vitals(patient, limit: int = 12) -> List[VitalSigns]:
        """
        Get patient's recent vital signs in chronological order (oldest first).

        Args:
            patient: Patient object
            limit: Maximum number of vitals to retrieve (default: 12)

        Returns:
            List of VitalSigns ordered chronologically (oldest → newest)
        """
        return list(
            VitalSigns.objects.filter(patient=patient)
            .order_by('-recorded_at')[:limit][::-1]  # Reverse to get oldest first
        )

    @staticmethod
    def calculate_roc(
        current_value: Optional[Decimal],
        previous_value: Optional[Decimal],
        time_diff_hours: float
    ) -> Optional[float]:
        """
        Calculate rate of change per hour between two measurements.

        Args:
            current_value: Current vital measurement (may be Decimal)
            previous_value: Previous vital measurement (may be Decimal)
            time_diff_hours: Time difference in hours (must be > 0)

        Returns:
            Rate of change per hour, or None if data insufficient
        """
        if (current_value is None or previous_value is None or time_diff_hours <= 0):
            return None

        try:
            current = float(current_value)
            previous = float(previous_value)
            return (current - previous) / time_diff_hours
        except (ValueError, TypeError):
            return None

    @staticmethod
    def get_time_diff_hours(current_time: timezone.datetime, previous_time: timezone.datetime) -> float:
        """
        Calculate time difference in hours between two timestamps.

        Args:
            current_time: Current timestamp
            previous_time: Previous timestamp

        Returns:
            Time difference in hours (float)
        """
        if current_time <= previous_time:
            return 0
        delta = current_time - previous_time
        return delta.total_seconds() / 3600

    def analyze_window(self, vitals: List[VitalSigns]) -> Dict:
        """
        Analyze trend over a window of vital observations.

        Args:
            vitals: List of VitalSigns objects in chronological order (oldest first)

        Returns:
            Dict with trend analysis results:
            {
                'count': number of observations,
                'time_span_hours': total hours covered,
                'vitals_analyzed': dict of vital-specific trends,
                'trend_directions': dict of direction per vital,
                'trend_scores': dict of numerical score per vital,
                'overall_trend_score': combined score,
                'deteriorating': bool (true if worsening pattern),
                'improving': bool (true if improving pattern),
                'stable': bool (true if no significant change),
            }
        """
        if not vitals or len(vitals) < 2:
            return {
                'count': len(vitals) if vitals else 0,
                'time_span_hours': 0,
                'vitals_analyzed': {},
                'trend_directions': {},
                'trend_scores': {},
                'overall_trend_score': 0,
                'deteriorating': False,
                'improving': False,
                'stable': True,
            }

        # Calculate time span
        first_vital = vitals[0]
        last_vital = vitals[-1]
        time_span_hours = self.get_time_diff_hours(last_vital.recorded_at, first_vital.recorded_at)

        if time_span_hours <= 0:
            return {
                'count': len(vitals),
                'time_span_hours': 0,
                'vitals_analyzed': {},
                'trend_directions': {},
                'trend_scores': {},
                'overall_trend_score': 0,
                'deteriorating': False,
                'improving': False,
                'stable': True,
            }

        # Analyze each vital over the window
        vitals_analyzed = {}
        trend_directions = {}
        trend_scores = {}
        total_score = 0

        # Heart Rate
        hr_roc = self.calculate_roc(
            last_vital.heart_rate,
            first_vital.heart_rate,
            time_span_hours
        )
        if hr_roc is not None:
            vitals_analyzed['heart_rate'] = {
                'roc': round(hr_roc, 2),
                'unit': 'bpm/hour',
                'first_value': float(first_vital.heart_rate) if first_vital.heart_rate else None,
                'last_value': float(last_vital.heart_rate) if last_vital.heart_rate else None,
            }
            hr_direction, hr_score = self._score_vital_trend('heart_rate', hr_roc)
            trend_directions['heart_rate'] = hr_direction
            trend_scores['heart_rate'] = hr_score
            total_score += hr_score * self.TREND_WEIGHTS['heart_rate']

        # Respiratory Rate
        rr_roc = self.calculate_roc(
            last_vital.respiratory_rate,
            first_vital.respiratory_rate,
            time_span_hours
        )
        if rr_roc is not None:
            vitals_analyzed['respiratory_rate'] = {
                'roc': round(rr_roc, 2),
                'unit': 'br/min/hour',
                'first_value': float(first_vital.respiratory_rate) if first_vital.respiratory_rate else None,
                'last_value': float(last_vital.respiratory_rate) if last_vital.respiratory_rate else None,
            }
            rr_direction, rr_score = self._score_vital_trend('respiratory_rate', rr_roc)
            trend_directions['respiratory_rate'] = rr_direction
            trend_scores['respiratory_rate'] = rr_score
            total_score += rr_score * self.TREND_WEIGHTS['respiratory_rate']

        # Oxygen Saturation
        spo2_roc = self.calculate_roc(
            last_vital.oxygen_saturation,
            first_vital.oxygen_saturation,
            time_span_hours
        )
        if spo2_roc is not None:
            vitals_analyzed['oxygen_saturation'] = {
                'roc': round(spo2_roc, 2),
                'unit': '%/hour',
                'first_value': float(first_vital.oxygen_saturation) if first_vital.oxygen_saturation else None,
                'last_value': float(last_vital.oxygen_saturation) if last_vital.oxygen_saturation else None,
            }
            spo2_direction, spo2_score = self._score_vital_trend('oxygen_saturation', spo2_roc)
            trend_directions['oxygen_saturation'] = spo2_direction
            trend_scores['oxygen_saturation'] = spo2_score
            total_score += spo2_score * self.TREND_WEIGHTS['oxygen_saturation']

        # Systolic Blood Pressure
        bp_roc = self.calculate_roc(
            last_vital.bp_systolic,
            first_vital.bp_systolic,
            time_span_hours
        )
        if bp_roc is not None:
            vitals_analyzed['bp_systolic'] = {
                'roc': round(bp_roc, 2),
                'unit': 'mmHg/hour',
                'first_value': float(first_vital.bp_systolic) if first_vital.bp_systolic else None,
                'last_value': float(last_vital.bp_systolic) if last_vital.bp_systolic else None,
            }
            bp_direction, bp_score = self._score_vital_trend('bp_systolic', bp_roc)
            trend_directions['bp_systolic'] = bp_direction
            trend_scores['bp_systolic'] = bp_score
            total_score += bp_score * self.TREND_WEIGHTS['bp_systolic']

        # Temperature
        temp_roc = self.calculate_roc(
            last_vital.temperature,
            first_vital.temperature,
            time_span_hours
        )
        if temp_roc is not None:
            vitals_analyzed['temperature'] = {
                'roc': round(temp_roc, 2),
                'unit': '°C/hour',
                'first_value': float(first_vital.temperature) if first_vital.temperature else None,
                'last_value': float(last_vital.temperature) if last_vital.temperature else None,
            }
            temp_direction, temp_score = self._score_vital_trend('temperature', temp_roc)
            trend_directions['temperature'] = temp_direction
            trend_scores['temperature'] = temp_score
            total_score += temp_score * self.TREND_WEIGHTS['temperature']

        # Determine overall trend
        deteriorating = total_score > 0
        improving = total_score < -2
        stable = not (deteriorating or improving)

        return {
            'count': len(vitals),
            'time_span_hours': round(time_span_hours, 2),
            'vitals_analyzed': vitals_analyzed,
            'trend_directions': trend_directions,
            'trend_scores': trend_scores,
            'overall_trend_score': round(total_score, 2),
            'deteriorating': deteriorating,
            'improving': improving,
            'stable': stable,
        }

    def _score_vital_trend(self, vital_name: str, roc: float) -> Tuple[str, int]:
        """
        Score the trend severity for a specific vital.

        Args:
            vital_name: Name of vital (e.g., 'heart_rate')
            roc: Rate of change per hour

        Returns:
            Tuple of (direction, score):
            - direction: 'worsening', 'stable', 'improving'
            - score: 0 (stable), 1 (mild), 2 (moderate), 3 (critical)
        """
        if vital_name not in self.CRITICAL_THRESHOLDS:
            return 'unknown', 0

        thresholds = self.CRITICAL_THRESHOLDS[vital_name]

        # For vitals where increase is bad (HR, RR, Temp, BP)
        if vital_name in ['heart_rate', 'respiratory_rate', 'temperature']:
            if roc >= thresholds.get('increase', float('inf')):
                return 'worsening', 3  # Critical
            elif roc >= thresholds.get('increase', float('inf')) * 0.5:
                return 'worsening', 2  # Moderate
            elif roc >= thresholds.get('increase', float('inf')) * 0.25:
                return 'worsening', 1  # Mild
            elif roc <= -thresholds.get('decrease', float('inf')) * 0.5:
                return 'improving', 1  # Mild improvement
            else:
                return 'stable', 0

        # For vitals where decrease is bad (SpO2, BP)
        elif vital_name in ['oxygen_saturation', 'bp_systolic']:
            if roc <= -thresholds.get('decrease', float('inf')):
                return 'worsening', 3  # Critical
            elif roc <= -thresholds.get('decrease', float('inf')) * 0.5:
                return 'worsening', 2  # Moderate
            elif roc <= -thresholds.get('decrease', float('inf')) * 0.25:
                return 'worsening', 1  # Mild
            elif roc >= thresholds.get('increase', float('inf')) * 0.5:
                return 'improving', 1  # Mild improvement
            else:
                return 'stable', 0

        return 'unknown', 0

    def analyze_patient_trends(self, patient) -> Dict:
        """
        Complete trend analysis for a patient across multiple windows.

        Args:
            patient: Patient object

        Returns:
            Dict with trend analysis for 4, 8, and 12 reading windows
        """
        vitals = self.get_recent_vitals(patient, limit=12)

        return {
            'patient_id': patient.id,
            'patient_name': patient.get_full_name(),
            'analysis_timestamp': timezone.now().isoformat(),
            'total_vitals_available': len(vitals),
            'window_4': self.analyze_window(vitals[-4:] if len(vitals) >= 4 else vitals),
            'window_8': self.analyze_window(vitals[-8:] if len(vitals) >= 8 else vitals),
            'window_12': self.analyze_window(vitals[-12:] if len(vitals) >= 12 else vitals),
        }

    def get_trend_score(self, patient, window_size: int = 4) -> int:
        """
        Get a single trend score for a patient (0-based, higher = worse).

        Args:
            patient: Patient object
            window_size: Size of window to analyze (4, 8, or 12)

        Returns:
            Integer trend score (0+)
        """
        vitals = self.get_recent_vitals(patient, limit=window_size)

        if len(vitals) < 2:
            return 0

        analysis = self.analyze_window(vitals)
        score = analysis['overall_trend_score']

        # Convert to 0+ scale
        return max(0, int(score))
