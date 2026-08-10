"""
JOMINGOS Risk Assessment Engine

Combines NEWS2 scoring and trend analysis to assess comprehensive deterioration risk.
Implements multi-parameter analysis for early deterioration detection.

Reference: Master Build Prompt Sections 14-17 (Multi-Parameter Analysis)
"""

from django.utils import timezone
from typing import Dict, Optional, Tuple
from vitals.models import VitalSigns
from vitals.utils.trend_engine import TrendAnalyzer


class RiskAssessmentEngine:
    """
    Comprehensive risk assessment combining:
    1. NEWS2 scoring (snapshot assessment)
    2. Trend analysis (trajectory assessment)
    3. Multi-parameter analysis (simultaneous deterioration)

    Outputs a combined risk score that enables early warning systems.
    """

    # Risk level thresholds
    RISK_THRESHOLDS = {
        'low': (0, 4),           # NEWS2 0-4
        'medium': (5, 6),        # NEWS2 5-6
        'high': (7, 100),        # NEWS2 7+
    }

    # How much trend score adds to NEWS2
    TREND_MULTIPLIER = 1.2  # Trends increase concern by 20%

    # Multi-parameter weighting (simultaneous worsening)
    MULTI_PARAM_WEIGHTS = {
        'all_worsening': 3.0,      # All vitals deteriorating
        'most_worsening': 2.0,     # 4-5 vitals deteriorating
        'some_worsening': 1.0,     # 2-3 vitals deteriorating
        'one_worsening': 0.5,      # Only 1 vital deteriorating
        'stable': 0.0,             # No deterioration
    }

    def __init__(self):
        """Initialize risk assessment engine"""
        self.trend_analyzer = TrendAnalyzer()

    def get_latest_vital(self, patient) -> Optional[VitalSigns]:
        """Get the most recent vital for a patient"""
        try:
            return VitalSigns.objects.filter(
                patient=patient
            ).order_by('-recorded_at').first()
        except:
            return None

    def calculate_news2_risk(self, vital: VitalSigns) -> Tuple[str, int]:
        """
        Calculate risk level based on NEWS2 score alone.

        Returns:
            Tuple of (risk_level, score):
            - risk_level: 'low', 'medium', 'high'
            - score: 0-15 (NEWS2 total)
        """
        news2_score = vital.news2_total

        if news2_score <= 4:
            return 'low', news2_score
        elif news2_score <= 6:
            return 'medium', news2_score
        else:
            return 'high', news2_score

    def calculate_trend_risk(self, patient, window_size: int = 4) -> Tuple[str, int]:
        """
        Calculate risk level based on trend analysis.

        Args:
            patient: Patient object
            window_size: Size of observation window (4, 8, or 12)

        Returns:
            Tuple of (risk_level, score):
            - risk_level: 'low', 'medium', 'high'
            - score: 0+ (trend severity)
        """
        trend_score = self.trend_analyzer.get_trend_score(patient, window_size)

        if trend_score == 0:
            return 'low', 0
        elif trend_score <= 3:
            return 'medium', trend_score
        else:
            return 'high', trend_score

    def analyze_multi_parameter_deterioration(self, patient) -> Dict:
        """
        Analyze whether multiple parameters are deteriorating simultaneously.

        This is key to early detection: a patient whose HR, RR, SpO2, and BP
        are all worsening simultaneously is at higher risk than one where
        only HR is elevated.

        Returns:
            Dict with multi-parameter analysis:
            {
                'worsening_count': number of vitals getting worse,
                'deteriorating_together': True if multiple worsening,
                'pattern': 'all_worsening' | 'most_worsening' | etc,
                'multi_param_score': additional risk points,
                'contributing_vitals': list of vitals worsening,
            }
        """
        vitals_list = self.trend_analyzer.get_recent_vitals(patient, limit=8)

        if len(vitals_list) < 2:
            return {
                'worsening_count': 0,
                'deteriorating_together': False,
                'pattern': 'stable',
                'multi_param_score': 0,
                'contributing_vitals': [],
            }

        # Analyze last 2 observations to detect parameter-level changes
        current = vitals_list[-1]
        previous = vitals_list[-2]

        worsening_vitals = []
        time_diff_hours = self.trend_analyzer.get_time_diff_hours(
            current.recorded_at, previous.recorded_at
        )

        if time_diff_hours <= 0:
            return {
                'worsening_count': 0,
                'deteriorating_together': False,
                'pattern': 'stable',
                'multi_param_score': 0,
                'contributing_vitals': [],
            }

        # Check each vital for worsening
        if current.heart_rate and previous.heart_rate:
            roc = self.trend_analyzer.calculate_roc(
                current.heart_rate, previous.heart_rate, time_diff_hours
            )
            if roc and roc >= 10:  # Significant HR increase
                worsening_vitals.append('heart_rate')

        if current.respiratory_rate and previous.respiratory_rate:
            roc = self.trend_analyzer.calculate_roc(
                current.respiratory_rate, previous.respiratory_rate, time_diff_hours
            )
            if roc and roc >= 5:  # Significant RR increase
                worsening_vitals.append('respiratory_rate')

        if current.oxygen_saturation and previous.oxygen_saturation:
            roc = self.trend_analyzer.calculate_roc(
                current.oxygen_saturation, previous.oxygen_saturation, time_diff_hours
            )
            if roc and roc <= -2:  # Significant SpO2 decrease
                worsening_vitals.append('oxygen_saturation')

        if current.bp_systolic and previous.bp_systolic:
            roc = self.trend_analyzer.calculate_roc(
                current.bp_systolic, previous.bp_systolic, time_diff_hours
            )
            if roc and abs(roc) >= 10:  # Significant BP change
                worsening_vitals.append('bp_systolic')

        if current.temperature and previous.temperature:
            roc = self.trend_analyzer.calculate_roc(
                current.temperature, previous.temperature, time_diff_hours
            )
            if roc and abs(roc) >= 1:  # Significant temp change
                worsening_vitals.append('temperature')

        # Determine pattern
        worsening_count = len(worsening_vitals)
        deteriorating_together = worsening_count >= 2

        if worsening_count >= 5:
            pattern = 'all_worsening'
            multi_param_score = self.MULTI_PARAM_WEIGHTS['all_worsening']
        elif worsening_count >= 3:
            pattern = 'most_worsening'
            multi_param_score = self.MULTI_PARAM_WEIGHTS['most_worsening']
        elif worsening_count >= 2:
            pattern = 'some_worsening'
            multi_param_score = self.MULTI_PARAM_WEIGHTS['some_worsening']
        elif worsening_count == 1:
            pattern = 'one_worsening'
            multi_param_score = self.MULTI_PARAM_WEIGHTS['one_worsening']
        else:
            pattern = 'stable'
            multi_param_score = 0

        return {
            'worsening_count': worsening_count,
            'deteriorating_together': deteriorating_together,
            'pattern': pattern,
            'multi_param_score': multi_param_score,
            'contributing_vitals': worsening_vitals,
        }

    def calculate_combined_risk(self, patient) -> Dict:
        """
        Calculate comprehensive combined risk assessment.

        Combines:
        1. NEWS2 score (snapshot)
        2. Trend score (trajectory)
        3. Multi-parameter deterioration (simultaneous worsening)

        Returns:
            Complete risk assessment dict
        """
        # Get latest vital
        vital = self.get_latest_vital(patient)
        if not vital:
            return {
                'patient_id': patient.id,
                'assessment_timestamp': timezone.now().isoformat(),
                'data_available': False,
                'combined_risk': 0,
                'risk_level': 'low',
                'explanation': 'No vital signs recorded yet',
            }

        # Calculate NEWS2 risk
        news2_level, news2_score = self.calculate_news2_risk(vital)

        # Calculate trend risk
        trend_level, trend_score = self.calculate_trend_risk(patient, window_size=4)

        # Calculate multi-parameter risk
        multi_param_analysis = self.analyze_multi_parameter_deterioration(patient)

        # Combine scores
        # Base: NEWS2 score
        # Add: Trend contribution (trend_score * multiplier)
        # Add: Multi-parameter bonus (simultaneous worsening)
        combined_risk = (
            news2_score +
            (trend_score * self.TREND_MULTIPLIER) +
            multi_param_analysis['multi_param_score']
        )

        # Determine overall risk level
        if combined_risk <= 4:
            overall_level = 'low'
        elif combined_risk <= 8:
            overall_level = 'medium'
        elif combined_risk <= 12:
            overall_level = 'high'
        else:
            overall_level = 'critical'

        # Generate explanation
        explanation = self._generate_explanation(
            vital, news2_score, trend_score, multi_param_analysis
        )

        return {
            'patient_id': patient.id,
            'patient_name': patient.get_full_name(),
            'assessment_timestamp': timezone.now().isoformat(),
            'recorded_at': vital.recorded_at.isoformat(),
            'data_available': True,
            'news2': {
                'score': news2_score,
                'level': news2_level,
                'hr_score': vital.news2_hr_score,
                'rr_score': vital.news2_respiratory_score,
                'spo2_score': vital.news2_spo2_score,
                'bp_score': vital.news2_bp_score,
                'temp_score': vital.news2_temp_score,
            },
            'trend': {
                'score': trend_score,
                'level': trend_level,
            },
            'multi_parameter': multi_param_analysis,
            'combined_risk': round(combined_risk, 2),
            'risk_level': overall_level,
            'explanation': explanation,
            'recommendation': self._get_recommendation(overall_level),
        }

    def _generate_explanation(
        self,
        vital: VitalSigns,
        news2_score: int,
        trend_score: int,
        multi_param_analysis: Dict
    ) -> str:
        """Generate human-readable explanation of risk assessment"""
        parts = []

        # NEWS2 explanation
        if news2_score <= 4:
            parts.append(f"NEWS2 score is {news2_score} (normal range).")
        elif news2_score <= 6:
            parts.append(f"NEWS2 score is {news2_score} (elevated).")
        else:
            parts.append(f"NEWS2 score is {news2_score} (critical).")

        # Trend explanation
        if trend_score == 0:
            parts.append("Vitals are stable over time.")
        elif trend_score <= 3:
            parts.append(f"Mild trend detected (score: {trend_score}).")
        elif trend_score <= 6:
            parts.append(f"Moderate deterioration trend (score: {trend_score}).")
        else:
            parts.append(f"Significant deterioration trend (score: {trend_score}).")

        # Multi-parameter explanation
        if multi_param_analysis['worsening_count'] >= 3:
            worsening = ', '.join(multi_param_analysis['contributing_vitals'])
            parts.append(f"Multiple parameters worsening: {worsening}.")
        elif multi_param_analysis['worsening_count'] > 0:
            parts.append(f"{multi_param_analysis['worsening_count']} vital parameter(s) deteriorating.")

        return ' '.join(parts)

    def _get_recommendation(self, risk_level: str) -> str:
        """Get clinical recommendation based on risk level"""
        recommendations = {
            'low': 'Routine monitoring. No immediate action required.',
            'medium': 'Increased monitoring recommended. Review with care team.',
            'high': 'Close monitoring required. Escalate to senior staff.',
            'critical': 'URGENT: Immediate clinical review required. Follow escalation protocol.',
        }
        return recommendations.get(risk_level, 'Unknown risk level.')

    def should_create_alert(self, patient, combined_risk: float) -> Tuple[bool, str]:
        """
        Determine if an alert should be created based on combined risk.

        Returns:
            Tuple of (should_alert, alert_reason)
        """
        if combined_risk >= 12:
            return True, f"CRITICAL: Combined risk {combined_risk:.1f} >= 12"
        elif combined_risk >= 8:
            return True, f"HIGH RISK: Combined risk {combined_risk:.1f} >= 8"
        elif combined_risk >= 5:
            # Check if there's deterioration trend
            trend_score = self.trend_analyzer.get_trend_score(patient, window_size=4)
            if trend_score > 0:
                return True, f"MEDIUM RISK with deterioration trend (risk: {combined_risk:.1f})"

        return False, ""

    def assess_patient(self, patient) -> Dict:
        """
        Complete patient risk assessment.

        This is the main entry point for risk assessment.

        Returns:
            Comprehensive assessment dictionary
        """
        return self.calculate_combined_risk(patient)
