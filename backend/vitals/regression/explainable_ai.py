"""
EXPLAINABLE AI - Confidence Scoring System

This module implements explainable AI (XAI) by assigning a confidence score
to every prediction. This helps clinical staff understand WHEN to trust
the system and WHEN to verify manually.

Why Explainable AI in Healthcare?

PROBLEM: Black-box predictions don't work in clinical settings
- Clinicians won't trust predictions they can't understand
- Regulators require explainability
- When wrong prediction happens, need to understand why
- Legal liability issues with unexplainable decisions

SOLUTION: Confidence scores with 4-factor breakdown

THE 4 CONFIDENCE FACTORS:

1. DATA VOLUME (25% weight)
   Question: Do we have enough historical data?
   Why: Models need sufficient history to learn patterns
   - Few measurements (n < 10): Low confidence (30%)
   - Medium measurements (n = 10-30): Medium confidence (70%)
   - Abundant measurements (n > 30): High confidence (95%)

2. MODEL AGREEMENT (25% weight)
   Question: Do all 5 methods predict similar values?
   Why: High disagreement means data is ambiguous/noisy
   - Methods within 5% of ensemble: High agreement (95%)
   - Methods within 10% of ensemble: Moderate agreement (70%)
   - Methods differ > 15%: Low agreement (30%)

3. EXTRAPOLATION DISTANCE (20% weight)
   Question: Is forecast far outside historical range?
   Why: Predictions outside observed range are unreliable
   - Forecast within historical min/max: High confidence (95%)
   - Forecast ±1 std from range: Medium confidence (70%)
   - Forecast > 2 std outside: Low confidence (20%)

4. STABILITY (30% weight)
   Question: Is the patient's condition stable or chaotic?
   Why: Stable patients = predictable, chaotic patients = unpredictable
   - Low variation (CV < 0.08): High confidence (95%)
   - Medium variation (CV 0.08-0.15): Medium confidence (70%)
   - High variation (CV > 0.15): Low confidence (35%)

COMPOSITE CONFIDENCE:
Confidence = 0.25*volume + 0.25*agreement + 0.20*extrapolation + 0.30*stability

CLINICAL IMPLICATIONS:
- HIGH (90%+): Can trigger alerts automatically
- MEDIUM (70-90%): Requires manual review before alert
- LOW (<70%): Information only, no automatic action
"""

import numpy as np
from typing import List, Dict, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceScore:
    """Data class for confidence score components."""
    overall: float
    data_volume: float
    model_agreement: float
    extrapolation_distance: float
    stability: float
    level: str  # 'HIGH', 'MEDIUM', 'LOW'
    reasoning: str


class ExplainableAIScorer:
    """
    Calculates confidence scores for predictions with explainability.

    Makes AI predictions trustworthy by answering:
    - Why this prediction?
    - How confident are we?
    - When should clinicians rely on this?
    - What could go wrong?
    """

    def __init__(self):
        """Initialize the XAI scorer."""
        self.measurements = None
        self.ensemble_forecast = None
        self.individual_predictions = None
        self.confidence_score = None

    def calculate_data_volume_score(self, n_measurements: int) -> Tuple[float, str]:
        """
        Factor 1: Evaluate sufficiency of historical data for reliable forecasting.

        The question: Do we have enough measurements to detect true patterns?

        Data volume thresholds are based on time-series analysis theory and our
        testing on patient vital signs. More measurements = more confidence in
        identified patterns:

        Threshold breakdown:
        - < 5 measurements: Cannot extract any meaningful pattern (10%)
        - 5-10 measurements: Minimal pattern detection (30%)
        - 10-20 measurements: Moderate confidence in pattern (60%)
        - 20-40 measurements: Strong pattern confidence (85%)
        - 40+ measurements: Very robust pattern detection (95%)

        Args:
            n_measurements (int): Count of historical vital sign measurements

        Returns:
            Tuple[float, str]: Confidence score (0-100), explanation string
        """
        if n_measurements < 5:
            score = 10.0
            reason = "Critical: Insufficient data (< 5 measurements)"
        elif n_measurements < 10:
            score = 30.0
            reason = "Warning: Limited data (5-10 measurements)"
        elif n_measurements < 20:
            score = 60.0
            reason = "Acceptable: Moderate data (10-20 measurements)"
        elif n_measurements < 40:
            score = 85.0
            reason = "Good: Substantial data (20-40 measurements)"
        else:
            score = 95.0
            reason = "Excellent: Abundant data (40+ measurements)"

        return score, reason

    def calculate_model_agreement_score(
        self,
        ensemble_forecast: float,
        individual_predictions: Dict[str, float]
    ) -> Tuple[float, str]:
        """
        Factor 2: Measure consensus among the 5 regression methods.

        The question: Do all our forecasting methods arrive at similar predictions?

        When all five methods (ARIMA, exponential smoothing, linear trend, etc.)
        predict similar values, this is strong evidence the pattern is robust
        and the data is clear. When methods heavily disagree, it indicates
        ambiguous or noisy data that's hard to forecast reliably.

        Deviation metric: Calculate mean percent difference from ensemble average.
        - < 2%: Near-perfect agreement (95% confidence)
        - 2-5%: Good consensus (85% confidence)
        - 5-10%: Acceptable diversity (70% confidence)
        - 10-15%: Significant disagreement (50% confidence)
        - > 15%: Major disagreement - data is ambiguous (30% confidence)

        Args:
            ensemble_forecast (float): Combined weighted prediction
            individual_predictions (Dict): Predictions from each of 5 methods

        Returns:
            Tuple[float, str]: Agreement score (0-100), detailed reasoning
        """
        if not individual_predictions:
            return 50.0, "Unknown: No predictions to compare"

        predictions = list(individual_predictions.values())

        # Calculate how far each method is from ensemble
        deviations = [abs(p - ensemble_forecast) for p in predictions]
        mean_deviation = np.mean(deviations)

        # Scale deviation as percentage of ensemble value
        if ensemble_forecast != 0:
            pct_deviation = (mean_deviation / abs(ensemble_forecast)) * 100
        else:
            pct_deviation = mean_deviation

        # Score based on deviation percentage
        if pct_deviation < 2:
            score = 95.0
            reason = f"Excellent agreement: All methods within 2% ({pct_deviation:.1f}%)"
        elif pct_deviation < 5:
            score = 85.0
            reason = f"Good agreement: Methods within 5% ({pct_deviation:.1f}%)"
        elif pct_deviation < 10:
            score = 70.0
            reason = f"Moderate agreement: Methods within 10% ({pct_deviation:.1f}%)"
        elif pct_deviation < 15:
            score = 50.0
            reason = f"Poor agreement: Methods within 15% ({pct_deviation:.1f}%)"
        else:
            score = 30.0
            reason = f"Very poor agreement: Methods differ significantly ({pct_deviation:.1f}%)"

        return score, reason

    def calculate_extrapolation_score(
        self,
        forecast: float,
        measurements: List[float]
    ) -> Tuple[float, str]:
        """
        Factor 3: Assess extrapolation distance (is forecast within historical range?).

        Predictions outside observed range are risky.

        Args:
            forecast (float): The ensemble forecast
            measurements (List[float]): Historical measurements

        Returns:
            Tuple[float, str]: Score (0-100), reasoning
        """
        data = np.array(measurements, dtype=np.float64)

        # Calculate historical range
        min_val = np.min(data)
        max_val = np.max(data)
        mean_val = np.mean(data)
        std_val = np.std(data)

        # Check if forecast is within range
        if min_val <= forecast <= max_val:
            score = 95.0
            reason = f"Within range: Forecast {forecast:.2f} between observed range ({min_val:.2f}-{max_val:.2f})"

        # Check if within ±1 std
        elif (mean_val - std_val) <= forecast <= (mean_val + std_val):
            score = 80.0
            reason = f"Near range: Forecast within ±1 std of mean"

        # Check if within ±2 std
        elif (mean_val - 2*std_val) <= forecast <= (mean_val + 2*std_val):
            score = 50.0
            reason = f"Outside range: Forecast {forecast:.2f} exceeds ±1 std but within ±2 std"

        else:
            score = 20.0
            reason = f"Risky extrapolation: Forecast {forecast:.2f} beyond ±2 std ({mean_val:.2f} ± {std_val:.2f})"

        return score, reason

    def calculate_stability_score(self, measurements: List[float]) -> Tuple[float, str]:
        """
        Factor 4: Evaluate patient stability as predictor of forecast reliability.

        The question: Is this patient's condition stable or highly variable?

        This factor carries 30% weight (highest) because patient stability is
        the strongest predictor of forecast accuracy. Stable patients follow
        predictable patterns. Unstable patients experience sudden changes that
        defy pattern detection.

        Measurement: Coefficient of Variation (CV) = StdDev / Mean
        This normalized metric accounts for different vital sign scales:

        Stability thresholds:
        - CV < 0.05 (5%): Excellent stability, highly predictable (95%)
        - CV < 0.08 (8%): Good stability, consistent patterns (85%)
        - CV < 0.12 (12%): Acceptable stability (70%)
        - CV < 0.15 (15%): Poor stability, variable patterns (50%)
        - CV > 0.15: Unstable patient, chaotic vital signs (35%)

        Args:
            measurements (List[float]): Time-ordered historical vital signs

        Returns:
            Tuple[float, str]: Stability score (0-100), interpretation string
        """
        data = np.array(measurements, dtype=np.float64)

        # Coefficient of variation normalizes variation relative to mean
        # Allows fair comparison across different vital sign types (HR vs temp)
        mean_val = np.mean(data)
        std_val = np.std(data)

        if mean_val == 0:
            cv = 0
        else:
            cv = std_val / mean_val

        # Interpret coefficient of variation
        if cv < 0.05:
            score = 95.0
            reason = f"Excellent stability: Very low variation (CV = {cv:.3f})"
        elif cv < 0.08:
            score = 85.0
            reason = f"Good stability: Low variation (CV = {cv:.3f})"
        elif cv < 0.12:
            score = 70.0
            reason = f"Acceptable stability: Moderate variation (CV = {cv:.3f})"
        elif cv < 0.15:
            score = 50.0
            reason = f"Poor stability: High variation (CV = {cv:.3f})"
        else:
            score = 35.0
            reason = f"Unstable patient: Very high variation (CV = {cv:.3f})"

        return score, reason

    def calculate_confidence(
        self,
        measurements: List[float],
        ensemble_forecast: float,
        individual_predictions: Dict[str, float]
    ) -> ConfidenceScore:
        """
        Combine all four confidence factors into single explainable score.

        This is the core of our Explainable AI system. We evaluate four
        independent dimensions of forecast reliability, weight them by
        importance for healthcare applications, and produce:
        1. Overall confidence percentage (0-100%)
        2. Individual factor scores (for transparency)
        3. Confidence level (HIGH/MEDIUM/LOW) for clinical workflow
        4. Natural language reasoning (why this confidence)

        Weighting rationale:
        - Stability (30%): Patient variability most critical for predictability
        - Data Volume (25%): Need sufficient history for pattern detection
        - Model Agreement (25%): Consensus indicates robust patterns
        - Extrapolation (20%): Predictions within range are safer

        Confidence thresholds for clinical action:
        - HIGH (≥90%): System can trigger automatic alerts
        - MEDIUM (70-89%): Require nurse to manually review before alert
        - LOW (<70%): Information only, no automatic escalation

        Args:
            measurements (List[float]): Patient's historical vital signs
            ensemble_forecast (float): Combined prediction from all methods
            individual_predictions (Dict): Predictions from each of 5 methods

        Returns:
            ConfidenceScore: Complete confidence assessment with reasoning

        Example:
            Patient has 50 measurements (excellent), methods within 3% (excellent),
            forecast within range (excellent), CV=0.06 (excellent) →
            Confidence = 0.25(95) + 0.25(95) + 0.20(95) + 0.30(95) = 95% HIGH
        """
        # Step 1: Evaluate each confidence dimension independently
        data_volume_score, data_volume_reason = self.calculate_data_volume_score(len(measurements))
        model_agreement_score, agreement_reason = self.calculate_model_agreement_score(
            ensemble_forecast, individual_predictions
        )
        extrapolation_score, extrapolation_reason = self.calculate_extrapolation_score(
            ensemble_forecast, measurements
        )
        stability_score, stability_reason = self.calculate_stability_score(measurements)

        # Step 2: Combine factors using weighted average (weights sum to 1.0)
        overall = (
            0.25 * data_volume_score +      # 25% weight: sufficient historical data
            0.25 * model_agreement_score +  # 25% weight: methods reach consensus
            0.20 * extrapolation_score +    # 20% weight: forecast within safe range
            0.30 * stability_score          # 30% weight: patient is stable/predictable
        )

        # Step 3: Classify overall confidence into clinical decision level
        if overall >= 90:
            level = 'HIGH'
        elif overall >= 70:
            level = 'MEDIUM'
        else:
            level = 'LOW'

        # Create detailed reasoning
        reasoning = f"""
CONFIDENCE BREAKDOWN (Overall: {overall:.1f}%):

1. DATA VOLUME (25% weight = {0.25*data_volume_score:.1f}):
   {data_volume_reason}

2. MODEL AGREEMENT (25% weight = {0.25*model_agreement_score:.1f}):
   {agreement_reason}

3. EXTRAPOLATION DISTANCE (20% weight = {0.20*extrapolation_score:.1f}):
   {extrapolation_reason}

4. STABILITY (30% weight = {0.30*stability_score:.1f}):
   {stability_reason}

CLINICAL RECOMMENDATION:
- HIGH ({overall:.1f}%) - Use as alert trigger
- Alert automatically if vital sign exceeds threshold
- Monitor and document

---

- MEDIUM (70-89%) - Manual review recommended
- Check if prediction makes clinical sense
- Alert only if clinician approves

---

- LOW (<70%) - Information only
- Do not trigger automatic alerts
- Requires manual patient assessment
"""

        confidence_score = ConfidenceScore(
            overall=overall,
            data_volume=data_volume_score,
            model_agreement=model_agreement_score,
            extrapolation_distance=extrapolation_score,
            stability=stability_score,
            level=level,
            reasoning=reasoning.strip()
        )

        self.confidence_score = confidence_score
        return confidence_score

    def get_json_report(self, confidence_score: ConfidenceScore) -> Dict:
        """
        Get machine-readable JSON report.

        Args:
            confidence_score (ConfidenceScore): Calculated confidence

        Returns:
            Dict: JSON-serializable report
        """
        return {
            'overall_confidence': round(confidence_score.overall, 2),
            'confidence_level': confidence_score.level,
            'factors': {
                'data_volume': round(confidence_score.data_volume, 2),
                'model_agreement': round(confidence_score.model_agreement, 2),
                'extrapolation_distance': round(confidence_score.extrapolation_distance, 2),
                'stability': round(confidence_score.stability, 2)
            },
            'weights': {
                'data_volume_weight': 0.25,
                'model_agreement_weight': 0.25,
                'extrapolation_weight': 0.20,
                'stability_weight': 0.30
            },
            'clinical_action': self._get_clinical_action(confidence_score.level)
        }

    @staticmethod
    def _get_clinical_action(confidence_level: str) -> str:
        """Get recommended clinical action based on confidence level."""
        actions = {
            'HIGH': 'Automatic alert trigger permitted',
            'MEDIUM': 'Manual review recommended before alert',
            'LOW': 'Information only, manual assessment required'
        }
        return actions.get(confidence_level, 'Unknown')
