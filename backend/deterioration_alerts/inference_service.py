"""
Deterioration Detection Inference Service

This module provides ML-based patient deterioration detection.
It loads a pre-trained model or uses a rule-based fallback.
"""

import os
import pickle
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class DeteriorationDetector:
    """
    Detects patient deterioration using ML or rule-based approach
    """

    def __init__(self):
        self.model = None
        self.use_ml = False
        self._load_model()

    def _load_model(self):
        """Attempt to load ML model, fallback to rule-based if not available"""
        try:
            model_path = os.path.join(settings.BASE_DIR, 'deterioration_model.pkl')
            if os.path.exists(model_path):
                with open(model_path, 'rb') as f:
                    self.model = pickle.load(f)
                self.use_ml = True
                logger.info("ML model loaded successfully")
            else:
                logger.warning(f"Model not found at {model_path}, using rule-based detection")
        except Exception as e:
            logger.warning(f"Failed to load model: {e}, using rule-based detection")

    def predict(self, vital_data):
        """
        Predict deterioration risk

        Args:
            vital_data (dict): Vital signs data with NEWS2 scores

        Returns:
            dict: Prediction with keys:
                - is_critical: bool
                - alert_level: str ('GREEN', 'YELLOW', 'AMBER', 'RED')
                - probability: float (0-1)
                - confidence: float (0-100)
        """
        if self.use_ml and self.model:
            return self._ml_predict(vital_data)
        else:
            return self._rule_based_predict(vital_data)

    def _ml_predict(self, vital_data):
        """ML-based prediction"""
        try:
            # If model exists, use it
            prediction = self.model.predict(vital_data)
            return prediction
        except Exception as e:
            logger.error(f"ML prediction failed: {e}, falling back to rules")
            return self._rule_based_predict(vital_data)

    def _rule_based_predict(self, vital_data):
        """
        Rule-based deterioration detection fallback
        Uses NEWS2 score and vital ranges
        """
        news2_total = vital_data.get('news2_total', 0)
        rr_score = vital_data.get('rr_score', 0)
        spo2_score = vital_data.get('spo2_score', 0)
        hr_score = vital_data.get('hr_score', 0)
        temp_score = vital_data.get('temp_score', 0)
        sbp_score = vital_data.get('sbp_score', 0)

        # Risk scoring logic
        alert_level = 'GREEN'  # Default
        probability = 0.0
        is_critical = False

        # NEWS2-based classification
        if news2_total >= 7:  # High risk threshold
            alert_level = 'RED'
            probability = 0.95
            is_critical = True
            confidence = 95
        elif news2_total >= 5:  # Medium-high risk
            alert_level = 'AMBER'
            probability = 0.75
            is_critical = False
            confidence = 75
        elif news2_total >= 3:  # Medium risk
            alert_level = 'YELLOW'
            probability = 0.5
            is_critical = False
            confidence = 50
        else:  # Low risk
            alert_level = 'GREEN'
            probability = 0.1
            is_critical = False
            confidence = 90

        # Additional checks for extreme values (RED flags)
        extreme_flags = 0
        if spo2_score >= 3:  # SpO2 <= 91%
            extreme_flags += 1
        if rr_score >= 3:  # RR <= 8 or >= 25
            extreme_flags += 1
        if hr_score >= 3:  # HR <= 40 or >= 130
            extreme_flags += 1
        if temp_score >= 3:  # Temp <= 35 or unknown
            extreme_flags += 1
        if sbp_score >= 3:  # SBP <= 90
            extreme_flags += 1

        # If multiple extreme flags, escalate to CRITICAL
        if extreme_flags >= 2:
            alert_level = 'RED'
            is_critical = True
            probability = 0.98
            confidence = 98

        return {
            'alert_level': alert_level,
            'probability': probability,
            'confidence': confidence,
            'is_critical': is_critical,
            'news2_score': news2_total,
        }


# Global detector instance
_detector = None


def get_detector():
    """
    Get or create the deterioration detector

    Returns:
        DeteriorationDetector: Singleton detector instance
    """
    global _detector
    if _detector is None:
        _detector = DeteriorationDetector()
    return _detector
