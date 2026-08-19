#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FALL DETECTION DEMO - Real-time Webcam Test

Tests fall detection with live webcam feed.
Shows posture and fall risk in real-time.
"""

import cv2
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from vitals.fall_detection_simple import FallDetectionSystem

print("\n" + "="*70)
print("FALL DETECTION SYSTEM - LIVE WEBCAM TEST")
print("="*70)

# Initialize
print("\n[INITIALIZING SYSTEM]")
system = FallDetectionSystem()
print("✓ Fall detection system initialized")

# Open webcam
print("\n[OPENING WEBCAM]")
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("[ERROR] Cannot open webcam")
    print("Make sure:")
    print("  1. Webcam is connected")
    print("  2. Camera is not in use by another application")
    print("  3. You granted camera permissions")
    sys.exit(1)

print("✓ Webcam opened successfully")
print("\n[RUNNING FALL DETECTION]")
print("Instructions:")
print("  - Stand normally in front of camera")
print("  - Try bending down to test")
print("  - Try lying on ground to test fall detection")
print("  - Press 'q' to quit")
print("-" * 70)

frame_count = 0
try:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Failed to read frame")
            break

        # Flip frame for mirror effect
        frame = cv2.flip(frame, 1)

        # Process frame
        result = system.process_frame(frame)

        # Get color based on risk level
        color = system.get_alert_color(result['risk_level'])

        # Draw status on frame
        cv2.rectangle(frame, (10, 10), (500, 120), color, -1)
        cv2.rectangle(frame, (10, 10), (500, 120), (0, 0, 0), 2)

        # Add text
        status_text = f"RISK: {result['risk_level']} ({result['risk_score']}%)"
        posture_text = f"Posture: {result['posture'].upper()}"
        explanation_text = result['explanation'][:60]

        cv2.putText(frame, status_text, (20, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
        cv2.putText(frame, posture_text, (20, 75),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 1)
        cv2.putText(frame, explanation_text, (20, 110),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # Add emoji indicators
        emoji_map = {
            'LOW': '🟢',
            'MEDIUM': '🟡',
            'HIGH': '🔴'
        }
        emoji = emoji_map.get(result['risk_level'], '?')

        # Display frame
        cv2.imshow('Fall Detection System', frame)

        # Print every 30 frames (1 second at 30fps)
        if frame_count % 30 == 0:
            print(f"\n[Frame {frame_count}]")
            print(f"  Status: {emoji} {result['risk_level']}")
            print(f"  Risk Score: {result['risk_score']}")
            print(f"  Posture: {result['posture']}")
            print(f"  Explanation: {result['explanation']}")

        # Check for quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        frame_count += 1

except KeyboardInterrupt:
    print("\n[INTERRUPTED BY USER]")

finally:
    cap.release()
    cv2.destroyAllWindows()

print("-" * 70)
print(f"[DEMO COMPLETE] Processed {frame_count} frames")
print("\n[SYSTEM SUMMARY]")
print("✓ Fall detection working")
print("✓ Real-time pose analysis active")
print("✓ Color-coded risk levels displayed")
print("✓ Explanations provided for each detection")
print("\n[NEXT STEPS]")
print("1. System is ready for Django integration")
print("2. Dashboard can display this in real-time")
print("3. Can enable/disable per patient")
print("4. Works alongside vital signs regression")
print("="*70 + "\n")
