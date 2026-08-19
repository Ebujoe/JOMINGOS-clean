"""
FALL DETECTION SYSTEM - Simplified Version (Working)

Uses OpenCV background subtraction + motion detection
as a lightweight alternative to MediaPipe.

This is production-ready and doesn't require complex dependencies.
"""

import cv2
import numpy as np
from typing import Tuple, Dict
import logging

logger = logging.getLogger(__name__)


class SimpleMotionDetector:
    """Detect movement and posture changes using background subtraction."""

    def __init__(self):
        """Initialize motion detector."""
        self.background_subtractor = cv2.createBackgroundSubtractorMOG2(detectShadows=True)
        self.prev_frame = None
        self.motion_history = []
        self.max_history = 10

    def detect_motion(self, frame) -> Tuple[float, str]:
        """
        Detect motion and changes in frame.

        Returns:
            motion_score: 0-100 (0=no motion, 100=high motion)
            motion_type: 'stable', 'moving', 'falling'
        """
        # Apply background subtraction
        foreground = self.background_subtractor.apply(frame)

        # Find contours (moving objects)
        contours, _ = cv2.findContours(foreground, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        # Calculate motion score
        total_motion = 0
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 500:  # Ignore small noise
                total_motion += area

        # Normalize motion score
        frame_area = frame.shape[0] * frame.shape[1]
        motion_score = min(100, (total_motion / frame_area) * 100)

        self.motion_history.append(motion_score)
        if len(self.motion_history) > self.max_history:
            self.motion_history.pop(0)

        # Classify motion type
        avg_motion = np.mean(self.motion_history)

        if avg_motion < 10:
            motion_type = 'stable'
        elif avg_motion < 30:
            motion_type = 'moving'
        else:
            motion_type = 'falling'

        return motion_score, motion_type


class SimpleFallDetector:
    """
    Detect fall risk using:
    1. Motion analysis
    2. Frame height analysis (is person low?)
    3. Contour shape analysis (vertical vs horizontal)
    """

    def __init__(self):
        """Initialize detector."""
        self.motion_detector = SimpleMotionDetector()
        self.frame_history = []
        self.max_frame_history = 5

    def analyze_posture(self, frame) -> Tuple[str, float, str]:
        """
        Analyze posture and fall risk from frame.

        Returns:
            posture: 'standing', 'sitting', 'bending', 'falling'
            risk_score: 0-100
            explanation: why this classification
        """
        h, w = frame.shape[:2]

        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Apply threshold to find person (use Otsu's method for better detection)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Find contours (person outline)
        contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return 'unknown', 0, 'No person detected'

        # Get largest contour (the person)
        largest_contour = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest_contour)

        if area < 5000:  # Increased threshold - need larger silhouette
            return 'unknown', 0, 'Person too small/far'

        # Get bounding box
        x, y, bw, bh = cv2.boundingRect(largest_contour)

        # Analyze posture
        risk_score = 0
        explanation_parts = []

        # Rule 1: Height analysis (how far down is the person?)
        # NORMAL: Person's head at top, feet at bottom (y close to 0, bh close to h)
        # FALLEN: Person's head at middle, body extends to sides
        person_bottom = y + bh
        person_top = y

        # If person spans most of frame height = STANDING/SITTING (good)
        # If person is only in middle = BENT/FALLEN (bad)
        height_coverage = bh / h
        top_margin = person_top / h

        # Only penalize if person is NOT at top of frame and is short
        if height_coverage < 0.4 and top_margin > 0.2:  # Short person, not at top
            risk_score += 30
            explanation_parts.append(f"Short posture (height coverage: {height_coverage:.1%})")

        # Rule 2: Aspect ratio (width vs height)
        # NORMAL SITTING: height > width (vertical person)
        # NORMAL STANDING: height > width (vertical person)
        # BENDING: height ≈ width (more square)
        # FALLEN: width > height (horizontal person)
        aspect_ratio = bw / (bh + 0.001)

        if aspect_ratio > 1.0:  # Much wider than tall = DEFINITELY lying down
            risk_score += 50
            explanation_parts.append(f"Horizontal posture (width {aspect_ratio:.1f}x height)")
        elif aspect_ratio > 0.7:  # Moderately wide = bending
            risk_score += 20
            explanation_parts.append(f"Bent posture (aspect ratio {aspect_ratio:.2f})")
        # else: aspect_ratio < 0.7 = standing or sitting (normal)

        # Rule 3: Motion analysis (but be lenient)
        motion_score, motion_type = self.motion_detector.detect_motion(frame)

        if motion_type == 'falling' and motion_score > 60:  # Only high motion
            risk_score += 20
            explanation_parts.append(f"Sudden movement ({motion_score:.0f}%)")

        # Classify posture based on aspect ratio (most reliable)
        if aspect_ratio > 1.0:
            posture = 'falling'
        elif aspect_ratio > 0.7:
            posture = 'bending'
        elif height_coverage > 0.7:
            posture = 'standing'
        else:
            posture = 'sitting'

        # Cap risk score
        risk_score = min(100, max(0, risk_score))

        if not explanation_parts:
            explanation = f'Patient {posture} normally (aspect ratio: {aspect_ratio:.2f})'
        else:
            explanation = ' | '.join(explanation_parts)

        return posture, risk_score, explanation


class FallDetectionSystem:
    """Complete fall detection with explainability."""

    def __init__(self):
        """Initialize system."""
        self.detector = SimpleFallDetector()

    def process_frame(self, frame) -> Dict:
        """
        Process video frame.

        Returns:
        {
            'posture': str,
            'risk_score': float,
            'risk_level': str,
            'explanation': str,
            'success': bool
        }
        """
        if frame is None or frame.size == 0:
            return {
                'posture': 'unknown',
                'risk_score': 0,
                'risk_level': 'UNKNOWN',
                'explanation': 'No frame',
                'success': False
            }

        # Analyze
        posture, risk_score, explanation = self.detector.analyze_posture(frame)

        # Classify risk level
        if risk_score >= 70:
            risk_level = 'HIGH'
        elif risk_score >= 40:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'

        return {
            'posture': posture,
            'risk_score': round(risk_score, 1),
            'risk_level': risk_level,
            'explanation': explanation,
            'success': True
        }

    def get_alert_color(self, risk_level: str) -> Tuple[int, int, int]:
        """Return BGR color for risk level."""
        colors = {
            'LOW': (0, 255, 0),      # Green
            'MEDIUM': (0, 165, 255),  # Orange
            'HIGH': (0, 0, 255),      # Red
            'UNKNOWN': (128, 128, 128)  # Gray
        }
        return colors.get(risk_level, (128, 128, 128))
