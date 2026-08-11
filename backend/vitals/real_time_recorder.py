"""
Phase 9: Real-time Data Recording & Flow Visualization

Records vital signs in real-time and tracks the complete flow through
the deterioration detection system.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List
from django.core.cache import cache
from .models import VitalSigns, RiskAssessment
from deterioration_alerts.models import DeteriorationAlert
from .utils.risk_engine import RiskAssessmentEngine
from .utils.trend_engine import TrendAnalyzer

logger = logging.getLogger(__name__)


class RealTimeDataRecorder:
    """
    Records real-time vital signs and tracks flow through the system.
    """

    def __init__(self, patient_id: int):
        """Initialize recorder for a patient."""
        self.patient_id = patient_id
        self.flow_log = []
        self.start_time = datetime.now()

    def record_vital_signs(self, vitals: Dict) -> Dict:
        """
        Record vital signs and process through system.

        Args:
            vitals: {
                'heart_rate': float,
                'respiratory_rate': float,
                'oxygen_saturation': float,
                'systolic_bp': float,
                'diastolic_bp': float,
                'temperature': float,
            }

        Returns:
            Complete flow result with all decisions
        """
        elapsed = (datetime.now() - self.start_time).total_seconds()

        flow_entry = {
            'timestamp': datetime.now().isoformat(),
            'elapsed_seconds': elapsed,
            'sequence_number': len(self.flow_log) + 1,
            'step_1_input': {
                'status': 'RECEIVED',
                'vitals': vitals,
                'time': elapsed,
            },
        }

        self.flow_log.append(flow_entry)

        try:
            vital_obj = VitalSigns.objects.create(
                patient_id=self.patient_id,
                heart_rate=vitals.get('heart_rate'),
                respiratory_rate=vitals.get('respiratory_rate'),
                oxygen_saturation=vitals.get('oxygen_saturation'),
                systolic_bp=vitals.get('systolic_bp'),
                diastolic_bp=vitals.get('diastolic_bp'),
                temperature=vitals.get('temperature'),
            )

            flow_entry['step_2_stored'] = {
                'status': 'STORED_IN_DATABASE',
                'vital_id': vital_obj.id,
                'time': (datetime.now() - self.start_time).total_seconds(),
            }

            engine = RiskAssessmentEngine()
            risk_result = engine.assess_risk(vitals)

            flow_entry['step_3_risk_assessment'] = {
                'status': 'ASSESSED',
                'news2_score': risk_result.get('news2_score', 0),
                'trend_score': risk_result.get('trend_score', 0),
                'combined_risk': risk_result.get('combined_risk', 0),
                'risk_level': risk_result.get('risk_level', 'unknown'),
                'time': (datetime.now() - self.start_time).total_seconds(),
            }

            risk_obj = RiskAssessment.objects.create(
                vital_signs=vital_obj,
                news2_score=risk_result.get('news2_score', 0),
                trend_level=risk_result.get('trend_score', 0),
                multi_param_pattern=risk_result.get('combined_risk', 0),
                recommendation='Monitor',
            )

            flow_entry['step_4_risk_stored'] = {
                'status': 'RISK_RECORD_CREATED',
                'risk_id': risk_obj.id,
                'time': (datetime.now() - self.start_time).total_seconds(),
            }

            is_deteriorating = risk_result.get('risk_level') in ['HIGH', 'CRITICAL']

            if is_deteriorating:
                alert_obj = DeteriorationAlert.objects.create(
                    patient_id=self.patient_id,
                    alert_type='research_deterioration_detection',
                    priority='HIGH' if risk_result.get('risk_level') == 'HIGH' else 'CRITICAL',
                    message=f"Risk Level: {risk_result.get('risk_level')}",
                    risk_assessment=risk_obj,
                )

                flow_entry['step_5_alert_generated'] = {
                    'status': 'ALERT_CREATED',
                    'alert_id': alert_obj.id,
                    'priority': alert_obj.priority,
                    'message': alert_obj.message,
                    'time': (datetime.now() - self.start_time).total_seconds(),
                }
            else:
                flow_entry['step_5_alert_generated'] = {
                    'status': 'NO_ALERT',
                    'reason': f'Risk level {risk_result.get("risk_level")} below threshold',
                    'time': (datetime.now() - self.start_time).total_seconds(),
                }

            flow_entry['step_6_decision'] = {
                'status': 'COMPLETE',
                'final_decision': 'ALERT' if is_deteriorating else 'NORMAL',
                'confidence': risk_result.get('confidence', 0),
                'total_time_ms': int((datetime.now() - self.start_time).total_seconds() * 1000),
            }

            return self.get_full_flow()

        except Exception as e:
            flow_entry['error'] = {
                'status': 'ERROR',
                'message': str(e),
                'time': (datetime.now() - self.start_time).total_seconds(),
            }
            logger.error(f"Error recording vitals: {e}")
            return self.get_full_flow()

    def get_full_flow(self) -> Dict:
        """Get the complete flow log."""
        return {
            'patient_id': self.patient_id,
            'recordings': len(self.flow_log),
            'started_at': self.start_time.isoformat(),
            'flow_sequence': self.flow_log,
            'latest_reading': self.flow_log[-1] if self.flow_log else None,
        }

    def get_summary(self) -> Dict:
        """Get summary of all recordings."""
        if not self.flow_log:
            return {'patient_id': self.patient_id, 'recordings': 0}

        decisions = [entry.get('step_6_decision', {}) for entry in self.flow_log]
        alerts_generated = sum(
            1 for entry in self.flow_log
            if entry.get('step_5_alert_generated', {}).get('status') == 'ALERT_CREATED'
        )

        return {
            'patient_id': self.patient_id,
            'total_recordings': len(self.flow_log),
            'alerts_generated': alerts_generated,
            'total_time_seconds': (datetime.now() - self.start_time).total_seconds(),
            'recording_sequence': [
                {
                    'seq': entry.get('sequence_number'),
                    'vital_hr': entry.get('step_1_input', {}).get('vitals', {}).get('heart_rate'),
                    'vital_spo2': entry.get('step_1_input', {}).get('vitals', {}).get('oxygen_saturation'),
                    'news2': entry.get('step_3_risk_assessment', {}).get('news2_score'),
                    'trend': entry.get('step_3_risk_assessment', {}).get('trend_score'),
                    'combined': entry.get('step_3_risk_assessment', {}).get('combined_risk'),
                    'risk_level': entry.get('step_3_risk_assessment', {}).get('risk_level'),
                    'decision': entry.get('step_6_decision', {}).get('final_decision'),
                }
                for entry in self.flow_log
            ],
        }


class FlowVisualizer:
    """
    Visualizes the data flow through the system.
    """

    @staticmethod
    def generate_flow_diagram(flow_data: Dict) -> str:
        """Generate ASCII flow diagram showing the complete sequence."""
        diagram = f"""
╔══════════════════════════════════════════════════════════════════════════╗
║                    REAL-TIME DETERIORATION DETECTION FLOW                ║
║                          Patient ID: {flow_data.get('patient_id', 'Unknown')}                             ║
╚══════════════════════════════════════════════════════════════════════════╝

DATA RECORDING SEQUENCE ({flow_data.get('recordings', 0)} readings)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
        for entry in flow_data.get('flow_sequence', []):
            seq = entry.get('sequence_number', '?')
            timestamp = entry.get('timestamp', '?')
            vitals = entry.get('step_1_input', {}).get('vitals', {})
            risk = entry.get('step_3_risk_assessment', {})
            decision = entry.get('step_6_decision', {})

            diagram += f"""
┌─ READING #{seq} ({timestamp}) ─────────────────────────────────────────┐
│                                                                         │
│  STEP 1: VITALS RECEIVED                                              │
│  ├─ HR: {vitals.get('heart_rate', '?')} bpm                                          │
│  ├─ RR: {vitals.get('respiratory_rate', '?')} br/min                                       │
│  ├─ SpO2: {vitals.get('oxygen_saturation', '?')}%                                     │
│  └─ BP: {vitals.get('systolic_bp', '?')}/{vitals.get('diastolic_bp', '?')} mmHg                              │
│                                                                         │
│  STEP 2: STORED IN DATABASE ✓                                          │
│                                                                         │
│  STEP 3: RISK ASSESSMENT CALCULATED                                   │
│  ├─ NEWS2 Score: {risk.get('news2_score', '?')} points                                │
│  ├─ Trend Score: {risk.get('trend_score', '?'):.1f} points                              │
│  ├─ Combined Risk: {risk.get('combined_risk', '?'):.1f} points                         │
│  └─ Risk Level: {risk.get('risk_level', '?')}                                    │
│                                                                         │
│  STEP 4: RISK RECORD CREATED ✓                                        │
│                                                                         │
│  STEP 5: DECISION LOGIC                                                │
│  └─ {entry.get('step_5_alert_generated', {}).get('status', '?')}                       │
│                                                                         │
│  STEP 6: FINAL DECISION                                                │
│  └─ [{decision.get('final_decision', '?')}] Confidence: {decision.get('confidence', '?')}%              │
│      (Processing time: {decision.get('total_time_ms', '?')} ms)                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
"""

        return diagram

    @staticmethod
    def generate_summary_table(summary: Dict) -> str:
        """Generate summary table of all recordings."""
        table = f"""
╔══════════════════════════════════════════════════════════════════════════╗
║                         RECORDING SUMMARY                                ║
╚══════════════════════════════════════════════════════════════════════════╝

Patient ID: {summary.get('patient_id', 'Unknown')}
Total Recordings: {summary.get('total_recordings', 0)}
Alerts Generated: {summary.get('alerts_generated', 0)}
Total Time: {summary.get('total_time_seconds', 0):.1f} seconds

SEQUENCE OF READINGS:
┌────┬──────┬─────────┬───────┬────────┬──────────┬──────────┬──────────┐
│ #  │ HR   │ SpO2    │ NEWS2 │ Trend  │ Combined │ Risk Lvl │ Decision │
├────┼──────┼─────────┼───────┼────────┼──────────┼──────────┼──────────┤
"""
        for entry in summary.get('recording_sequence', []):
            seq = entry.get('seq', '?')
            hr = entry.get('vital_hr', '?')
            spo2 = entry.get('vital_spo2', '?')
            news2 = entry.get('news2', '?')
            trend = entry.get('trend', '?')
            combined = entry.get('combined', '?')
            risk = entry.get('risk_level', '?')
            decision = entry.get('decision', '?')

            table += f"│ {seq:2} │ {hr:>4} │ {spo2:>5}% │ {news2:>5} │ {trend:>6.1f} │ {combined:>8.1f} │ {risk:>8} │ {decision:>8} │\n"

        table += """└────┴──────┴─────────┴───────┴────────┴──────────┴──────────┴──────────┘

INTERPRETATION:
• HR: Heart Rate (60-100 normal)
• SpO2: Oxygen Saturation (>95% normal)
• NEWS2: Clinical score (0-20, <7 normal)
• Trend: Rate of change (<2 normal)
• Combined: NEWS2 + Trend×1.2 (<8 normal)
• Risk Level: LOW, MEDIUM, HIGH, CRITICAL
• Decision: NORMAL or ALERT
"""
        return table
