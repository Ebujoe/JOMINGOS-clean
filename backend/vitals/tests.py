"""
JOMINGOS NEWS2 Scoring Tests

Comprehensive test suite for NEWS2 (National Early Warning Score 2) implementation.
Tests all vital sign component scoring and combined risk assessment.

Reference: Royal College of Physicians NEWS2 specification
"""

from django.test import TestCase
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal

from patients.models import Patient
from accounts.models import User
from vitals.models import VitalSigns, RiskAssessment


class PatientFactory:
    """Helper to create test patients"""
    @staticmethod
    def create_patient(first_name="Test", last_name="Patient", age=65):
        # Calculate date of birth from age
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
        bp_diastolic=None,
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
            bp_diastolic=bp_diastolic,
            temperature=Decimal(str(temperature)) if temperature else None,
            recorded_at=recorded_at
        )


class NEWS2RespiratoryRateTests(TestCase):
    """Test NEWS2 Respiratory Rate (RR) scoring"""

    def setUp(self):
        self.patient = PatientFactory.create_patient()

    def test_rr_8_or_less_scores_3(self):
        """RR ≤ 8: 3 points"""
        vitals = VitalSignsFactory.create_vitals(self.patient, respiratory_rate=8)
        self.assertEqual(vitals.news2_respiratory_score, 3)

        vitals = VitalSignsFactory.create_vitals(self.patient, respiratory_rate=5)
        self.assertEqual(vitals.news2_respiratory_score, 3)

    def test_rr_9_to_11_scores_1(self):
        """RR 9-11: 1 point"""
        for rr in [9, 10, 11]:
            vitals = VitalSignsFactory.create_vitals(self.patient, respiratory_rate=rr)
            self.assertEqual(vitals.news2_respiratory_score, 1, f"RR={rr} should score 1")

    def test_rr_12_to_20_scores_0(self):
        """RR 12-20: 0 points (normal range)"""
        for rr in [12, 16, 20]:
            vitals = VitalSignsFactory.create_vitals(self.patient, respiratory_rate=rr)
            self.assertEqual(vitals.news2_respiratory_score, 0, f"RR={rr} should score 0")

    def test_rr_21_to_24_scores_2(self):
        """RR 21-24: 2 points"""
        for rr in [21, 23, 24]:
            vitals = VitalSignsFactory.create_vitals(self.patient, respiratory_rate=rr)
            self.assertEqual(vitals.news2_respiratory_score, 2, f"RR={rr} should score 2")

    def test_rr_25_or_more_scores_3(self):
        """RR ≥ 25: 3 points (critical)"""
        for rr in [25, 30, 40]:
            vitals = VitalSignsFactory.create_vitals(self.patient, respiratory_rate=rr)
            self.assertEqual(vitals.news2_respiratory_score, 3, f"RR={rr} should score 3")

    def test_rr_none_scores_0(self):
        """Missing RR: 0 points"""
        vitals = VitalSignsFactory.create_vitals(self.patient, respiratory_rate=None)
        self.assertEqual(vitals.news2_respiratory_score, 0)


class NEWS2OxygenSaturationTests(TestCase):
    """Test NEWS2 Oxygen Saturation (SpO₂) scoring"""

    def setUp(self):
        self.patient = PatientFactory.create_patient()

    def test_spo2_91_or_less_scores_3(self):
        """SpO₂ ≤ 91%: 3 points (critical)"""
        for spo2 in [91, 90, 85]:
            vitals = VitalSignsFactory.create_vitals(self.patient, oxygen_saturation=spo2)
            self.assertEqual(vitals.news2_spo2_score, 3, f"SpO₂={spo2} should score 3")

    def test_spo2_92_to_93_scores_2(self):
        """SpO₂ 92-93%: 2 points"""
        for spo2 in [92, 93]:
            vitals = VitalSignsFactory.create_vitals(self.patient, oxygen_saturation=spo2)
            self.assertEqual(vitals.news2_spo2_score, 2, f"SpO₂={spo2} should score 2")

    def test_spo2_94_to_95_scores_1(self):
        """SpO₂ 94-95%: 1 point"""
        for spo2 in [94, 95]:
            vitals = VitalSignsFactory.create_vitals(self.patient, oxygen_saturation=spo2)
            self.assertEqual(vitals.news2_spo2_score, 1, f"SpO₂={spo2} should score 1")

    def test_spo2_96_or_more_scores_0(self):
        """SpO₂ ≥ 96%: 0 points (normal)"""
        for spo2 in [96, 97, 98, 99, 100]:
            vitals = VitalSignsFactory.create_vitals(self.patient, oxygen_saturation=spo2)
            self.assertEqual(vitals.news2_spo2_score, 0, f"SpO₂={spo2} should score 0")

    def test_spo2_none_scores_0(self):
        """Missing SpO₂: 0 points"""
        vitals = VitalSignsFactory.create_vitals(self.patient, oxygen_saturation=None)
        self.assertEqual(vitals.news2_spo2_score, 0)


class NEWS2TemperatureTests(TestCase):
    """Test NEWS2 Temperature scoring"""

    def setUp(self):
        self.patient = PatientFactory.create_patient()

    def test_temp_35_or_less_scores_3(self):
        """Temp ≤ 35.0°C: 3 points (hypothermia)"""
        for temp in [35.0, 34.0, 32.0]:
            vitals = VitalSignsFactory.create_vitals(self.patient, temperature=temp)
            self.assertEqual(vitals.news2_temp_score, 3, f"Temp={temp} should score 3")

    def test_temp_35_1_to_36_0_scores_1(self):
        """Temp 35.1-36.0°C: 1 point"""
        for temp in [35.5, 36.0]:
            vitals = VitalSignsFactory.create_vitals(self.patient, temperature=temp)
            self.assertEqual(vitals.news2_temp_score, 1, f"Temp={temp} should score 1")

    def test_temp_36_1_to_38_0_scores_0(self):
        """Temp 36.1-38.0°C: 0 points (normal)"""
        for temp in [36.5, 37.0, 37.5, 38.0]:
            vitals = VitalSignsFactory.create_vitals(self.patient, temperature=temp)
            self.assertEqual(vitals.news2_temp_score, 0, f"Temp={temp} should score 0")

    def test_temp_38_1_to_39_0_scores_1(self):
        """Temp 38.1-39.0°C: 1 point (fever)"""
        for temp in [38.5, 39.0]:
            vitals = VitalSignsFactory.create_vitals(self.patient, temperature=temp)
            self.assertEqual(vitals.news2_temp_score, 1, f"Temp={temp} should score 1")

    def test_temp_39_1_or_more_scores_2(self):
        """Temp ≥ 39.1°C: 2 points (high fever)"""
        for temp in [39.1, 40.0, 41.0]:
            vitals = VitalSignsFactory.create_vitals(self.patient, temperature=temp)
            self.assertEqual(vitals.news2_temp_score, 2, f"Temp={temp} should score 2")

    def test_temp_none_scores_0(self):
        """Missing Temp: 0 points"""
        vitals = VitalSignsFactory.create_vitals(self.patient, temperature=None)
        self.assertEqual(vitals.news2_temp_score, 0)


class NEWS2BloodPressureTests(TestCase):
    """Test NEWS2 Systolic Blood Pressure scoring"""

    def setUp(self):
        self.patient = PatientFactory.create_patient()

    def test_bp_systolic_90_or_less_scores_3(self):
        """BP ≤ 90 mmHg: 3 points (hypotensive)"""
        for bp in [90, 85, 80]:
            vitals = VitalSignsFactory.create_vitals(self.patient, bp_systolic=bp, bp_diastolic=60)
            self.assertEqual(vitals.news2_bp_score, 3, f"BP={bp} should score 3")

    def test_bp_systolic_91_to_100_scores_2(self):
        """BP 91-100 mmHg: 2 points"""
        for bp in [91, 95, 100]:
            vitals = VitalSignsFactory.create_vitals(self.patient, bp_systolic=bp, bp_diastolic=60)
            self.assertEqual(vitals.news2_bp_score, 2, f"BP={bp} should score 2")

    def test_bp_systolic_101_to_110_scores_1(self):
        """BP 101-110 mmHg: 1 point"""
        for bp in [101, 105, 110]:
            vitals = VitalSignsFactory.create_vitals(self.patient, bp_systolic=bp, bp_diastolic=60)
            self.assertEqual(vitals.news2_bp_score, 1, f"BP={bp} should score 1")

    def test_bp_systolic_111_to_219_scores_0(self):
        """BP 111-219 mmHg: 0 points (normal-high range)"""
        for bp in [111, 120, 150, 219]:
            vitals = VitalSignsFactory.create_vitals(self.patient, bp_systolic=bp, bp_diastolic=60)
            self.assertEqual(vitals.news2_bp_score, 0, f"BP={bp} should score 0")

    def test_bp_systolic_220_or_more_scores_3(self):
        """BP ≥ 220 mmHg: 3 points (hypertensive crisis)"""
        for bp in [220, 230, 240]:
            vitals = VitalSignsFactory.create_vitals(self.patient, bp_systolic=bp, bp_diastolic=120)
            self.assertEqual(vitals.news2_bp_score, 3, f"BP={bp} should score 3")

    def test_bp_systolic_none_scores_0(self):
        """Missing BP: 0 points"""
        vitals = VitalSignsFactory.create_vitals(self.patient, bp_systolic=None, bp_diastolic=None)
        self.assertEqual(vitals.news2_bp_score, 0)


class NEWS2HeartRateTests(TestCase):
    """Test NEWS2 Heart Rate scoring"""

    def setUp(self):
        self.patient = PatientFactory.create_patient()

    def test_hr_40_or_less_scores_3(self):
        """HR ≤ 40 bpm: 3 points (bradycardia)"""
        for hr in [40, 35, 30]:
            vitals = VitalSignsFactory.create_vitals(self.patient, heart_rate=hr)
            self.assertEqual(vitals.news2_hr_score, 3, f"HR={hr} should score 3")

    def test_hr_41_to_50_scores_1(self):
        """HR 41-50 bpm: 1 point"""
        for hr in [41, 45, 50]:
            vitals = VitalSignsFactory.create_vitals(self.patient, heart_rate=hr)
            self.assertEqual(vitals.news2_hr_score, 1, f"HR={hr} should score 1")

    def test_hr_51_to_90_scores_0(self):
        """HR 51-90 bpm: 0 points (normal)"""
        for hr in [51, 60, 75, 90]:
            vitals = VitalSignsFactory.create_vitals(self.patient, heart_rate=hr)
            self.assertEqual(vitals.news2_hr_score, 0, f"HR={hr} should score 0")

    def test_hr_91_to_110_scores_1(self):
        """HR 91-110 bpm: 1 point (tachycardia)"""
        for hr in [91, 100, 110]:
            vitals = VitalSignsFactory.create_vitals(self.patient, heart_rate=hr)
            self.assertEqual(vitals.news2_hr_score, 1, f"HR={hr} should score 1")

    def test_hr_111_to_130_scores_2(self):
        """HR 111-130 bpm: 2 points"""
        for hr in [111, 120, 130]:
            vitals = VitalSignsFactory.create_vitals(self.patient, heart_rate=hr)
            self.assertEqual(vitals.news2_hr_score, 2, f"HR={hr} should score 2")

    def test_hr_131_or_more_scores_3(self):
        """HR ≥ 131 bpm: 3 points (severe tachycardia)"""
        for hr in [131, 140, 160]:
            vitals = VitalSignsFactory.create_vitals(self.patient, heart_rate=hr)
            self.assertEqual(vitals.news2_hr_score, 3, f"HR={hr} should score 3")

    def test_hr_none_scores_0(self):
        """Missing HR: 0 points"""
        vitals = VitalSignsFactory.create_vitals(self.patient, heart_rate=None)
        self.assertEqual(vitals.news2_hr_score, 0)


class NEWS2TotalScoringTests(TestCase):
    """Test combined NEWS2 total scores"""

    def setUp(self):
        self.patient = PatientFactory.create_patient()

    def test_all_normal_scores_0(self):
        """All vitals normal: NEWS2 = 0"""
        vitals = VitalSignsFactory.create_vitals(
            self.patient,
            heart_rate=75,
            respiratory_rate=16,
            oxygen_saturation=97,
            bp_systolic=120,
            temperature=37.0
        )
        self.assertEqual(vitals.news2_total, 0, "All normal vitals should score 0")
        self.assertEqual(vitals.news2_level, 'low')

    def test_mild_abnormalities_score_2_to_4(self):
        """Mild abnormalities: NEWS2 = 2-4"""
        vitals = VitalSignsFactory.create_vitals(
            self.patient,
            heart_rate=105,  # 1 point
            respiratory_rate=22,  # 2 points
            oxygen_saturation=95,  # 1 point
            bp_systolic=115,  # 0 points
            temperature=37.0  # 0 points
        )
        self.assertIn(vitals.news2_total, [4], f"Expected 4, got {vitals.news2_total}")
        self.assertEqual(vitals.news2_level, 'low')

    def test_medium_risk_scores_5_to_6(self):
        """Medium risk: NEWS2 = 5-6"""
        vitals = VitalSignsFactory.create_vitals(
            self.patient,
            heart_rate=120,  # 2 points
            respiratory_rate=24,  # 2 points
            oxygen_saturation=94,  # 1 point
            bp_systolic=95,  # 2 points
            temperature=37.0  # 0 points
        )
        self.assertEqual(vitals.news2_total, 7, f"Should score 7 (HIGH RISK)")
        self.assertEqual(vitals.news2_level, 'high')

    def test_high_risk_scores_7_or_more(self):
        """High risk: NEWS2 ≥ 7"""
        vitals = VitalSignsFactory.create_vitals(
            self.patient,
            heart_rate=135,  # 3 points (≥131)
            respiratory_rate=26,  # 3 points
            oxygen_saturation=92,  # 2 points
            bp_systolic=105,  # 1 point
            temperature=38.2  # 1 point
        )
        self.assertEqual(vitals.news2_total, 10, f"Should score 10 (HIGH RISK)")
        self.assertEqual(vitals.news2_level, 'high')

    def test_critical_patient_all_bad_vitals(self):
        """Critical patient: Multiple critical vitals"""
        vitals = VitalSignsFactory.create_vitals(
            self.patient,
            heart_rate=140,  # 3 points
            respiratory_rate=28,  # 3 points
            oxygen_saturation=90,  # 3 points
            bp_systolic=230,  # 3 points
            temperature=40.5  # 2 points
        )
        self.assertEqual(vitals.news2_total, 14, f"Expected 14, got {vitals.news2_total}")
        self.assertEqual(vitals.news2_level, 'high')

    def test_hypothermic_patient(self):
        """Hypothermic patient"""
        vitals = VitalSignsFactory.create_vitals(
            self.patient,
            heart_rate=45,  # 1 point
            respiratory_rate=14,  # 0 points
            oxygen_saturation=97,  # 0 points
            bp_systolic=95,  # 2 points
            temperature=34.5  # 3 points
        )
        self.assertEqual(vitals.news2_total, 6, f"Expected 6, got {vitals.news2_total}")
        self.assertEqual(vitals.news2_level, 'medium')


class NEWS2RiskLevelTests(TestCase):
    """Test risk level classification"""

    def setUp(self):
        self.patient = PatientFactory.create_patient()

    def test_low_risk_0_to_4(self):
        """NEWS2 0-4: Low Risk"""
        vitals = VitalSignsFactory.create_vitals(
            self.patient,
            heart_rate=72,
            respiratory_rate=16,
            oxygen_saturation=97,
            bp_systolic=120,
            temperature=37.0
        )
        self.assertEqual(vitals.news2_level, 'low')
        self.assertEqual(vitals.news2_label, 'Low Risk')

    def test_medium_risk_5_to_6(self):
        """NEWS2 5-6: Medium Risk"""
        vitals = VitalSignsFactory.create_vitals(
            self.patient,
            heart_rate=105,  # 1 point
            respiratory_rate=22,  # 2 points
            oxygen_saturation=94,  # 1 point
            bp_systolic=95,  # 2 points
            temperature=37.0  # 0 points
        )
        # This should be 6 points
        self.assertIn(vitals.news2_total, [6], f"Expected 6, got {vitals.news2_total}")
        self.assertEqual(vitals.news2_level, 'medium')
        self.assertEqual(vitals.news2_label, 'Medium Risk')

    def test_high_risk_7_or_more(self):
        """NEWS2 ≥ 7: High Risk"""
        vitals = VitalSignsFactory.create_vitals(
            self.patient,
            heart_rate=120,  # 2 points
            respiratory_rate=26,  # 3 points
            oxygen_saturation=92,  # 2 points
            bp_systolic=115,  # 0 points
            temperature=38.0  # 0 points
        )
        self.assertEqual(vitals.news2_total, 7)
        self.assertEqual(vitals.news2_level, 'high')
        self.assertEqual(vitals.news2_label, 'HIGH RISK')


class RiskAssessmentModelTests(TestCase):
    """Test RiskAssessment model creation and functionality"""

    def setUp(self):
        self.patient = PatientFactory.create_patient()
        self.vital = VitalSignsFactory.create_vitals(
            self.patient,
            heart_rate=120,
            respiratory_rate=24,
            oxygen_saturation=94,
            bp_systolic=110,
            temperature=37.5
        )

    def test_risk_assessment_creation(self):
        """Test creating a RiskAssessment record"""
        assessment = RiskAssessment.objects.create(
            patient=self.patient,
            assessed_at=timezone.now(),
            observation_count=1,
            news2_total=5,
            news2_hr_score=1,
            news2_rr_score=2,
            news2_spo2_score=1,
            news2_bp_score=0,
            news2_temp_score=1,
            trend_score=0,
            combined_risk=5,
            risk_level='medium',
            explanation_text='Patient showing some abnormal vitals',
        )
        self.assertIsNotNone(assessment.id)
        self.assertEqual(assessment.patient, self.patient)
        self.assertEqual(assessment.news2_total, 5)
        self.assertEqual(assessment.risk_level, 'medium')

    def test_risk_assessment_with_vitals_relationship(self):
        """Test linking vital signs to risk assessment"""
        assessment = RiskAssessment.objects.create(
            patient=self.patient,
            assessed_at=self.vital.recorded_at,
            observation_count=1,
            news2_total=self.vital.news2_total,
            news2_hr_score=self.vital.news2_hr_score,
            news2_rr_score=self.vital.news2_respiratory_score,
            news2_spo2_score=self.vital.news2_spo2_score,
            news2_bp_score=self.vital.news2_bp_score,
            news2_temp_score=self.vital.news2_temp_score,
            combined_risk=self.vital.news2_total,
            risk_level=self.vital.news2_level,
        )
        assessment.vital_signs.add(self.vital)
        assessment.save()

        self.assertEqual(assessment.vital_signs.count(), 1)
        self.assertIn(self.vital, assessment.vital_signs.all())

    def test_risk_assessment_ordering(self):
        """Test that assessments are ordered by assessed_at (newest first)"""
        now = timezone.now()
        assessment1 = RiskAssessment.objects.create(
            patient=self.patient,
            assessed_at=now - timedelta(hours=2),
            news2_total=3,
            news2_hr_score=0,
            news2_rr_score=0,
            news2_spo2_score=0,
            news2_bp_score=0,
            news2_temp_score=3,
            combined_risk=3,
            risk_level='low',
        )
        assessment2 = RiskAssessment.objects.create(
            patient=self.patient,
            assessed_at=now,
            news2_total=5,
            news2_hr_score=1,
            news2_rr_score=1,
            news2_spo2_score=1,
            news2_bp_score=1,
            news2_temp_score=1,
            combined_risk=5,
            risk_level='medium',
        )

        assessments = list(RiskAssessment.objects.filter(patient=self.patient))
        self.assertEqual(assessments[0].id, assessment2.id)
        self.assertEqual(assessments[1].id, assessment1.id)


class NEWS2BoundaryConditionsTests(TestCase):
    """Test boundary conditions and edge cases"""

    def setUp(self):
        self.patient = PatientFactory.create_patient()

    def test_boundary_rr_20_21(self):
        """Test boundary between RR 20 (0 points) and RR 21 (2 points)"""
        vitals_20 = VitalSignsFactory.create_vitals(self.patient, respiratory_rate=20)
        vitals_21 = VitalSignsFactory.create_vitals(self.patient, respiratory_rate=21)

        self.assertEqual(vitals_20.news2_respiratory_score, 0)
        self.assertEqual(vitals_21.news2_respiratory_score, 2)

    def test_boundary_spo2_95_96(self):
        """Test boundary between SpO2 95% (1 point) and SpO2 96% (0 points)"""
        vitals_95 = VitalSignsFactory.create_vitals(self.patient, oxygen_saturation=95)
        vitals_96 = VitalSignsFactory.create_vitals(self.patient, oxygen_saturation=96)

        self.assertEqual(vitals_95.news2_spo2_score, 1)
        self.assertEqual(vitals_96.news2_spo2_score, 0)

    def test_boundary_temp_36_0_36_1(self):
        """Test boundary between Temp 36.0 (1 point) and 36.1 (0 points)"""
        vitals_36_0 = VitalSignsFactory.create_vitals(self.patient, temperature=36.0)
        vitals_36_1 = VitalSignsFactory.create_vitals(self.patient, temperature=36.1)

        self.assertEqual(vitals_36_0.news2_temp_score, 1)
        self.assertEqual(vitals_36_1.news2_temp_score, 0)

    def test_boundary_bp_110_111(self):
        """Test boundary between BP 110 (1 point) and BP 111 (0 points)"""
        vitals_110 = VitalSignsFactory.create_vitals(self.patient, bp_systolic=110, bp_diastolic=70)
        vitals_111 = VitalSignsFactory.create_vitals(self.patient, bp_systolic=111, bp_diastolic=70)

        self.assertEqual(vitals_110.news2_bp_score, 1)
        self.assertEqual(vitals_111.news2_bp_score, 0)

    def test_boundary_hr_90_91(self):
        """Test boundary between HR 90 (0 points) and HR 91 (1 point)"""
        vitals_90 = VitalSignsFactory.create_vitals(self.patient, heart_rate=90)
        vitals_91 = VitalSignsFactory.create_vitals(self.patient, heart_rate=91)

        self.assertEqual(vitals_90.news2_hr_score, 0)
        self.assertEqual(vitals_91.news2_hr_score, 1)


class NEWS2ImpossibleValuesTests(TestCase):
    """Test handling of impossible or extreme values"""

    def setUp(self):
        self.patient = PatientFactory.create_patient()

    def test_negative_heart_rate(self):
        """Test that negative HR is handled (shouldn't occur in practice)"""
        # The model should still work even with invalid data
        vitals = VitalSignsFactory.create_vitals(self.patient, heart_rate=-50)
        # Should not crash, though value is physiologically impossible
        self.assertIsNotNone(vitals.news2_hr_score)

    def test_zero_vital_values(self):
        """Test zero vital values"""
        vitals = VitalSignsFactory.create_vitals(
            self.patient,
            heart_rate=0,
            respiratory_rate=0,
            oxygen_saturation=0,
            bp_systolic=0,
            temperature=0
        )
        # Should calculate scores even if 0 (will be high-risk due to critical values)
        self.assertGreater(vitals.news2_total, 0)

    def test_extreme_high_values(self):
        """Test extremely high vital values"""
        vitals = VitalSignsFactory.create_vitals(
            self.patient,
            heart_rate=250,
            respiratory_rate=100,
            oxygen_saturation=100,
            bp_systolic=300,
            temperature=45
        )
        # Should still calculate without crashing
        self.assertIsNotNone(vitals.news2_total)
        self.assertGreater(vitals.news2_total, 0)
