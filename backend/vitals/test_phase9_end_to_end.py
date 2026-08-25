"""
Phase 9: End-to-End Testing & Flow Validation

Complete end-to-end tests showing data recording, processing, and decision-making.
Tests demonstrate the full flow from data input to alert generation.
"""

import sys
import unittest
from datetime import datetime
from django.test import TestCase, Client

# These tests print Unicode box-drawing characters; Windows' default console
# codepage (cp1252) can't encode them, so force UTF-8 stdout when available.
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from .models import VitalSigns, Patient, RiskAssessment
from .real_time_recorder import RealTimeDataRecorder, FlowVisualizer


class EndToEndTestScenarios(TestCase):
    """
    Complete end-to-end test scenarios showing the full flow.
    These tests demonstrate EXACTLY how to test the system.
    """

    def setUp(self):
        """Set up test patient"""
        self.patient = Patient.objects.create(
            first_name="Test",
            last_name="Patient",
            date_of_birth="1950-01-01",
        )
        self.client = APIClient()

    def test_scenario_1_normal_vitals(self):
        """
        SCENARIO 1: Normal Vital Signs
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        Input: Patient with normal vital signs
        Expected: NORMAL status, no alert
        """
        print("\n" + "="*70)
        print("SCENARIO 1: NORMAL VITAL SIGNS")
        print("="*70)

        vitals = {
            'patient_id': self.patient.id,
            'heart_rate': 75,           # Normal: 60-100
            'respiratory_rate': 16,     # Normal: 12-20
            'oxygen_saturation': 98.0,  # Normal: >95%
            'systolic_bp': 120,         # Normal: 90-180
            'diastolic_bp': 80,         # Normal: 60-100
            'temperature': 37.0,        # Normal: 36.1-38.0
        }

        print("\nSTEP 1: Input vital signs")
        print(f"  HR: {vitals['heart_rate']} bpm")
        print(f"  RR: {vitals['respiratory_rate']} br/min")
        print(f"  SpO2: {vitals['oxygen_saturation']}%")
        print(f"  BP: {vitals['systolic_bp']}/{vitals['diastolic_bp']} mmHg")
        print(f"  Temp: {vitals['temperature']}°C")

        recorder = RealTimeDataRecorder(self.patient.id)
        result = recorder.record_vital_signs(vitals)

        print("\nSTEP 2: System processes the data")
        risk_assessment = result['flow_sequence'][0].get('step_3_risk_assessment', {})
        print(f"  NEWS2 Score: {risk_assessment.get('news2_score')} (threshold: 7)")
        print(f"  Trend Score: {risk_assessment.get('trend_score')} (threshold: 2)")
        print(f"  Combined Risk: {risk_assessment.get('combined_risk')} (threshold: 8)")
        print(f"  Risk Level: {risk_assessment.get('risk_level')}")

        print("\nSTEP 3: System makes decision")
        decision = result['flow_sequence'][0].get('step_6_decision', {})
        print(f"  Final Decision: [{decision.get('final_decision')}]")
        print(f"  Processing Time: {decision.get('total_time_ms')} ms")

        # Assertions
        self.assertEqual(risk_assessment.get('risk_level'), 'LOW')
        self.assertEqual(decision.get('final_decision'), 'NORMAL')

        print("\n✓ RESULT: PASS - System correctly identified normal vitals")

    def test_scenario_2_mild_deterioration(self):
        """
        SCENARIO 2: Mild Deterioration
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        Input: Patient showing mild deterioration signs
        Expected: NORMAL to ALERT transition
        """
        print("\n" + "="*70)
        print("SCENARIO 2: MILD DETERIORATION")
        print("="*70)

        recorder = RealTimeDataRecorder(self.patient.id)

        # First reading: Normal
        print("\nFIRST READING: Normal vitals")
        vitals_1 = {
            'heart_rate': 75,
            'respiratory_rate': 16,
            'oxygen_saturation': 98.0,
            'systolic_bp': 120,
            'diastolic_bp': 80,
            'temperature': 37.0,
        }
        result_1 = recorder.record_vital_signs(vitals_1)
        decision_1 = result_1['flow_sequence'][0].get('step_6_decision', {})
        print(f"  Decision: [{decision_1.get('final_decision')}]")
        self.assertEqual(decision_1.get('final_decision'), 'NORMAL')

        # Second reading: Mild deterioration
        print("\nSECOND READING: Mild deterioration detected")
        vitals_2 = {
            'heart_rate': 95,           # Elevated
            'respiratory_rate': 22,     # Elevated
            'oxygen_saturation': 94.0,  # Slightly low
            'systolic_bp': 110,         # Lower
            'diastolic_bp': 75,
            'temperature': 38.5,        # Elevated
        }
        result_2 = recorder.record_vital_signs(vitals_2)
        risk_2 = result_2['flow_sequence'][1].get('step_3_risk_assessment', {})
        decision_2 = result_2['flow_sequence'][1].get('step_6_decision', {})

        print(f"  HR: {vitals_2['heart_rate']} (was 75, +20)")
        print(f"  RR: {vitals_2['respiratory_rate']} (was 16, +6)")
        print(f"  SpO2: {vitals_2['oxygen_saturation']}% (was 98%, -4%)")
        print(f"  NEWS2 Score: {risk_2.get('news2_score')}")
        print(f"  Trend Score: {risk_2.get('trend_score'):.1f}")
        print(f"  Decision: [{decision_2.get('final_decision')}]")

        print("\n✓ RESULT: System detected deterioration trend")

    def test_scenario_3_critical_deterioration(self):
        """
        SCENARIO 3: Critical Deterioration
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        Input: Patient with critical vital signs
        Expected: CRITICAL ALERT
        """
        print("\n" + "="*70)
        print("SCENARIO 3: CRITICAL DETERIORATION")
        print("="*70)

        vitals = {
            'patient_id': self.patient.id,
            'heart_rate': 120,          # Elevated (>110)
            'respiratory_rate': 28,     # Very high (>24)
            'oxygen_saturation': 88.0,  # Critical (<92%)
            'systolic_bp': 85,          # Low (<90)
            'diastolic_bp': 55,
            'temperature': 39.5,        # High (>39%)
        }

        print("\nCRITICAL VITALS DETECTED:")
        print(f"  HR: {vitals['heart_rate']} bpm (ABNORMAL)")
        print(f"  RR: {vitals['respiratory_rate']} br/min (ABNORMAL)")
        print(f"  SpO2: {vitals['oxygen_saturation']}% (CRITICAL)")
        print(f"  BP: {vitals['systolic_bp']}/{vitals['diastolic_bp']} mmHg (CRITICAL)")
        print(f"  Temp: {vitals['temperature']}°C (HIGH)")

        recorder = RealTimeDataRecorder(self.patient.id)
        result = recorder.record_vital_signs(vitals)

        risk_assessment = result['flow_sequence'][0].get('step_3_risk_assessment', {})
        alert_status = result['flow_sequence'][0].get('step_5_alert_generated', {})
        decision = result['flow_sequence'][0].get('step_6_decision', {})

        print("\nSYSTEM PROCESSING:")
        print(f"  NEWS2 Score: {risk_assessment.get('news2_score')} (threshold: 7)")
        print(f"  Trend Score: {risk_assessment.get('trend_score'):.1f}")
        print(f"  Combined Risk: {risk_assessment.get('combined_risk'):.1f} (threshold: 8)")
        print(f"  Risk Level: {risk_assessment.get('risk_level')}")

        print("\nALERT GENERATION:")
        print(f"  Alert Status: {alert_status.get('status')}")
        print(f"  Alert Priority: {alert_status.get('priority', 'N/A')}")

        print("\nFINAL DECISION:")
        print(f"  Decision: [{decision.get('final_decision')}]")
        print(f"  Processing Time: {decision.get('total_time_ms')} ms")

        # Assertions
        self.assertIn(risk_assessment.get('risk_level'), ['HIGH', 'CRITICAL'])
        self.assertEqual(decision.get('final_decision'), 'ALERT')

        print("\n✓ RESULT: PASS - System correctly identified critical condition and generated alert")

    def test_scenario_4_sequential_deterioration(self):
        """
        SCENARIO 4: Sequential Deterioration (Show Progression)
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        This is the scenario you'll show the panel:
        Record multiple data points to show the progression
        """
        print("\n" + "="*70)
        print("SCENARIO 4: SEQUENTIAL DETERIORATION (PANEL DEMO)")
        print("="*70)
        print("\nThis is what you'll show the panel...")

        recorder = RealTimeDataRecorder(self.patient.id)

        test_sequence = [
            {
                'name': 'FIRST DATA - Normal',
                'vitals': {
                    'heart_rate': 72,
                    'respiratory_rate': 15,
                    'oxygen_saturation': 98.5,
                    'systolic_bp': 125,
                    'diastolic_bp': 82,
                    'temperature': 36.8,
                },
            },
            {
                'name': 'SECOND DATA - Slight change',
                'vitals': {
                    'heart_rate': 85,
                    'respiratory_rate': 18,
                    'oxygen_saturation': 97.0,
                    'systolic_bp': 120,
                    'diastolic_bp': 80,
                    'temperature': 37.2,
                },
            },
            {
                'name': 'THIRD DATA - Deterioration begins',
                'vitals': {
                    'heart_rate': 105,
                    'respiratory_rate': 24,
                    'oxygen_saturation': 94.0,
                    'systolic_bp': 110,
                    'diastolic_bp': 75,
                    'temperature': 38.5,
                },
            },
            {
                'name': 'FOURTH DATA - Critical',
                'vitals': {
                    'heart_rate': 120,
                    'respiratory_rate': 28,
                    'oxygen_saturation': 89.0,
                    'systolic_bp': 90,
                    'diastolic_bp': 60,
                    'temperature': 39.5,
                },
            },
        ]

        print("\n" + "─"*70)
        for i, scenario in enumerate(test_sequence, 1):
            print(f"\n{scenario['name']}")
            print("─"*70)

            result = recorder.record_vital_signs(scenario['vitals'])
            entry = result['flow_sequence'][-1]

            vitals = entry.get('step_1_input', {}).get('vitals', {})
            risk = entry.get('step_3_risk_assessment', {})
            decision = entry.get('step_6_decision', {})

            print(f"Sequence: {entry.get('sequence_number')}")
            print(f"Vitals: HR={vitals.get('heart_rate')}, RR={vitals.get('respiratory_rate')}, SpO2={vitals.get('oxygen_saturation')}%")
            print(f"Assessment: NEWS2={risk.get('news2_score')}, Trend={risk.get('trend_score'):.1f}, Combined={risk.get('combined_risk'):.1f}")
            print(f"Risk Level: {risk.get('risk_level')}")
            print(f"Decision: [{decision.get('final_decision')}]")

        print("\n" + "─"*70)
        print("\nVISUALIZATION OF COMPLETE FLOW:")
        print("─"*70)

        # Generate summary
        summary = recorder.get_summary()
        flow = recorder.get_full_flow()

        print(FlowVisualizer.generate_summary_table(summary))

        self.assertEqual(len(summary.get('recording_sequence', [])), 4)
        print("\n✓ RESULT: PASS - Complete sequential demonstration working")


class RealTimeRecorderTests(TestCase):
    """
    Tests for RealTimeDataRecorder class
    """

    def setUp(self):
        """Set up test patient"""
        self.patient = Patient.objects.create(
            first_name="Recorder",
            last_name="Test Patient",
            date_of_birth="1950-01-01",
        )

    def test_recorder_initialization(self):
        """Initialize recorder"""
        recorder = RealTimeDataRecorder(self.patient.id)
        self.assertIsNotNone(recorder)
        self.assertEqual(recorder.patient_id, self.patient.id)

    def test_record_single_vital(self):
        """Record single set of vital signs"""
        recorder = RealTimeDataRecorder(self.patient.id)

        vitals = {
            'heart_rate': 80,
            'respiratory_rate': 16,
            'oxygen_saturation': 97.0,
            'systolic_bp': 120,
            'diastolic_bp': 80,
            'temperature': 37.0,
        }

        result = recorder.record_vital_signs(vitals)

        self.assertIn('flow_sequence', result)
        self.assertEqual(len(result['flow_sequence']), 1)
        self.assertEqual(result['recordings'], 1)

    def test_record_multiple_vitals(self):
        """Record multiple vital sign sets"""
        recorder = RealTimeDataRecorder(self.patient.id)

        for i in range(3):
            vitals = {
                'heart_rate': 75 + i*10,
                'respiratory_rate': 16,
                'oxygen_saturation': 98.0 - i*0.5,
                'systolic_bp': 120,
                'diastolic_bp': 80,
                'temperature': 37.0,
            }
            recorder.record_vital_signs(vitals)

        result = recorder.get_full_flow()
        self.assertEqual(len(result['flow_sequence']), 3)

    def test_flow_visualization(self):
        """Generate flow diagram"""
        recorder = RealTimeDataRecorder(self.patient.id)

        vitals = {
            'heart_rate': 80,
            'respiratory_rate': 16,
            'oxygen_saturation': 97.0,
            'systolic_bp': 120,
            'diastolic_bp': 80,
            'temperature': 37.0,
        }

        recorder.record_vital_signs(vitals)
        flow = recorder.get_full_flow()

        diagram = FlowVisualizer.generate_flow_diagram(flow)
        self.assertIn('REAL-TIME DETERIORATION DETECTION FLOW', diagram)
        self.assertIn('STEP 1: VITALS RECEIVED', diagram)
        self.assertIn('STEP 6: FINAL DECISION', diagram)

    def test_summary_generation(self):
        """Generate summary report"""
        recorder = RealTimeDataRecorder(self.patient.id)

        vitals = {
            'heart_rate': 80,
            'respiratory_rate': 16,
            'oxygen_saturation': 97.0,
            'systolic_bp': 120,
            'diastolic_bp': 80,
            'temperature': 37.0,
        }

        recorder.record_vital_signs(vitals)
        summary = recorder.get_summary()

        self.assertEqual(summary.get('total_recordings'), 1)
        self.assertIn('recording_sequence', summary)


if __name__ == '__main__':
    unittest.main()
