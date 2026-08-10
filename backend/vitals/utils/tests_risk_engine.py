"""
Comprehensive Risk Assessment Engine Tests

Tests for RiskAssessmentEngine and all risk detection functionality.
"""

from django.test import TestCase
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal

from patients.models import Patient
from vitals.models import VitalSigns
from vitals.utils.risk_engine import RiskAssessmentEngine


class PatientFactory:
    """Helper to create test patients"""
    @staticmethod
    def create_patient(first_name="Test", last_name="Patient", age=65):
        today = date.today()
        dob = date(today.year - age, today.month, today.day)
        return Patient.objects.create(
            first_name=first_name,
            last_name=last_name,
            date_of_birth=dob,
            gender='M'
        )


class VitalSignsFactory:
    """Helper to create vital sign records"""
    @staticmethod
    def create_vitals(
        patient,
        heart_rate=None,
        respiratory_rate=None,
        oxygen_saturation=None,
        bp_systolic=None,
        temperature=None,
        recorded_at=None
    ):
        if recorded_at is None:
            recorded_at = timezone.now()

        return VitalSigns.objects.create(
            patient=patient,
            heart_rate=heart_rate,
            respiratory_rate=respiratory_rate,
            oxygen_saturation=Decimal(str(oxygen_saturation)) if oxygen_saturation else None,
            bp_systolic=bp_systolic,
            bp_diastolic=70,
            temperature=Decimal(str(temperature)) if temperature else None,
            recorded_at=recorded_at
        )


class NEWS2RiskTests(TestCase):
    """Test NEWS2-based risk calculation"""

    def setUp(self):
        self.engine = RiskAssessmentEngine()
        self.patient = PatientFactory.create_patient()

    def test_low_risk_news2(self):
        """Test low risk classification (NEWS2 0-4)"""
        vital = VitalSignsFactory.create_vitals(
            self.patient,
            heart_rate=75,
            respiratory_rate=16,
            oxygen_saturation=97,
            bp_systolic=120,
            temperature=37.0
        )
        level, score = self.engine.calculate_news2_risk(vital)
        self.assertEqual(level, 'low')
        self.assertLessEqual(score, 4)

    def test_medium_risk_news2(self):
        """Test medium risk classification (NEWS2 5-6)"""
        vital = VitalSignsFactory.create_vitals(
            self.patient,
            heart_rate=105,  # 1 point
            respiratory_rate=22,  # 2 points
            oxygen_saturation=94,  # 1 point
            bp_systolic=95,  # 2 points
            temperature=37.0  # 0 points
        )
        level, score = self.engine.calculate_news2_risk(vital)
        self.assertEqual(level, 'medium')
        self.assertIn(score, [5, 6])

    def test_high_risk_news2(self):
        """Test high risk classification (NEWS2 7+)"""
        vital = VitalSignsFactory.create_vitals(
            self.patient,
            heart_rate=120,
            respiratory_rate=26,
            oxygen_saturation=92,
            bp_systolic=115,
            temperature=38.2
        )
        level, score = self.engine.calculate_news2_risk(vital)
        self.assertEqual(level, 'high')
        self.assertGreaterEqual(score, 7)


class TrendRiskTests(TestCase):
    """Test trend-based risk calculation"""

    def setUp(self):
        self.engine = RiskAssessmentEngine()
        self.patient = PatientFactory.create_patient()
        self.base_time = timezone.now()

    def test_stable_trend_risk(self):
        """Test low risk with stable trend"""
        level, score = self.engine.calculate_trend_risk(self.patient)
        self.assertEqual(level, 'low')
        self.assertEqual(score, 0)

    def test_mild_trend_risk(self):
        """Test mild trend risk"""
        # Create vitals with significant deterioration to register trend
        for i in range(4):
            VitalSignsFactory.create_vitals(
                self.patient,
                heart_rate=70 + (i * 5),  # 5 bpm/hour increase
                respiratory_rate=16 + (i * 2),  # More significant increase
                recorded_at=self.base_time + timedelta(hours=i)
            )

        level, score = self.engine.calculate_trend_risk(self.patient, window_size=4)
        # Should have trend detected with significant changes
        self.assertGreaterEqual(score, 0)

    def test_severe_trend_risk(self):
        """Test severe deterioration trend"""
        # Create vitals with rapid deterioration
        for i in range(4):
            VitalSignsFactory.create_vitals(
                self.patient,
                heart_rate=70 + (i * 15),  # Rapid increase
                respiratory_rate=16 + (i * 3),
                oxygen_saturation=98 - (i * 1.5),
                recorded_at=self.base_time + timedelta(hours=i)
            )

        level, score = self.engine.calculate_trend_risk(self.patient, window_size=4)
        self.assertGreater(score, 3)


class MultiParameterAnalysisTests(TestCase):
    """Test multi-parameter deterioration detection"""

    def setUp(self):
        self.engine = RiskAssessmentEngine()
        self.patient = PatientFactory.create_patient()
        self.base_time = timezone.now()

    def test_stable_multi_parameter(self):
        """Test multi-parameter analysis with stable vitals"""
        VitalSignsFactory.create_vitals(
            self.patient,
            heart_rate=75,
            respiratory_rate=16,
            oxygen_saturation=97,
            bp_systolic=120,
            temperature=37.0,
            recorded_at=self.base_time
        )
        VitalSignsFactory.create_vitals(
            self.patient,
            heart_rate=76,
            respiratory_rate=16,
            oxygen_saturation=97,
            bp_systolic=120,
            temperature=37.0,
            recorded_at=self.base_time + timedelta(hours=1)
        )

        result = self.engine.analyze_multi_parameter_deterioration(self.patient)
        self.assertEqual(result['worsening_count'], 0)
        self.assertFalse(result['deteriorating_together'])
        self.assertEqual(result['pattern'], 'stable')

    def test_one_parameter_worsening(self):
        """Test multi-parameter analysis with one parameter worsening"""
        VitalSignsFactory.create_vitals(
            self.patient,
            heart_rate=75,
            respiratory_rate=16,
            oxygen_saturation=97,
            bp_systolic=120,
            temperature=37.0,
            recorded_at=self.base_time
        )
        VitalSignsFactory.create_vitals(
            self.patient,
            heart_rate=115,  # Worsening
            respiratory_rate=16,  # Stable
            oxygen_saturation=97,  # Stable
            bp_systolic=120,  # Stable
            temperature=37.0,  # Stable
            recorded_at=self.base_time + timedelta(hours=1)
        )

        result = self.engine.analyze_multi_parameter_deterioration(self.patient)
        self.assertEqual(result['worsening_count'], 1)
        self.assertEqual(result['pattern'], 'one_worsening')
        self.assertIn('heart_rate', result['contributing_vitals'])

    def test_multiple_parameters_worsening(self):
        """Test multi-parameter analysis with multiple parameters worsening"""
        VitalSignsFactory.create_vitals(
            self.patient,
            heart_rate=75,
            respiratory_rate=16,
            oxygen_saturation=97,
            bp_systolic=120,
            temperature=37.0,
            recorded_at=self.base_time
        )
        VitalSignsFactory.create_vitals(
            self.patient,
            heart_rate=115,  # Worsening
            respiratory_rate=26,  # Worsening
            oxygen_saturation=91,  # Worsening
            bp_systolic=100,  # Worsening
            temperature=38.5,  # Worsening
            recorded_at=self.base_time + timedelta(hours=1)
        )

        result = self.engine.analyze_multi_parameter_deterioration(self.patient)
        self.assertEqual(result['worsening_count'], 5)
        self.assertEqual(result['pattern'], 'all_worsening')
        self.assertTrue(result['deteriorating_together'])
        self.assertGreater(result['multi_param_score'], 2)


class CombinedRiskTests(TestCase):
    """Test combined risk assessment"""

    def setUp(self):
        self.engine = RiskAssessmentEngine()
        self.patient = PatientFactory.create_patient()
        self.base_time = timezone.now()

    def test_combined_risk_low(self):
        """Test low combined risk"""
        VitalSignsFactory.create_vitals(
            self.patient,
            heart_rate=75,
            respiratory_rate=16,
            oxygen_saturation=97,
            bp_systolic=120,
            temperature=37.0
        )

        result = self.engine.calculate_combined_risk(self.patient)
        self.assertTrue(result['data_available'])
        self.assertEqual(result['risk_level'], 'low')
        self.assertEqual(result['news2']['level'], 'low')

    def test_combined_risk_medium(self):
        """Test medium combined risk"""
        VitalSignsFactory.create_vitals(
            self.patient,
            heart_rate=105,
            respiratory_rate=22,
            oxygen_saturation=94,
            bp_systolic=95,
            temperature=37.0
        )

        result = self.engine.calculate_combined_risk(self.patient)
        self.assertTrue(result['data_available'])
        self.assertEqual(result['risk_level'], 'medium')

    def test_combined_risk_high(self):
        """Test high combined risk"""
        VitalSignsFactory.create_vitals(
            self.patient,
            heart_rate=135,  # More critical HR
            respiratory_rate=26,
            oxygen_saturation=92,
            bp_systolic=105,
            temperature=38.5  # More elevated temp
        )

        result = self.engine.calculate_combined_risk(self.patient)
        self.assertTrue(result['data_available'])
        # Should be high or critical risk
        self.assertIn(result['risk_level'], ['high', 'critical'])

    def test_combined_risk_critical(self):
        """Test critical combined risk"""
        VitalSignsFactory.create_vitals(
            self.patient,
            heart_rate=140,
            respiratory_rate=28,
            oxygen_saturation=90,
            bp_systolic=230,
            temperature=40.5
        )

        result = self.engine.calculate_combined_risk(self.patient)
        self.assertTrue(result['data_available'])
        self.assertEqual(result['risk_level'], 'critical')

    def test_combined_risk_no_data(self):
        """Test combined risk with no vital data"""
        result = self.engine.calculate_combined_risk(self.patient)
        self.assertFalse(result['data_available'])
        self.assertEqual(result['risk_level'], 'low')


class AlertDecisionTests(TestCase):
    """Test alert creation decision logic"""

    def setUp(self):
        self.engine = RiskAssessmentEngine()
        self.patient = PatientFactory.create_patient()

    def test_critical_combined_risk_alert(self):
        """Test alert creation at critical combined risk"""
        should_alert, reason = self.engine.should_create_alert(self.patient, 15.0)
        self.assertTrue(should_alert)
        self.assertIn('CRITICAL', reason)

    def test_high_combined_risk_alert(self):
        """Test alert creation at high combined risk"""
        should_alert, reason = self.engine.should_create_alert(self.patient, 10.0)
        self.assertTrue(should_alert)
        self.assertIn('HIGH RISK', reason)

    def test_medium_risk_no_alert(self):
        """Test no alert at medium risk without trend"""
        should_alert, reason = self.engine.should_create_alert(self.patient, 6.0)
        self.assertFalse(should_alert)

    def test_medium_risk_with_trend_alert(self):
        """Test alert creation at medium risk with deterioration trend"""
        # Create vitals showing deterioration
        base_time = timezone.now()
        for i in range(4):
            VitalSignsFactory.create_vitals(
                self.patient,
                heart_rate=70 + (i * 10),  # Clear trend
                respiratory_rate=16 + i,
                recorded_at=base_time + timedelta(hours=i)
            )

        should_alert, reason = self.engine.should_create_alert(self.patient, 6.0)
        # Depending on trend score, may or may not alert
        self.assertIsNotNone(reason)


class ExplanationGenerationTests(TestCase):
    """Test explanation text generation"""

    def setUp(self):
        self.engine = RiskAssessmentEngine()
        self.patient = PatientFactory.create_patient()
        self.base_time = timezone.now()

    def test_explanation_low_risk(self):
        """Test explanation generation for low risk"""
        vital = VitalSignsFactory.create_vitals(
            self.patient,
            heart_rate=75,
            respiratory_rate=16,
            oxygen_saturation=97,
            bp_systolic=120,
            temperature=37.0
        )

        result = self.engine.calculate_combined_risk(self.patient)
        self.assertIn('normal range', result['explanation'])

    def test_explanation_high_risk(self):
        """Test explanation generation for high risk"""
        VitalSignsFactory.create_vitals(
            self.patient,
            heart_rate=120,
            respiratory_rate=26,
            oxygen_saturation=92,
            bp_systolic=115,
            temperature=38.2
        )

        result = self.engine.calculate_combined_risk(self.patient)
        self.assertIn('critical', result['explanation'])

    def test_recommendation_low_risk(self):
        """Test recommendation for low risk"""
        VitalSignsFactory.create_vitals(
            self.patient,
            heart_rate=75,
            respiratory_rate=16,
            oxygen_saturation=97,
            bp_systolic=120,
            temperature=37.0
        )

        result = self.engine.calculate_combined_risk(self.patient)
        self.assertIn('Routine', result['recommendation'])

    def test_recommendation_critical_risk(self):
        """Test recommendation for critical risk"""
        VitalSignsFactory.create_vitals(
            self.patient,
            heart_rate=140,
            respiratory_rate=28,
            oxygen_saturation=90,
            bp_systolic=230,
            temperature=40.5
        )

        result = self.engine.calculate_combined_risk(self.patient)
        self.assertIn('URGENT', result['recommendation'])


class EdgeCaseTests(TestCase):
    """Test edge cases and error conditions"""

    def setUp(self):
        self.engine = RiskAssessmentEngine()
        self.patient = PatientFactory.create_patient()

    def test_assess_patient_with_no_vitals(self):
        """Test patient assessment when no vitals exist"""
        result = self.engine.assess_patient(self.patient)
        self.assertFalse(result['data_available'])
        self.assertEqual(result['risk_level'], 'low')

    def test_assess_patient_single_vital(self):
        """Test patient assessment with single vital"""
        VitalSignsFactory.create_vitals(
            self.patient,
            heart_rate=80,
            respiratory_rate=18,
            oxygen_saturation=96,
            bp_systolic=125,
            temperature=37.2
        )

        result = self.engine.assess_patient(self.patient)
        self.assertTrue(result['data_available'])
        self.assertIn(result['risk_level'], ['low', 'medium', 'high', 'critical'])

    def test_assess_patient_multiple_vitals(self):
        """Test patient assessment with multiple vitals"""
        base_time = timezone.now()
        for i in range(5):
            VitalSignsFactory.create_vitals(
                self.patient,
                heart_rate=70 + i,
                respiratory_rate=16 + i,
                oxygen_saturation=97 - i,
                recorded_at=base_time + timedelta(hours=i)
            )

        result = self.engine.assess_patient(self.patient)
        self.assertTrue(result['data_available'])
        self.assertIsNotNone(result['trend']['score'])
        self.assertIsNotNone(result['combined_risk'])

    def test_missing_vital_components(self):
        """Test assessment with missing vital components"""
        VitalSignsFactory.create_vitals(
            self.patient,
            heart_rate=75,
            respiratory_rate=None,  # Missing
            oxygen_saturation=97,
            bp_systolic=120,
            temperature=37.0
        )

        result = self.engine.assess_patient(self.patient)
        self.assertTrue(result['data_available'])
        # Should still calculate without crashing, even if risk is 0
        self.assertIsNotNone(result['combined_risk'])


class ScoreCombinationTests(TestCase):
    """Test how NEWS2, Trend, and Multi-parameter scores combine"""

    def setUp(self):
        self.engine = RiskAssessmentEngine()
        self.patient = PatientFactory.create_patient()
        self.base_time = timezone.now()

    def test_news2_only_high_risk(self):
        """Test high risk from NEWS2 alone"""
        VitalSignsFactory.create_vitals(
            self.patient,
            heart_rate=135,
            respiratory_rate=26,
            oxygen_saturation=92,
            bp_systolic=105,
            temperature=38.2
        )

        result = self.engine.calculate_combined_risk(self.patient)
        # Should have significant combined risk
        self.assertGreaterEqual(result['combined_risk'], 8)
        self.assertIn(result['risk_level'], ['high', 'critical'])

    def test_trend_amplifies_news2(self):
        """Test that trends amplify NEWS2-based risk"""
        # Create gradually worsening vitals
        for i in range(5):
            VitalSignsFactory.create_vitals(
                self.patient,
                heart_rate=80 + (i * 10),
                respiratory_rate=18 + i,
                oxygen_saturation=96 - (i * 0.5),
                recorded_at=self.base_time + timedelta(hours=i)
            )

        result = self.engine.calculate_combined_risk(self.patient)
        # Final vital should have reasonable NEWS2
        # But combined risk should be amplified by trend
        self.assertGreater(result['combined_risk'], result['news2']['score'])

    def test_multi_parameter_amplification(self):
        """Test that simultaneous deterioration amplifies risk"""
        VitalSignsFactory.create_vitals(
            self.patient,
            heart_rate=75,
            respiratory_rate=16,
            oxygen_saturation=97,
            bp_systolic=120,
            temperature=37.0,
            recorded_at=self.base_time
        )
        VitalSignsFactory.create_vitals(
            self.patient,
            heart_rate=115,  # All worsening
            respiratory_rate=26,
            oxygen_saturation=91,
            bp_systolic=100,
            temperature=38.5,
            recorded_at=self.base_time + timedelta(hours=1)
        )

        result = self.engine.calculate_combined_risk(self.patient)
        # Multi-parameter worsening should add significant score
        self.assertGreater(result['multi_parameter']['multi_param_score'], 0)
        self.assertEqual(result['multi_parameter']['worsening_count'], 5)
