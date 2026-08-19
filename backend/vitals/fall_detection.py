"""
FALL DETECTION SYSTEM - Real-time Pose Analysis with Explainable AI

Uses MediaPipe for pose detection + simple classifier for fall risk assessment.
Provides explainability by showing which keypoints triggered detection.

Flow:
1. Webcam captures video frame
2. MediaPipe detects 17 body keypoints (skeleton)
3. Classifier analyzes posture and movement
4. Returns: posture_type, fall_risk_score, explanation
5. Dashboard shows real-time alert with reasoning
"""

import cv2
import numpy as np
from typing import Tuple, Dict, List
import logging
import mediapipe as mp

logger = logging.getLogger(__name__)


class PoseAnalyzer:
    """Analyze body pose using MediaPipe."""

    def __init__(self):
        """Initialize MediaPipe Pose."""
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=0,  # Lightweight
            smooth_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils

    def extract_keypoints(self, frame) -> Tuple[np.ndarray, bool]:
        """
        Extract 17 body keypoints from frame.

        Returns:
            keypoints: (17, 3) array of (x, y, confidence)
            success: True if pose detected
        """
        h, w, c = frame.shape
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(frame_rgb)

        if not results.pose_landmarks:
            return None, False

        # Extract keypoints
        keypoints = []
        for landmark in results.pose_landmarks.landmark:
            keypoints.append([landmark.x, landmark.y, landmark.visibility])

        return np.array(keypoints), True

    def draw_skeleton(self, frame, keypoints):
        """Draw skeleton on frame for visualization."""
        if keypoints is None:
            return frame

        h, w, c = frame.shape
        keypoints_px = keypoints.copy()
        keypoints_px[:, 0] *= w  # x to pixel
        keypoints_px[:, 1] *= h  # y to pixel

        # Draw keypoints
        for i, (x, y, conf) in enumerate(keypoints_px):
            if conf > 0.5:
                cv2.circle(frame, (int(x), int(y)), 5, (0, 255, 0), -1)

        # Draw skeleton connections (simplified)
        connections = [
            (0, 1), (1, 2), (2, 3),  # Head
            (5, 6), (6, 7), (7, 8),  # Right arm
            (9, 10), (10, 11), (11, 12),  # Left arm
            (11, 13), (13, 15),  # Left side
            (12, 14), (14, 16)  # Right side
        ]

        for start, end in connections:
            if keypoints[start, 2] > 0.5 and keypoints[end, 2] > 0.5:
                x1, y1 = int(keypoints_px[start, 0]), int(keypoints_px[start, 1])
                x2, y2 = int(keypoints_px[end, 0]), int(keypoints_px[end, 1])
                cv2.line(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        return frame


class FallRiskClassifier:
    """Classify fall risk from body pose."""

    def __init__(self):
        """Initialize classifier."""
        self.keypoint_names = [
            'nose', 'left_eye', 'right_eye', 'left_ear', 'right_ear',
            'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
            'left_wrist', 'right_wrist', 'left_hip', 'right_hip',
            'left_knee', 'right_knee', 'left_ankle', 'right_ankle'
        ]

    def calculate_body_angles(self, keypoints: np.ndarray) -> Dict:
        """
        Calculate key body angles for posture analysis.

        Returns angles for:
        - Torso tilt (forward bend)
        - Knee bend (standing vs bending)
        - Hip position (relative to shoulder)
        """
        angles = {}

        # Get key points
        l_shoulder = keypoints[5][:2]
        r_shoulder = keypoints[6][:2]
        l_hip = keypoints[11][:2]
        r_hip = keypoints[12][:2]
        l_knee = keypoints[13][:2]
        r_knee = keypoints[14][:2]
        l_ankle = keypoints[15][:2]
        r_ankle = keypoints[16][:2]

        # Torso tilt: angle between shoulder-hip line and vertical
        mid_shoulder = (l_shoulder + r_shoulder) / 2
        mid_hip = (l_hip + r_hip) / 2

        torso_vec = mid_hip - mid_shoulder
        torso_angle = np.arctan2(torso_vec[0], -torso_vec[1]) * 180 / np.pi
        angles['torso_tilt'] = abs(torso_angle)

        # Knee bend: angle at knee joint
        left_knee_angle = self._calculate_angle(l_hip, l_knee, l_ankle)
        right_knee_angle = self._calculate_angle(r_hip, r_knee, r_ankle)
        angles['left_knee_angle'] = left_knee_angle
        angles['right_knee_angle'] = right_knee_angle
        angles['avg_knee_angle'] = (left_knee_angle + right_knee_angle) / 2

        # Height ratio: how low is torso compared to shoulder-ankle distance
        torso_height = np.linalg.norm(mid_hip - mid_shoulder)
        ankle_height = np.linalg.norm(l_ankle - r_ankle)
        angles['torso_to_leg_ratio'] = torso_height / (ankle_height + 0.001)

        return angles

    def _calculate_angle(self, p1, p2, p3):
        """Calculate angle at p2 formed by p1-p2-p3."""
        v1 = p1 - p2
        v2 = p3 - p2

        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 0.001)
        cos_angle = np.clip(cos_angle, -1, 1)
        angle = np.arccos(cos_angle) * 180 / np.pi

        return angle

    def classify_posture(self, keypoints: np.ndarray) -> Tuple[str, float, str]:
        """
        Classify posture type and fall risk.

        Returns:
            posture: 'standing', 'sitting', 'bending', 'falling'
            risk_score: 0-100 (0=safe, 100=falling)
            explanation: Why this classification
        """
        if keypoints is None:
            return 'unknown', 0, 'No pose detected'

        # Check if enough keypoints visible
        visible_count = np.sum(keypoints[:, 2] > 0.5)
        if visible_count < 10:
            return 'unknown', 0, f'Only {visible_count} keypoints visible'

        # Get angles
        angles = self.calculate_body_angles(keypoints)

        torso_tilt = angles['torso_tilt']
        knee_angle = angles['avg_knee_angle']
        torso_leg_ratio = angles['torso_to_leg_ratio']

        # Classification logic
        risk_score = 0
        explanation_parts = []

        # Rule 1: Forward bend (torso tilt > 45°)
        if torso_tilt > 45:
            risk_score += 40
            explanation_parts.append(f"Body bent forward {torso_tilt:.0f}°")

        # Rule 2: Knees bent (angle < 90°)
        if knee_angle < 90:
            risk_score += 30
            explanation_parts.append(f"Knees bent {knee_angle:.0f}°")

        # Rule 3: Very low torso (ratio < 0.3)
        if torso_leg_ratio < 0.3:
            risk_score += 30
            explanation_parts.append("Body very low to ground")

        # Classify posture
        if risk_score > 70:
            posture = 'falling'
        elif risk_score > 50:
            posture = 'bending'
        elif knee_angle < 120:
            posture = 'sitting'
        else:
            posture = 'standing'

        if not explanation_parts:
            explanation = 'Patient standing upright'
        else:
            explanation = ' | '.join(explanation_parts)

        return posture, min(100, risk_score), explanation


class FallDetectionSystem:
    """Complete fall detection system with webcam integration."""

    def __init__(self):
        """Initialize system."""
        self.pose_analyzer = PoseAnalyzer()
        self.classifier = FallRiskClassifier()
        self.frame_buffer = []
        self.max_buffer_size = 5

    def process_frame(self, frame) -> Dict:
        """
        Process single video frame.

        Args:
            frame: Video frame from webcam

        Returns:
            {
                'posture': str (standing/sitting/bending/falling),
                'risk_score': float (0-100),
                'risk_level': str (LOW/MEDIUM/HIGH),
                'explanation': str (why this classification),
                'keypoints': array (for visualization),
                'success': bool
            }
        """
        # Extract pose
        keypoints, success = self.pose_analyzer.extract_keypoints(frame)

        if not success:
            return {
                'posture': 'unknown',
                'risk_score': 0,
                'risk_level': 'UNKNOWN',
                'explanation': 'No pose detected',
                'keypoints': None,
                'success': False
            }

        # Classify posture
        posture, risk_score, explanation = self.classifier.classify_posture(keypoints)

        # Determine risk level
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
            'keypoints': keypoints,
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
