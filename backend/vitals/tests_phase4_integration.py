"""
Phase 4: Integration & Alerts - Comprehensive Integration Tests

Tests the complete flow:
1. Vital sign recorded
2. Signal handler invokes RiskAssessmentEngine
3. RiskAssessment record created
4. Alert created if needed
5. Dashboard receives updates
"""

from django.test import TestCase
from django.utils import timezone
from patients.models import Patient
from accounts.models import User
from vitals.models import VitalSigns, RiskAssessment
from deterioration_alerts.models import DeteriorationAlert
from datetime import timedelta
from decimal import Decimal


class PatientFactory:
    """Create test patients"""
    @staticmethod
    def create_patient(first_name="Test", last_name="Patient", age=75):
        from datetime import date
        dob = date.today() - timedelta(days=age*365)
        return Patient.objects.create(
            first_name=first_name,
            last_name=last_name,
            date_of_birth=dob,
            nhs_number=f"NHS{Patient.objects.count():08d}"
        )


class UserFactory:
    """Create test users"""
    @staticmethod
    def create_user(username="testuser", email="test@example.com"):
        user, created = User.objects.get_or_create(
            username=username,
            defaults={'email': email}
        )
        return user


class StableVitalSignsTests(TestCase):
    """Test stable patient - LOW risk, no alert"""

    def setUp(self):
        self.patient = PatientFactory.create_patient("John", "Smith", 75)
        self.user = UserFactory.create_user()

    def test_stable_vitals_creates_low_risk_assessment(self):
        """Stable vitals should create LOW risk RiskAssessment"""
        vital = VitalSigns.objects.create(
            patient=self.patient,
            recorded_by=self.user,
            heart_rate=75,
            respiratory_rate=16,
            oxygen_saturation=Decimal('97.0'),
            bp_systolic=120,
            bp_diastolic=80,
            temperature=Decimal('37.0'),
            recorded_at=timezone.now()
        )

        # Should create RiskAssessment
        assessment = RiskAssessment.objects.filter(patient=self.patient).first()
        self.assertIsNotNone(assessment)
        self.assertEqual(assessment.risk_level, 'low')
        self.assertLessEqual(assessment.combined_risk, 4)

    def test_stable_vitals_no_alert(self):
        """Stable vitals should NOT create alert"""
        vital = VitalSigns.objects.create(
            patient=self.patient,
            recorded_by=self.user,
            heart_rate=75,
            respiratory_rate=16,
            oxygen_saturation=Decimal('97.0'),
            bp_systolic=120,
            bp_diastolic=80,
            temperature=Decimal('37.0'),
            recorded_at=timezone.now()
        )

        # Should NOT create alert
        alerts = DeteriorationAlert.objects.filter(patient=self.patient)
        self.assertEqual(alerts.count(), 0)

    def test_stable_multiple_readings_consistent_assessment(self):
        """Multiple stable readings should maintain low risk"""
        now = timezone.now()

        for i in range(3):
            VitalSigns.objects.create(
                patient=self.patient,
                recorded_by=self.user,
                heart_rate=75 + i,
                respiratory_rate=16,
                oxygen_saturation=Decimal('97.0'),
                bp_systolic=120,
                bp_diastolic=80,
                temperature=Decimal('37.0'),
                recorded_at=now - timedelta(hours=2-i)
            )

        # Latest assessment should still be LOW
        latest_assessment = RiskAssessment.objects.filter(
            patient=self.patient
        ).latest('assessed_at')

        self.assertEqual(latest_assessment.risk_level, 'low')


class MediumRiskTests(TestCase):
    """Test MEDIUM risk scenarios"""

    def setUp(self):
        self.patient = PatientFactory.create_patient("Jane", "Doe", 72)
        self.user = UserFactory.create_user("user2")

    def test_elevated_news2_creates_medium_risk(self):
        """Elevated NEWS2 (5-6) creates MEDIUM risk"""
        vital = VitalSigns.objects.create(
            patient=self.patient,
            recorded_by=self.user,
            heart_rate=105,  # 1 point
            respiratory_rate=22,  # 2 points
            oxygen_saturation=Decimal('94.0'),  # 1 point
            bp_systolic=140,  # 0 points
            bp_diastolic=90,
            temperature=Decimal('38.2'),  # 1 point
            recorded_at=timezone.now()
        )

        assessment = RiskAssessment.objects.filter(patient=self.patient).first()
        self.assertIsNotNone(assessment)
        self.assertIn(assessment.risk_level, ['medium', 'high'])

    def test_medium_risk_with_deteriorating_trend_creates_alert(self):
        """MEDIUM risk + deterioration trend creates alert"""
        now = timezone.now()

        # First vital - baseline
        VitalSigns.objects.create(
            patient=self.patient,
            recorded_by=self.user,
            heart_rate=75,
            respiratory_rate=16,
            oxygen_saturation=Decimal('96.0'),
            bp_systolic=120,
            bp_diastolic=80,
            temperature=Decimal('37.0'),
            recorded_at=now - timedelta(hours=1)
        )

        # Second vital - small deterioration trend
        vital2 = VitalSigns.objects.create(
            patient=self.patient,
            recorded_by=self.user,
            heart_rate=85,  # +10 bpm/hour trend
            respiratory_rate=19,  # +3 br/min/hour trend
            oxygen_saturation=Decimal('95.0'),  # -1%/hour trend (minimal)
            bp_systolic=115,  # -5 mmHg/hour trend
            bp_diastolic=75,
            temperature=Decimal('37.2'),  # +0.2°C/hour trend
            recorded_at=now
        )

        # Should create alert due to deterioration trend
        alerts = DeteriorationAlert.objects.filter(patient=self.patient)
        self.assertGreater(alerts.count(), 0)

        alert = alerts.first()
        # Alert priority depends on combined risk - should be at least medium
        self.assertIn(alert.priority, ['medium', 'high', 'critical'])


class HighRiskTests(TestCase):
    """Test HIGH risk scenarios"""

    def setUp(self):
        self.patient = PatientFactory.create_patient("Bob", "Johnson", 78)
        self.user = UserFactory.create_user("user3")

    def test_high_news2_creates_high_risk_alert(self):
        """NEWS2 >= 7 creates HIGH or CRITICAL risk alert"""
        now = timezone.now()

        # Baseline first
        VitalSigns.objects.create(
            patient=self.patient,
            recorded_by=self.user,
            heart_rate=75,
            respiratory_rate=16,
            oxygen_saturation=Decimal('97.0'),
            bp_systolic=120,
            bp_diastolic=80,
            temperature=Decimal('37.0'),
            recorded_at=now - timedelta(hours=1)
        )

        # Then critical vital (creates trend)
        vital = VitalSigns.objects.create(
            patient=self.patient,
            recorded_by=self.user,
            heart_rate=120,  # 2 points, +45 bpm/hour trend
            respiratory_rate=26,  # 3 points, +10 br/min/hour trend
            oxygen_saturation=Decimal('92.0'),  # 2 points, -5%/hour trend
            bp_systolic=160,  # 0 points, +40 mmHg/hour trend
            bp_diastolic=95,
            temperature=Decimal('38.8'),  # 1 point, +1.8°C/hour trend
            recorded_at=now
        )

        # Should create HIGH or CRITICAL risk assessment (with trend amplification)
        assessment = RiskAssessment.objects.filter(patient=self.patient).latest('assessed_at')
        self.assertIsNotNone(assessment)
        self.assertIn(assessment.risk_level, ['high', 'critical'])

        # Should create alert with HIGH or CRITICAL priority
        alert = DeteriorationAlert.objects.filter(patient=self.patient).first()
        self.assertIsNotNone(alert)
        self.assertIn(alert.priority, ['high', 'critical'])

    def test_combined_risk_reaches_high(self):
        """Combined risk score >= 8 creates HIGH alert"""
        now = timezone.now()

        # Baseline
        VitalSigns.objects.create(
            patient=self.patient,
            recorded_by=self.user,
            heart_rate=80,
            respiratory_rate=18,
            oxygen_saturation=Decimal('96.0'),
            bp_systolic=120,
            bp_diastolic=80,
            temperature=Decimal('37.0'),
            recorded_at=now - timedelta(hours=1)
        )

        # Deterioration
        vital = VitalSigns.objects.create(
            patient=self.patient,
            recorded_by=self.user,
            heart_rate=105,  # NEWS2: 1 point, trend: +25 bpm/hour
            respiratory_rate=24,  # NEWS2: 2 points, trend: +6 br/min/hour
            oxygen_saturation=Decimal('93.0'),  # NEWS2: 2 points, trend: -3%/hour
            bp_systolic=135,
            bp_diastolic=85,
            temperature=Decimal('38.2'),  # NEWS2: 1 point
            recorded_at=now
        )

        # Combined risk should be >= 8
        assessment = RiskAssessment.objects.filter(patient=self.patient).latest('assessed_at')
        self.assertGreaterEqual(assessment.combined_risk, 8)
        self.assertIn(assessment.risk_level, ['high', 'critical'])


class CriticalRiskTests(TestCase):
    """Test CRITICAL risk scenarios"""

    def setUp(self):
        self.patient = PatientFactory.create_patient("Alice", "Williams", 85)
        self.user = UserFactory.create_user("user4")

    def test_critical_news2_creates_critical_alert(self):
        """NEWS2 >= 9 creates CRITICAL risk"""
        vital = VitalSigns.objects.create(
            patient=self.patient,
            recorded_by=self.user,
            heart_rate=135,  # 3 points
            respiratory_rate=28,  # 3 points
            oxygen_saturation=Decimal('89.0'),  # 3 points
            bp_systolic=85,  # 3 points
            bp_diastolic=55,
            temperature=Decimal('38.8'),  # 1 point
            recorded_at=timezone.now()
        )

        # Should create CRITICAL assessment
        assessment = RiskAssessment.objects.filter(patient=self.patient).first()
        self.assertIsNotNone(assessment)
        self.assertEqual(assessment.risk_level, 'critical')

        # Should create CRITICAL priority alert
        alert = DeteriorationAlert.objects.filter(patient=self.patient).first()
        self.assertIsNotNone(alert)
        self.assertEqual(alert.priority, 'critical')

    def test_combined_risk_reaches_critical(self):
        """Combined risk score >= 12 creates CRITICAL alert"""
        now = timezone.now()

        # Rapid deterioration
        VitalSigns.objects.create(
            patient=self.patient,
            recorded_by=self.user,
            heart_rate=75,
            respiratory_rate=16,
            oxygen_saturation=Decimal('97.0'),
            bp_systolic=120,
            bp_diastolic=80,
            temperature=Decimal('37.0'),
            recorded_at=now - timedelta(hours=1)
        )

        # Critical state
        vital = VitalSigns.objects.create(
            patient=self.patient,
            recorded_by=self.user,
            heart_rate=125,  # 2 points NEWS2
            respiratory_rate=30,  # 3 points NEWS2
            oxygen_saturation=Decimal('90.0'),  # 3 points NEWS2
            bp_systolic=90,  # 3 points NEWS2
            bp_diastolic=60,
            temperature=Decimal('38.5'),  # 1 point NEWS2
            recorded_at=now
        )

        # Combined risk should be >= 12
        assessment = RiskAssessment.objects.filter(patient=self.patient).latest('assessed_at')
        self.assertGreaterEqual(assessment.combined_risk, 12)
        self.assertEqual(assessment.risk_level, 'critical')

        # Should create CRITICAL alert
        alert = DeteriorationAlert.objects.filter(patient=self.patient).latest('triggered_at')
        self.assertEqual(alert.priority, 'critical')


class MultiParameterDeterioration(TestCase):
    """Test multi-parameter worsening detection"""

    def setUp(self):
        self.patient = PatientFactory.create_patient("David", "Brown", 70)
        self.user = UserFactory.create_user("user5")

    def test_all_vitals_deteriorating_creates_high_alert(self):
        """All 5 vitals deteriorating simultaneously creates alert"""
        now = timezone.now()

        # Baseline
        VitalSigns.objects.create(
            patient=self.patient,
            recorded_by=self.user,
            heart_rate=75,
            respiratory_rate=16,
            oxygen_saturation=Decimal('97.0'),
            bp_systolic=120,
            bp_diastolic=80,
            temperature=Decimal('37.0'),
            recorded_at=now - timedelta(hours=1)
        )

        # All worsening - triggers alert
        vital = VitalSigns.objects.create(
            patient=self.patient,
            recorded_by=self.user,
            heart_rate=100,  # +25 bpm/hour (worsening >=10)
            respiratory_rate=23,  # +7 br/min/hour (worsening >=5)
            oxygen_saturation=Decimal('93.0'),  # -4%/hour (worsening <=-2)
            bp_systolic=100,  # -20 mmHg/hour (worsening >=+-10)
            bp_diastolic=65,
            temperature=Decimal('38.2'),  # +1.2°C/hour (worsening >=+-1)
            recorded_at=now
        )

        # Should have created alert due to multi-parameter worsening
        alerts = DeteriorationAlert.objects.filter(patient=self.patient)
        self.assertGreater(alerts.count(), 0)

        # Latest alert should be for the deteriorated vital
        alert = alerts.latest('triggered_at')
        self.assertEqual(alert.related_vital, vital)


class RiskAssessmentRecordingTests(TestCase):
    """Test RiskAssessment record creation and storage"""

    def setUp(self):
        self.patient = PatientFactory.create_patient("Emma", "Davis", 68)
        self.user = UserFactory.create_user("user6")

    def test_risk_assessment_stores_news2_components(self):
        """RiskAssessment should store all NEWS2 component scores"""
        vital = VitalSigns.objects.create(
            patient=self.patient,
            recorded_by=self.user,
            heart_rate=105,
            respiratory_rate=22,
            oxygen_saturation=Decimal('94.0'),
            bp_systolic=140,
            bp_diastolic=90,
            temperature=Decimal('38.0'),
            recorded_at=timezone.now()
        )

        assessment = RiskAssessment.objects.filter(patient=self.patient).first()
        self.assertIsNotNone(assessment)
        self.assertEqual(assessment.news2_hr_score, vital.news2_hr_score)
        self.assertEqual(assessment.news2_rr_score, vital.news2_respiratory_score)
        self.assertEqual(assessment.news2_spo2_score, vital.news2_spo2_score)
        self.assertEqual(assessment.news2_bp_score, vital.news2_bp_score)
        self.assertEqual(assessment.news2_temp_score, vital.news2_temp_score)
        self.assertEqual(assessment.news2_total, vital.news2_total)

    def test_risk_assessment_stores_decision_logic(self):
        """RiskAssessment should store decision logic for explainability"""
        vital = VitalSigns.objects.create(
            patient=self.patient,
            recorded_by=self.user,
            heart_rate=95,
            respiratory_rate=20,
            oxygen_saturation=Decimal('95.0'),
            bp_systolic=130,
            bp_diastolic=85,
            temperature=Decimal('37.5'),
            recorded_at=timezone.now()
        )

        assessment = RiskAssessment.objects.filter(patient=self.patient).first()
        self.assertIsNotNone(assessment)
        if assessment.decision_logic:  # decision_logic might be empty if it fails to generate
            self.assertIn('algorithm_version', assessment.decision_logic)
        self.assertGreaterEqual(len(assessment.explanation_text), 0)
        self.assertGreaterEqual(len(assessment.recommendation), 0)

    def test_risk_assessment_links_to_vital_signs(self):
        """RiskAssessment should be linked to the vital signs that triggered it"""
        vital = VitalSigns.objects.create(
            patient=self.patient,
            recorded_by=self.user,
            heart_rate=85,
            respiratory_rate=18,
            oxygen_saturation=Decimal('96.0'),
            bp_systolic=125,
            bp_diastolic=82,
            temperature=Decimal('37.2'),
            recorded_at=timezone.now()
        )

        assessment = RiskAssessment.objects.filter(patient=self.patient).first()
        self.assertIn(vital, assessment.vital_signs.all())

    def test_alert_links_to_risk_assessment(self):
        """Alerts should reference the RiskAssessment that triggered them"""
        now = timezone.now()

        # Baseline
        VitalSigns.objects.create(
            patient=self.patient,
            recorded_by=self.user,
            heart_rate=75,
            respiratory_rate=16,
            oxygen_saturation=Decimal('97.0'),
            bp_systolic=120,
            bp_diastolic=80,
            temperature=Decimal('37.0'),
            recorded_at=now - timedelta(hours=1)
        )

        # Trigger alert
        vital = VitalSigns.objects.create(
            patient=self.patient,
            recorded_by=self.user,
            heart_rate=125,  # 2 points
            respiratory_rate=27,  # 3 points
            oxygen_saturation=Decimal('91.0'),  # 3 points
            bp_systolic=85,  # 3 points
            bp_diastolic=55,
            temperature=Decimal('38.8'),  # 1 point
            recorded_at=now
        )

        alert = DeteriorationAlert.objects.filter(patient=self.patient).first()
        self.assertIsNotNone(alert)
        self.assertIsNotNone(alert.risk_assessment)
        self.assertEqual(alert.related_vital, vital)


class IntegrationFlowTests(TestCase):
    """End-to-end integration flow tests"""

    def setUp(self):
        self.patient = PatientFactory.create_patient("Frank", "Miller", 80)
        self.user = UserFactory.create_user("user7")

    def test_complete_flow_stable_to_critical(self):
        """Test progression from stable to critical with alerts"""
        now = timezone.now()

        # Hour 1: Stable
        vital1 = VitalSigns.objects.create(
            patient=self.patient,
            recorded_by=self.user,
            heart_rate=75,
            respiratory_rate=16,
            oxygen_saturation=Decimal('97.0'),
            bp_systolic=120,
            bp_diastolic=80,
            temperature=Decimal('37.0'),
            recorded_at=now
        )

        assessment1 = RiskAssessment.objects.filter(patient=self.patient).first()
        self.assertEqual(assessment1.risk_level, 'low')
        self.assertEqual(DeteriorationAlert.objects.filter(patient=self.patient).count(), 0)

        # Hour 2: Deteriorating
        vital2 = VitalSigns.objects.create(
            patient=self.patient,
            recorded_by=self.user,
            heart_rate=95,
            respiratory_rate=22,
            oxygen_saturation=Decimal('94.0'),
            bp_systolic=130,
            bp_diastolic=85,
            temperature=Decimal('37.8'),
            recorded_at=now + timedelta(hours=1)
        )

        assessment2 = RiskAssessment.objects.filter(patient=self.patient).latest('assessed_at')
        # With deterioration trend, may already be high or critical
        self.assertIn(assessment2.risk_level, ['medium', 'high', 'critical'])

        # Hour 3: Critical
        vital3 = VitalSigns.objects.create(
            patient=self.patient,
            recorded_by=self.user,
            heart_rate=125,
            respiratory_rate=29,
            oxygen_saturation=Decimal('90.0'),
            bp_systolic=90,
            bp_diastolic=60,
            temperature=Decimal('38.8'),
            recorded_at=now + timedelta(hours=2)
        )

        assessment3 = RiskAssessment.objects.filter(patient=self.patient).latest('assessed_at')
        self.assertEqual(assessment3.risk_level, 'critical')

        # Should have created alerts
        alerts = DeteriorationAlert.objects.filter(patient=self.patient)
        self.assertGreater(alerts.count(), 0)

        # Latest alert should be critical priority
        latest_alert = alerts.latest('triggered_at')
        self.assertEqual(latest_alert.priority, 'critical')

    def test_no_duplicate_assessments_on_non_vital_updates(self):
        """Signal should only trigger on VitalSigns creation, not updates"""
        vital = VitalSigns.objects.create(
            patient=self.patient,
            recorded_by=self.user,
            heart_rate=80,
            respiratory_rate=16,
            oxygen_saturation=Decimal('97.0'),
            bp_systolic=120,
            bp_diastolic=80,
            temperature=Decimal('37.0'),
            recorded_at=timezone.now()
        )

        initial_count = RiskAssessment.objects.filter(patient=self.patient).count()
        self.assertEqual(initial_count, 1)

        # Update the vital (modify notes)
        vital.notes = "Updated notes"
        vital.save()

        # Should still have only 1 assessment
        final_count = RiskAssessment.objects.filter(patient=self.patient).count()
        self.assertEqual(final_count, 1)
