"""
JOMINGOS Explainability Engine

Generates human-readable clinical explanations for risk assessments.
Enables "why this result?" transparency for healthcare professionals.

Reference: Phase 5 - Explainability & Dashboard Display
"""

from typing import Dict, List, Optional
from django.utils import timezone
from vitals.models import RiskAssessment, VitalSigns


class ExplainabilityEngine:
    """
    Generates detailed, clinically-meaningful explanations for risk assessments.

    Provides:
    1. Component-level explanations (NEWS2, Trend, Multi-parameter)
    2. Contributing factors analysis
    3. Historical context
    4. Actionable recommendations
    5. Risk progression narrative
    """

    # Clinical thresholds for explanation
    CRITICAL_NEWS2_SCORE = 7
    HIGH_COMBINED_RISK = 8
    CRITICAL_COMBINED_RISK = 12

    # Vital-specific context
    VITAL_THRESHOLDS = {
        'heart_rate': {
            'critical_low': 40,
            'critical_high': 130,
            'warning_low': 50,
            'warning_high': 110,
            'normal': (50, 90),
        },
        'respiratory_rate': {
            'critical_low': 8,
            'critical_high': 24,
            'warning_low': 12,
            'warning_high': 20,
            'normal': (12, 20),
        },
        'oxygen_saturation': {
            'critical': 91,
            'warning': 94,
            'normal': (95, 100),
        },
        'bp_systolic': {
            'critical_low': 90,
            'critical_high': 220,
            'warning_low': 100,
            'warning_high': 160,
            'normal': (110, 140),
        },
        'temperature': {
            'critical_low': 35.0,
            'critical_high': 39.0,
            'warning_low': 36.0,
            'warning_high': 38.0,
            'normal': (36.5, 37.5),
        },
    }

    def __init__(self):
        """Initialize explainability engine"""
        pass

    def explain_assessment(self, assessment: RiskAssessment) -> Dict[str, str]:
        """
        Generate comprehensive explanation for a risk assessment.

        Returns:
            Dict with detailed explanations:
            - executive_summary: 1-2 sentence overview
            - news2_explanation: Why NEWS2 score is at this level
            - trend_explanation: Vital trend analysis
            - multi_param_explanation: Which vitals worsening together
            - contributing_factors: Ordered list of concern areas
            - clinical_context: Historical context
            - recommendation: Action to take
        """
        return {
            'executive_summary': self._generate_executive_summary(assessment),
            'news2_explanation': self._explain_news2(assessment),
            'trend_explanation': self._explain_trend(assessment),
            'multi_param_explanation': self._explain_multi_parameter(assessment),
            'contributing_factors': self._identify_contributing_factors(assessment),
            'clinical_context': self._get_clinical_context(assessment),
            'recommendation': self._get_detailed_recommendation(assessment),
            'next_actions': self._get_next_actions(assessment),
        }

    def _generate_executive_summary(self, assessment: RiskAssessment) -> str:
        """1-2 sentence overview of patient status"""
        if assessment.risk_level == 'critical':
            return f"URGENT: Patient risk level is CRITICAL (score: {assessment.combined_risk:.1f}). Immediate clinical review required."
        elif assessment.risk_level == 'high':
            return f"HIGH RISK: Combined risk score {assessment.combined_risk:.1f} indicates need for escalation and close monitoring."
        elif assessment.risk_level == 'medium':
            return f"MEDIUM RISK: Patient showing concerning vital trends (score: {assessment.combined_risk:.1f}). Increased monitoring recommended."
        else:
            return f"LOW RISK: Patient vitals are stable (score: {assessment.combined_risk:.1f}). Routine monitoring appropriate."

    def _explain_news2(self, assessment: RiskAssessment) -> str:
        """Explain NEWS2 component and why it's at this level"""
        score = assessment.news2_total

        if score <= 4:
            severity = "normal"
        elif score <= 6:
            severity = "elevated"
        else:
            severity = "critical"

        parts = [f"NEWS2 score is {score} ({severity} range)."]

        # Identify contributing components
        components = []
        if assessment.news2_hr_score > 0:
            components.append(f"heart rate ({assessment.news2_hr_score} points)")
        if assessment.news2_rr_score > 0:
            components.append(f"respiratory rate ({assessment.news2_rr_score} points)")
        if assessment.news2_spo2_score > 0:
            components.append(f"oxygen saturation ({assessment.news2_spo2_score} points)")
        if assessment.news2_bp_score > 0:
            components.append(f"blood pressure ({assessment.news2_bp_score} points)")
        if assessment.news2_temp_score > 0:
            components.append(f"temperature ({assessment.news2_temp_score} points)")

        if components:
            parts.append(f"Contributing factors: {', '.join(components)}.")

        return ' '.join(parts)

    def _explain_trend(self, assessment: RiskAssessment) -> str:
        """Explain vital trends and trajectory"""
        if assessment.trend_score == 0:
            return "Vital signs are stable over time with no concerning trends."

        trend_desc = {
            'low': 'mild',
            'medium': 'moderate',
            'high': 'significant',
        }.get(assessment.trend_level, 'unknown')

        return f"{trend_desc.capitalize()} deterioration trend detected (trend score: {assessment.trend_score}). Vitals are moving in concerning directions."

    def _explain_multi_parameter(self, assessment: RiskAssessment) -> str:
        """Explain multi-parameter worsening"""
        pattern = assessment.multi_param_details.get('pattern', 'stable')

        if pattern == 'stable':
            return "No multi-parameter worsening detected."
        elif pattern == 'one_worsening':
            vitals = assessment.multi_param_details.get('contributing_vitals', [])
            vital = vitals[0] if vitals else 'vital'
            return f"One vital parameter deteriorating: {vital}."
        elif pattern == 'some_worsening':
            vitals = assessment.multi_param_details.get('contributing_vitals', [])
            return f"Multiple parameters worsening: {', '.join(vitals)}."
        elif pattern == 'most_worsening':
            vitals = assessment.multi_param_details.get('contributing_vitals', [])
            return f"Most vital parameters worsening: {', '.join(vitals)}. This simultaneous deterioration significantly increases risk."
        elif pattern == 'all_worsening':
            vitals = assessment.multi_param_details.get('contributing_vitals', [])
            return f"ALL vital parameters worsening simultaneously: {', '.join(vitals)}. This is a critical pattern requiring immediate intervention."

        return "Multi-parameter analysis indicates concerning patterns."

    def _identify_contributing_factors(self, assessment: RiskAssessment) -> List[Dict[str, str]]:
        """
        Identify and rank contributing factors to risk.

        Returns ordered list of concern areas with explanations.
        """
        factors = []

        # Add NEWS2 components (if scoring points)
        if assessment.news2_spo2_score > 0:
            factors.append({
                'factor': 'Low Oxygen Saturation',
                'severity': 'critical' if assessment.news2_spo2_score >= 3 else 'high',
                'explanation': f'SpO2 score: {assessment.news2_spo2_score} points. Hypoxia is a critical concern.',
                'priority': 1,
            })

        if assessment.news2_rr_score > 0:
            factors.append({
                'factor': 'Abnormal Respiratory Rate',
                'severity': 'high' if assessment.news2_rr_score >= 3 else 'medium',
                'explanation': f'RR score: {assessment.news2_rr_score} points. Respiratory distress detected.',
                'priority': 2,
            })

        if assessment.news2_hr_score > 0:
            factors.append({
                'factor': 'Abnormal Heart Rate',
                'severity': 'medium' if assessment.news2_hr_score >= 2 else 'low',
                'explanation': f'HR score: {assessment.news2_hr_score} points. Tachycardia or bradycardia detected.',
                'priority': 3,
            })

        if assessment.news2_bp_score > 0:
            factors.append({
                'factor': 'Abnormal Blood Pressure',
                'severity': 'high' if assessment.news2_bp_score >= 3 else 'medium',
                'explanation': f'BP score: {assessment.news2_bp_score} points. Blood pressure outside safe range.',
                'priority': 4,
            })

        if assessment.news2_temp_score > 0:
            factors.append({
                'factor': 'Abnormal Temperature',
                'severity': 'medium',
                'explanation': f'Temp score: {assessment.news2_temp_score} points. Fever or hypothermia detected.',
                'priority': 5,
            })

        # Add trend factor if present
        if assessment.trend_score > 0:
            factors.append({
                'factor': 'Deteriorating Trend',
                'severity': 'high' if assessment.trend_score > 5 else 'medium',
                'explanation': f'Vital trends show worsening (score: {assessment.trend_score}). Patient moving toward critical.',
                'priority': 0,  # Highest priority
            })

        # Add multi-parameter factor if present
        if assessment.multi_param_score > 0:
            factors.append({
                'factor': 'Multi-Parameter Deterioration',
                'severity': 'critical' if assessment.multi_param_score >= 2.5 else 'high',
                'explanation': f'Multiple vitals worsening simultaneously ({assessment.multi_param_details.get("worsening_count", 0)} parameters). Pattern: {assessment.multi_param_details.get("pattern", "unknown")}.',
                'priority': 1,
            })

        # Sort by priority
        factors.sort(key=lambda x: x['priority'])

        return factors

    def _get_clinical_context(self, assessment: RiskAssessment) -> str:
        """Get historical context about patient trend"""
        try:
            # Get previous assessment if available
            previous = RiskAssessment.objects.filter(
                patient=assessment.patient,
                assessed_at__lt=assessment.assessed_at
            ).order_by('-assessed_at').first()

            if not previous:
                return "First risk assessment on record for this patient."

            # Compare to previous
            if assessment.combined_risk > previous.combined_risk + 2:
                trend_desc = f"worsening (increased from {previous.combined_risk:.1f} to {assessment.combined_risk:.1f})"
            elif assessment.combined_risk < previous.combined_risk - 2:
                trend_desc = f"improving (decreased from {previous.combined_risk:.1f} to {assessment.combined_risk:.1f})"
            else:
                trend_desc = f"stable (unchanged from {previous.combined_risk:.1f})"

            time_diff = (assessment.assessed_at - previous.assessed_at).total_seconds() / 3600
            return f"Patient risk is {trend_desc} over the last {int(time_diff)} hour(s)."

        except Exception as e:
            return f"Unable to retrieve historical context: {str(e)}"

    def _get_detailed_recommendation(self, assessment: RiskAssessment) -> str:
        """Get detailed clinical recommendation based on risk level"""
        recommendations = {
            'low': 'Continue routine monitoring. No escalation needed. Review again at next scheduled vital check.',
            'medium': 'Increase monitoring frequency. Notify care team lead. Review vitals again within 1-2 hours.',
            'high': 'ESCALATE to senior nursing staff immediately. Consider physician consultation. Continuous or frequent monitoring required.',
            'critical': 'URGENT: Immediate physician review required. Follow critical patient protocol. Consider acute care transfer if appropriate.',
        }
        return recommendations.get(assessment.risk_level, 'Contact clinical supervisor for guidance.')

    def _get_next_actions(self, assessment: RiskAssessment) -> List[str]:
        """Get ordered list of next clinical actions"""
        actions = []

        if assessment.risk_level == 'critical':
            actions = [
                'Notify physician immediately',
                'Assess airway, breathing, circulation (ABC)',
                'Consider ICU transfer',
                'Initiate continuous monitoring',
                'Repeat vital signs within 5 minutes',
                'Document decision to escalate',
            ]
        elif assessment.risk_level == 'high':
            actions = [
                'Notify senior nursing staff',
                'Increase monitoring frequency to every 30-60 minutes',
                'Prepare for possible escalation',
                'Repeat vital signs in 30 minutes',
                'Consider oxygen therapy if SpO2 low',
                'Consult care plan',
            ]
        elif assessment.risk_level == 'medium':
            actions = [
                'Notify charge nurse',
                'Increase monitoring frequency to every 2-3 hours',
                'Re-assess in 1-2 hours',
                'Document trend noted',
                'Prepare escalation plan if worsens',
            ]
        else:  # low
            actions = [
                'Continue routine monitoring',
                'Next vital check per standard schedule',
                'Note stability in chart',
            ]

        return actions

    def explain_vital_contribution(self, vital: VitalSigns, assessment: RiskAssessment) -> Dict[str, str]:
        """
        Explain how a specific vital contributed to risk assessment.

        Shows:
        - Raw value
        - NEWS2 points awarded
        - Comparison to normal range
        - Clinical significance
        """
        explanations = {}

        # Heart Rate
        if vital.heart_rate:
            hr = vital.heart_rate
            if hr <= 40:
                status = "critically low (severe bradycardia)"
                score_explanation = "3 points - severe bradycardia"
            elif hr <= 50:
                status = "low (mild bradycardia)"
                score_explanation = "1 point - mild bradycardia"
            elif hr <= 90:
                status = "normal"
                score_explanation = "0 points - normal range"
            elif hr <= 110:
                status = "elevated (mild tachycardia)"
                score_explanation = "1 point - mild tachycardia"
            elif hr <= 130:
                status = "high (moderate tachycardia)"
                score_explanation = "2 points - moderate tachycardia"
            else:
                status = "critically high (severe tachycardia)"
                score_explanation = "3 points - severe tachycardia"

            explanations['heart_rate'] = f"{hr} bpm ({status}). {score_explanation}."

        # Respiratory Rate
        if vital.respiratory_rate:
            rr = vital.respiratory_rate
            if rr <= 8:
                status = "critically low"
                score_explanation = "3 points - respiratory depression"
            elif rr <= 11:
                status = "low"
                score_explanation = "1 point - hypoventilation"
            elif rr <= 20:
                status = "normal"
                score_explanation = "0 points - normal range"
            elif rr <= 24:
                status = "elevated"
                score_explanation = "2 points - tachypnea"
            else:
                status = "critically elevated"
                score_explanation = "3 points - severe tachypnea"

            explanations['respiratory_rate'] = f"{rr} br/min ({status}). {score_explanation}."

        # Oxygen Saturation
        if vital.oxygen_saturation:
            spo2 = float(vital.oxygen_saturation)
            if spo2 <= 91:
                status = "critically low"
                score_explanation = "3 points - severe hypoxia"
            elif spo2 <= 93:
                status = "low"
                score_explanation = "2 points - moderate hypoxia"
            elif spo2 <= 95:
                status = "mildly low"
                score_explanation = "1 point - mild hypoxia"
            else:
                status = "normal"
                score_explanation = "0 points - normal range"

            explanations['oxygen_saturation'] = f"{spo2}% ({status}). {score_explanation}."

        # Blood Pressure
        if vital.bp_systolic:
            bp = vital.bp_systolic
            if bp <= 90:
                status = "critically low (hypotension)"
                score_explanation = "3 points - severe hypotension"
            elif bp <= 100:
                status = "low (mild hypotension)"
                score_explanation = "2 points - mild hypotension"
            elif bp <= 110:
                status = "mildly low"
                score_explanation = "1 point - borderline low"
            elif bp <= 219:
                status = "normal"
                score_explanation = "0 points - normal range"
            else:
                status = "critically high (hypertensive crisis)"
                score_explanation = "3 points - severe hypertension"

            explanations['bp_systolic'] = f"{bp} mmHg ({status}). {score_explanation}."

        # Temperature
        if vital.temperature:
            temp = float(vital.temperature)
            if temp <= 35.0:
                status = "critically low (hypothermia)"
                score_explanation = "3 points - severe hypothermia"
            elif temp <= 36.0:
                status = "low"
                score_explanation = "1 point - hypothermia"
            elif temp <= 38.0:
                status = "normal"
                score_explanation = "0 points - normal range"
            elif temp <= 39.0:
                status = "elevated (fever)"
                score_explanation = "1 point - mild fever"
            else:
                status = "high (high fever)"
                score_explanation = "2 points - high fever"

            explanations['temperature'] = f"{temp}°C ({status}). {score_explanation}."

        return explanations

    def generate_assessment_narrative(self, assessment: RiskAssessment) -> str:
        """
        Generate a complete narrative summary suitable for clinical notes.
        """
        narrative_parts = []

        # Assessment time
        time_str = assessment.assessed_at.strftime("%d/%m/%Y %H:%M")
        narrative_parts.append(f"**Risk Assessment ({time_str})**")
        narrative_parts.append("")

        # Overall status
        narrative_parts.append(f"**Risk Level**: {assessment.risk_level.upper()}")
        narrative_parts.append(f"**Combined Risk Score**: {assessment.combined_risk:.1f}")
        narrative_parts.append("")

        # Components
        narrative_parts.append("**Component Scores**:")
        narrative_parts.append(f"- NEWS2: {assessment.news2_total} ({assessment.news2_total <= 4 and 'low' or assessment.news2_total <= 6 and 'medium' or 'high'})")
        narrative_parts.append(f"- Trend: {assessment.trend_score} ({assessment.trend_level})")
        narrative_parts.append(f"- Multi-Parameter: {assessment.multi_param_score}")
        narrative_parts.append("")

        # Clinical explanation
        narrative_parts.append("**Clinical Assessment**:")
        narrative_parts.append(assessment.explanation_text)
        narrative_parts.append("")

        # Recommendation
        narrative_parts.append("**Recommendation**:")
        narrative_parts.append(assessment.recommendation)
        narrative_parts.append("")

        # Decision logic
        if assessment.decision_logic:
            narrative_parts.append("**Decision Logic**:")
            narrative_parts.append(assessment.decision_logic.get('combined_formula', 'N/A'))

        return "\n".join(narrative_parts)
