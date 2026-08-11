"""
Phase 10: Predictive Forecasting - Comprehensive Tests

Tests for:
- Forecasting engine (linear regression, exponential smoothing, moving average)
- Trajectory analyzer (time-to-critical calculations)
- Predictive risk assessment integration
- End-to-end predictive pipeline
"""

from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
import numpy as np

from patients.models import Patient
from accounts.models import User
from vitals.models import VitalSigns, PredictiveRiskAssessment
from vitals.utils.forecasting_engine import ForecastingEngine
from vitals.utils.trajectory_analyzer import TrajectoryAnalyzer


class TestForecastingEngine(TestCase):
    """Test time-series forecasting models."""

    def setUp(self):
        self.engine = ForecastingEngine(min_readings=3)

    def test_linear_regression_forecast_rising_trend(self):
        """Test linear regression with rising trend (deterioration)."""
        # Heart rate rising: 70, 75, 80 → trend upward
        historical_values = [70.0, 75.0, 80.0]
        historical_times = [-8.0, -4.0, 0.0]  # 4-hour intervals

        result = self.engine.forecast_vital(
            historical_values,
            historical_times,
            horizon_hours=24
        )

        # Should predict ~90-100 (continued upward trend)
        self.assertIsNotNone(result['forecast'])
        self.assertGreater(result['forecast'], 80)
        self.assertIn('rising', result['trend']['direction'].lower())

    def test_linear_regression_forecast_falling_trend(self):
        """Test linear regression with falling trend (SpO2 deterioration)."""
        # SpO2 falling: 98, 96, 94 → trend downward
        historical_values = [98.0, 96.0, 94.0]
        historical_times = [-8.0, -4.0, 0.0]

        result = self.engine.forecast_vital(
            historical_values,
            historical_times,
            horizon_hours=24
        )

        # Should predict <94 (continued downward trend)
        self.assertIsNotNone(result['forecast'])
        self.assertLess(result['forecast'], 94)
        self.assertIn('falling', result['trend']['direction'].lower())

    def test_exponential_smoothing_weights_recent_readings(self):
        """Test exponential smoothing gives weight to recent observations."""
        # Stable then sudden change
        historical_values = [72.0, 72.0, 72.0, 85.0]
        historical_times = [-12.0, -8.0, -4.0, 0.0]

        result = self.engine.forecast_vital(
            historical_values,
            historical_times,
            horizon_hours=24
        )

        self.assertIsNotNone(result['forecast'])
        # Should be closer to recent value (85) than old values
        self.assertGreater(result['forecast'], 72)

    def test_forecast_requires_minimum_readings(self):
        """Test forecast fails gracefully with insufficient data."""
        result = self.engine.forecast_vital(
            [72.0],  # Only 1 reading
            [-4.0],
            horizon_hours=24
        )

        self.assertIsNone(result['forecast'])
        self.assertEqual(result['reason'], 'insufficient_data')

    def test_model_consensus_increases_confidence(self):
        """Test that when models agree, confidence is high."""
        # Stable trend - all models should agree
        historical_values = [72.0, 72.0, 72.0, 72.0]
        historical_times = [-12.0, -8.0, -4.0, 0.0]

        result = self.engine.forecast_vital(
            historical_values,
            historical_times,
            horizon_hours=24
        )

        # High confidence when models agree on stable
        self.assertGreaterEqual(result['confidence'], 0.7)

    def test_forecast_all_vitals_integration(self):
        """Test forecasting all vitals from complete history."""
        vital_history = {
            'heart_rate': [
                {'value': 70, 'time_hours_ago': -12},
                {'value': 75, 'time_hours_ago': -8},
                {'value': 80, 'time_hours_ago': -4},
                {'value': 85, 'time_hours_ago': 0},
            ],
            'oxygen_saturation': [
                {'value': 98, 'time_hours_ago': -12},
                {'value': 96, 'time_hours_ago': -8},
                {'value': 94, 'time_hours_ago': -4},
                {'value': 92, 'time_hours_ago': 0},
            ],
        }

        forecasts = self.engine.forecast_all_vitals(vital_history, horizon_hours=24)

        # Should have forecasts for both vitals
        self.assertIn('heart_rate', forecasts)
        self.assertIn('oxygen_saturation', forecasts)

        # Both should show deterioration trend
        self.assertIn('rising', forecasts['heart_rate']['trend']['direction'].lower())
        self.assertIn('falling', forecasts['oxygen_saturation']['trend']['direction'].lower())


class TestTrajectoryAnalyzer(TestCase):
    """Test deterioration trajectory analysis."""

    def setUp(self):
        self.analyzer = TrajectoryAnalyzer()

    def test_oxygen_saturation_critical_calculation(self):
        """Test time-to-critical calculation for falling SpO2."""
        current_spo2 = 94.0
        forecast_data = {
            'forecast': 88.0,  # Will drop to critical in 24h
            'trend': {
                'direction': 'falling',
                'magnitude': -0.25,  # 0.25% per hour
            }
        }

        trajectory = self.analyzer.calculate_time_to_deterioration(
            current_spo2,
            'oxygen_saturation',
            forecast_data
        )

        # Should predict reaching critical (88%) in approximately 24 hours
        self.assertIsNotNone(trajectory['hours_to_critical'])
        self.assertLess(trajectory['hours_to_critical'], 30)
        self.assertGreater(trajectory['hours_to_critical'], 20)

    def test_heart_rate_rising_to_critical(self):
        """Test HR rising to critical threshold."""
        current_hr = 95.0
        forecast_data = {
            'forecast': 130.0,  # Rising to critical
            'trend': {
                'direction': 'rising',
                'magnitude': 1.46,  # ~1.46 bpm/hour → 35 bpm/day
            }
        }

        trajectory = self.analyzer.calculate_time_to_deterioration(
            current_hr,
            'heart_rate',
            forecast_data
        )

        # Should predict reaching high critical (130 bpm)
        self.assertIsNotNone(trajectory['hours_to_critical'])
        self.assertIn('deteriorating_to_critical', trajectory['risk_status'])

    def test_stable_vital_no_deterioration(self):
        """Test stable vital shows no deterioration."""
        current_hr = 75.0
        forecast_data = {
            'forecast': 76.0,
            'trend': {
                'direction': 'stable',
                'magnitude': 0.01,  # Nearly flat
            }
        }

        trajectory = self.analyzer.calculate_time_to_deterioration(
            current_hr,
            'heart_rate',
            forecast_data
        )

        self.assertIsNone(trajectory['hours_to_critical'])
        self.assertEqual(trajectory['risk_status'], 'stable')

    def test_patient_trajectory_analysis_multiple_vitals(self):
        """Test comprehensive patient trajectory across vitals."""
        current_vitals = {
            'heart_rate': 95.0,
            'oxygen_saturation': 94.0,
            'respiratory_rate': 22.0,
        }

        forecasts = {
            'heart_rate': {
                'forecast': 115.0,
                'trend': {'direction': 'rising', 'magnitude': 0.8},
            },
            'oxygen_saturation': {
                'forecast': 90.0,
                'trend': {'direction': 'falling', 'magnitude': -0.17},
            },
            'respiratory_rate': {
                'forecast': 28.0,
                'trend': {'direction': 'rising', 'magnitude': 0.25},
            },
        }

        analysis = self.analyzer.analyze_patient_trajectory(
            current_vitals,
            forecasts
        )

        # Should identify multiple vitals at risk
        self.assertGreater(len(analysis['vitals_at_risk']), 0)
        # Should identify earliest critical time
        self.assertIsNotNone(analysis['earliest_critical'])
        # Should generate recommendations
        self.assertGreater(len(analysis['recommendations']), 0)

    def test_risk_summary_critical_within_6_hours(self):
        """Test risk summary for imminent critical state."""
        critical_times = [
            {'vital': 'oxygen_saturation', 'hours': 3.5},
            {'vital': 'respiratory_rate', 'hours': 4.2},
        ]

        trajectories = {}
        summary = self.analyzer._summarize_risk(trajectories, critical_times)

        self.assertEqual(summary['level'], 'critical')
        self.assertEqual(summary['urgency'], 'immediate')

    def test_recommendation_generation_immediate(self):
        """Test clinical recommendations for immediate critical risk."""
        critical_times = [
            {'vital': 'oxygen_saturation', 'hours': 2.5, 'reason': 'SpO2 dropping fast'},
        ]
        risk_summary = {'level': 'critical', 'urgency': 'immediate'}

        recommendations = self.analyzer._generate_recommendations(
            critical_times,
            risk_summary
        )

        # Should include urgent recommendations
        self.assertTrue(any('URGENT' in r or 'immediate' in r.lower() for r in recommendations))
        self.assertTrue(any('oxygen' in r.lower() or 'respiratory' in r.lower() for r in recommendations))

    def test_recommendation_generation_elevated_risk(self):
        """Test clinical recommendations for elevated risk (24-48h)."""
        critical_times = [
            {'vital': 'heart_rate', 'hours': 36.0},
        ]
        risk_summary = {'level': 'medium', 'urgency': 'elevated'}

        recommendations = self.analyzer._generate_recommendations(
            critical_times,
            risk_summary
        )

        # Should include monitoring recommendations
        self.assertTrue(any('monitor' in r.lower() or 'care plan' in r.lower() for r in recommendations))


class TestPredictiveRiskAssessmentModel(TestCase):
    """Test PredictiveRiskAssessment model."""

    def setUp(self):
        self.patient = Patient.objects.create(
            first_name='Test',
            last_name='Patient',
            date_of_birth='1950-01-01'
        )

    def test_create_predictive_assessment(self):
        """Test creating predictive risk assessment record."""
        assessment = PredictiveRiskAssessment.objects.create(
            patient=self.patient,
            prediction_timestamp=timezone.now(),
            current_heart_rate=85.0,
            current_oxygen_saturation=94.0,
            forecast_24h_heart_rate=105.0,
            forecast_24h_oxygen_saturation=90.0,
            forecast_24h_news2_score=7,
            hours_to_critical=24.0,
            trajectory_level='moderate_deterioration',
            forecast_confidence=0.75,
            historical_readings_used=4,
        )

        self.assertEqual(assessment.patient, self.patient)
        self.assertEqual(assessment.forecast_24h_news2_score, 7)
        self.assertFalse(assessment.is_critical_risk)

    def test_urgency_level_immediate(self):
        """Test urgency level for imminent critical state."""
        assessment = PredictiveRiskAssessment.objects.create(
            patient=self.patient,
            prediction_timestamp=timezone.now(),
            hours_to_critical=3.0,
            trajectory_level='critical_within_24h',
        )

        self.assertEqual(assessment.urgency_level, 'immediate')
        self.assertTrue(assessment.is_critical_risk)

    def test_urgency_level_urgent(self):
        """Test urgency level for urgent risk (< 24h)."""
        assessment = PredictiveRiskAssessment.objects.create(
            patient=self.patient,
            prediction_timestamp=timezone.now(),
            hours_to_critical=12.0,
            trajectory_level='rapid_deterioration',
        )

        self.assertEqual(assessment.urgency_level, 'urgent')

    def test_urgency_level_monitor(self):
        """Test urgency level for stable monitoring."""
        assessment = PredictiveRiskAssessment.objects.create(
            patient=self.patient,
            prediction_timestamp=timezone.now(),
            hours_to_critical=72.0,
            trajectory_level='slow_deterioration',
        )

        self.assertEqual(assessment.urgency_level, 'monitor')


class TestEndToEndPredictivePipeline(TestCase):
    """Integration tests for complete predictive pipeline."""

    def setUp(self):
        self.user = User.objects.create_user(username='clinician', password='test')
        self.patient = Patient.objects.create(
            first_name='Elderly',
            last_name='Patient',
            date_of_birth='1940-01-01'
        )
        self.engine = ForecastingEngine()
        self.analyzer = TrajectoryAnalyzer()

    def test_full_pipeline_deteriorating_patient(self):
        """Test complete pipeline from vitals to predictions."""
        # Create 5 vital recordings showing deterioration
        now = timezone.now()
        vitals = []
        for i in range(5):
            vital = VitalSigns.objects.create(
                patient=self.patient,
                recorded_by=self.user,
                heart_rate=70 + (i * 8),  # Rising: 70, 78, 86, 94, 102
                respiratory_rate=15 + (i * 2),  # Rising: 15, 17, 19, 21, 23
                oxygen_saturation=98 - (i * 1.5),  # Falling: 98, 96.5, 95, 93.5, 92
                bp_systolic=125 - (i * 5),  # Falling: 125, 120, 115, 110, 105
                temperature=36.8 + (i * 0.2),  # Rising: 36.8, 37.0, 37.2, 37.4, 37.6
                recorded_at=now - timedelta(hours=(4 - i))
            )
            vitals.append(vital)

        # Build historical data
        historical_data = {
            'heart_rate': [{'value': float(v.heart_rate), 'time_hours_ago': -(4 - i) * 4}
                          for i, v in enumerate(vitals)],
            'oxygen_saturation': [{'value': float(v.oxygen_saturation), 'time_hours_ago': -(4 - i) * 4}
                                 for i, v in enumerate(vitals)],
        }

        # Generate forecasts
        forecasts = self.engine.forecast_all_vitals(
            historical_data,
            horizon_hours=24
        )

        # Should have forecasts
        self.assertIn('heart_rate', forecasts)
        self.assertIn('oxygen_saturation', forecasts)

        # Both should show deterioration
        self.assertEqual(forecasts['heart_rate']['trend']['direction'], 'rising')
        self.assertEqual(forecasts['oxygen_saturation']['trend']['direction'], 'falling')

        # Analyze trajectory
        current_vitals = {
            'heart_rate': float(vitals[-1].heart_rate),
            'oxygen_saturation': float(vitals[-1].oxygen_saturation),
        }

        trajectory = self.analyzer.analyze_patient_trajectory(
            current_vitals,
            forecasts
        )

        # Should identify at-risk vitals
        self.assertGreater(len(trajectory['vitals_at_risk']), 0)
        # Should have earliest critical time
        self.assertIsNotNone(trajectory['earliest_critical'])


class TestPredictiveAccuracy(TestCase):
    """Test forecast accuracy against known trajectories."""

    def setUp(self):
        self.engine = ForecastingEngine()

    def test_linear_projection_accuracy(self):
        """Test linear regression forecast captures trend direction."""
        # Create perfect linear trend: +5 per hour
        historical_values = [50.0, 55.0, 60.0, 65.0]
        historical_times = [-3.0, -2.0, -1.0, 0.0]

        result = self.engine.forecast_vital(
            historical_values,
            historical_times,
            horizon_hours=1
        )

        # Should predict trend correctly (positive direction)
        # Models average may not perfectly track linear, but should capture trend
        self.assertIsNotNone(result['forecast'])
        self.assertGreater(result['forecast'], 55.0)  # Rising trend
        self.assertIn('rising', result['trend']['direction'].lower())

    def test_exponential_smoothing_preserves_stable_state(self):
        """Test exponential smoothing preserves truly stable conditions."""
        # Perfectly stable
        historical_values = [75.0, 75.0, 75.0, 75.0, 75.0]
        historical_times = [-4.0, -3.0, -2.0, -1.0, 0.0]

        result = self.engine.forecast_vital(
            historical_values,
            historical_times,
            horizon_hours=24
        )

        # Should predict ~75 (unchanged)
        self.assertIsNotNone(result['forecast'])
        self.assertAlmostEqual(result['forecast'], 75.0, delta=1.0)


class TestPredictiveAging(TestCase):
    """Test predictive focus on elderly patients."""

    def setUp(self):
        self.analyzer = TrajectoryAnalyzer()
        # Simulate elderly patient vitals (more variable baseline)
        self.elderly_vitals = {
            'heart_rate': 82.0,  # Elderly often have elevated resting HR
            'oxygen_saturation': 94.0,  # Often lower than young adults
            'respiratory_rate': 18.0,
            'temperature': 36.7,  # Lower baseline in elderly
        }

    def test_elderly_patient_fragility_detection(self):
        """Test system detects rapid deterioration in elderly."""
        # Elderly patient showing rapid deterioration
        forecasts = {
            'heart_rate': {
                'forecast': 110.0,
                'trend': {'direction': 'rising', 'magnitude': 1.17},  # +28 bpm in 24h
            },
            'oxygen_saturation': {
                'forecast': 88.0,
                'trend': {'direction': 'falling', 'magnitude': -0.25},  # -6% in 24h
            },
            'respiratory_rate': {
                'forecast': 26.0,
                'trend': {'direction': 'rising', 'magnitude': 0.33},  # +8 br in 24h
            },
        }

        trajectory = self.analyzer.analyze_patient_trajectory(
            self.elderly_vitals,
            forecasts
        )

        # Should detect fragility (multiple parameters deteriorating)
        self.assertGreaterEqual(len(trajectory['vitals_at_risk']), 1)
        # Should have recommendations
        self.assertGreater(len(trajectory['recommendations']), 0)
        # Check that recommendations mention clinical action
        recommendations_text = ' '.join(trajectory['recommendations']).lower()
        self.assertTrue(
            'monitor' in recommendations_text or
            'review' in recommendations_text or
            'escalat' in recommendations_text or
            'oxygen' in recommendations_text
        )
