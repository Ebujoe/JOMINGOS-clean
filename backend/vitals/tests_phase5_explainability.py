"""
Phase 5: Dashboard Display & Explainability - Test Suite

Tests for:
1. Explainability Engine
2. API Endpoints
3. Clinical explanation generation
4. Risk timeline rendering
"""

from django.test import TestCase, Client
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from datetime import timedelta, date
from decimal import Decimal

from patients.models import Patient
from accounts.models import User
from vitals.models import VitalSigns, RiskAssessment
from vitals.utils.explainability import ExplainabilityEngine


class PatientFactory:
    """Create test patients"""
    @staticmethod
    def create_patient(first_name="Test", last_name="Patient", age=75):
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


class ExplainabilityEngineTests(TestCase):
    """Test explainability engine"""

    def setUp(self):
        self.engine = ExplainabilityEngine()
        self.patient = PatientFactory.create_patient("Alice", "Smith", 75)
        self.user = UserFactory.create_user()

    def test_low_risk_explanation(self):
        """Low risk should generate routine explanation"""
        vital = VitalSigns.objects.create(
            patient=self.patient,
            recorded_by=self.user,
            heart_rate=75,
            respiratory_rate=16,
            oxygen_saturation=Decimal('97.0'),
            bp_systolic=120,
            bp_diastolic=80,
            temperature=Decimal('37.0'),
        )

        assessment = RiskAssessment.objects.create(
            patient=self.patient,
            assessed_at=timezone.now(),
            news2_total=0,
            news2_hr_score=0,
            news2_rr_score=0,
            news2_spo2_score=0,
            news2_bp_score=0,
            news2_temp_score=0,
            trend_score=0,
            trend_level='low',
            multi_param_score=0,
            multi_param_pattern='stable',
            combined_risk=0,
            risk_level='low',
            explanation_text='Vitals stable',
            recommendation='Routine monitoring',
        )
        assessment.vital_signs.add(vital)

        explanation = self.engine.explain_assessment(assessment)

        self.assertIn('routine', explanation['executive_summary'].lower())
        self.assertEqual(explanation['recommendation'],
                        'Continue routine monitoring. No escalation needed. Review again at next scheduled vital check.')

    def test_critical_risk_explanation(self):
        """Critical risk should generate urgent explanation"""
        vital = VitalSigns.objects.create(
            patient=self.patient,
            recorded_by=self.user,
            heart_rate=135,
            respiratory_rate=28,
            oxygen_saturation=Decimal('89.0'),
            bp_systolic=85,
            bp_diastolic=55,
            temperature=Decimal('38.8'),
        )

        assessment = RiskAssessment.objects.create(
            patient=self.patient,
            assessed_at=timezone.now(),
            news2_total=13,
            news2_hr_score=3,
            news2_rr_score=3,
            news2_spo2_score=3,
            news2_bp_score=3,
            news2_temp_score=1,
            trend_score=10,
            trend_level='high',
            multi_param_score=3.0,
            multi_param_pattern='all_worsening',
            combined_risk=27.6,
            risk_level='critical',
            explanation_text='Critical deterioration',
            recommendation='URGENT: Immediate review',
            multi_param_details={
                'worsening_count': 5,
                'pattern': 'all_worsening',
                'contributing_vitals': ['heart_rate', 'respiratory_rate', 'oxygen_saturation', 'bp_systolic', 'temperature'],
            }
        )
        assessment.vital_signs.add(vital)

        explanation = self.engine.explain_assessment(assessment)

        self.assertIn('urgent', explanation['executive_summary'].lower())
        self.assertIn('critical', explanation['executive_summary'].lower())
        self.assertEqual(len(explanation['next_actions']), 6)  # 6 critical actions

    def test_contributing_factors_identification(self):
        """Identify and rank contributing factors"""
        vital = VitalSigns.objects.create(
            patient=self.patient,
            recorded_by=self.user,
            heart_rate=105,
            respiratory_rate=26,
            oxygen_saturation=Decimal('92.0'),
            bp_systolic=140,
            bp_diastolic=90,
            temperature=Decimal('38.2'),
        )

        assessment = RiskAssessment.objects.create(
            patient=self.patient,
            assessed_at=timezone.now(),
            news2_total=7,
            news2_hr_score=1,
            news2_rr_score=3,
            news2_spo2_score=2,
            news2_bp_score=0,
            news2_temp_score=1,
            trend_score=3,
            trend_level='medium',
            multi_param_score=0,
            multi_param_pattern='stable',
            combined_risk=6.6,
            risk_level='medium',
            explanation_text='Elevated NEWS2',
            recommendation='Increased monitoring',
            multi_param_details={'worsening_count': 0, 'pattern': 'stable', 'contributing_vitals': []}
        )
        assessment.vital_signs.add(vital)

        factors = self.engine._identify_contributing_factors(assessment)

        # Should have multiple factors (RR, SpO2, Temp, Trend)
        self.assertGreater(len(factors), 0)
        # SpO2 should have high priority (critical)
        spo2_factor = next((f for f in factors if 'oxygen' in f['factor'].lower()), None)
        self.assertIsNotNone(spo2_factor)

    def test_vital_contribution_explanation(self):
        """Explain how specific vital contributed to risk"""
        vital = VitalSigns.objects.create(
            patient=self.patient,
            recorded_by=self.user,
            heart_rate=105,
            respiratory_rate=26,
            oxygen_saturation=Decimal('92.0'),
            bp_systolic=140,
            bp_diastolic=90,
            temperature=Decimal('38.2'),
        )

        assessment = RiskAssessment.objects.create(
            patient=self.patient,
            assessed_at=timezone.now(),
            news2_total=7,
            news2_hr_score=1,
            news2_rr_score=3,
            news2_spo2_score=2,
            news2_bp_score=0,
            news2_temp_score=1,
            trend_score=0,
            trend_level='low',
            multi_param_score=0,
            multi_param_pattern='stable',
            combined_risk=7,
            risk_level='high',
            explanation_text='Elevated NEWS2',
            recommendation='Close monitoring',
            multi_param_details={'worsening_count': 0, 'pattern': 'stable', 'contributing_vitals': []}
        )
        assessment.vital_signs.add(vital)

        contributions = self.engine.explain_vital_contribution(vital, assessment)

        self.assertIn('heart_rate', contributions)
        self.assertIn('respiratory_rate', contributions)
        self.assertIn('oxygen_saturation', contributions)

    def test_narrative_generation(self):
        """Generate assessment narrative"""
        vital = VitalSigns.objects.create(
            patient=self.patient,
            recorded_by=self.user,
            heart_rate=95,
            respiratory_rate=20,
            oxygen_saturation=Decimal('95.0'),
            bp_systolic=130,
            bp_diastolic=85,
            temperature=Decimal('37.5'),
        )

        assessment = RiskAssessment.objects.create(
            patient=self.patient,
            assessed_at=timezone.now(),
            news2_total=2,
            news2_hr_score=0,
            news2_rr_score=0,
            news2_spo2_score=1,
            news2_bp_score=0,
            news2_temp_score=0,
            trend_score=1,
            trend_level='low',
            multi_param_score=0,
            multi_param_pattern='stable',
            combined_risk=3.2,
            risk_level='low',
            explanation_text='Stable vitals',
            recommendation='Routine monitoring',
            decision_logic={'combined_formula': 'NEWS2(2) + Trend*1.2(1.2) + MultiParam(0) = 3.2'},
            multi_param_details={'worsening_count': 0, 'pattern': 'stable', 'contributing_vitals': []}
        )
        assessment.vital_signs.add(vital)

        narrative = self.engine.generate_assessment_narrative(assessment)

        self.assertIn('Risk Level', narrative)
        self.assertIn('Combined Risk Score', narrative)
        self.assertIn('Component Scores', narrative)
        self.assertIn('Clinical Assessment', narrative)
        self.assertGreater(len(narrative), 100)


class RiskAssessmentAPITests(APITestCase):
    """Test API endpoints for risk assessments"""

    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory.create_user("apiuser", "api@test.com")
        self.user.set_password('testpass')
        self.user.save()
        self.client.force_authenticate(user=self.user)

        self.patient = PatientFactory.create_patient("Bob", "Johnson", 70)

    def test_risk_assessment_list(self):
        """List risk assessments"""
        vital = VitalSigns.objects.create(
            patient=self.patient,
            recorded_by=self.user,
            heart_rate=80,
            respiratory_rate=16,
            oxygen_saturation=Decimal('97.0'),
            bp_systolic=120,
            bp_diastolic=80,
            temperature=Decimal('37.0'),
        )

        assessment = RiskAssessment.objects.create(
            patient=self.patient,
            assessed_at=timezone.now(),
            news2_total=0,
            news2_hr_score=0,
            news2_rr_score=0,
            news2_spo2_score=0,
            news2_bp_score=0,
            news2_temp_score=0,
            trend_score=0,
            trend_level='low',
            multi_param_score=0,
            multi_param_pattern='stable',
            combined_risk=0,
            risk_level='low',
            explanation_text='Stable',
            recommendation='Routine',
            decision_logic={},
            multi_param_details={'worsening_count': 0, 'pattern': 'stable', 'contributing_vitals': []}
        )
        assessment.vital_signs.add(vital)

        response = self.client.get('/vitals/api/v1/risk-assessments/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check if paginated or direct list
        if isinstance(response.data, dict) and 'results' in response.data:
            self.assertGreaterEqual(len(response.data['results']), 1)
        else:
            self.assertGreaterEqual(len(response.data), 1)

    def test_risk_assessment_explain(self):
        """Get explanation for risk assessment"""
        vital = VitalSigns.objects.create(
            patient=self.patient,
            recorded_by=self.user,
            heart_rate=105,
            respiratory_rate=26,
            oxygen_saturation=Decimal('92.0'),
            bp_systolic=140,
            bp_diastolic=90,
            temperature=Decimal('38.2'),
        )

        assessment = RiskAssessment.objects.create(
            patient=self.patient,
            assessed_at=timezone.now(),
            news2_total=7,
            news2_hr_score=1,
            news2_rr_score=3,
            news2_spo2_score=2,
            news2_bp_score=0,
            news2_temp_score=1,
            trend_score=0,
            trend_level='low',
            multi_param_score=0,
            multi_param_pattern='stable',
            combined_risk=7,
            risk_level='high',
            explanation_text='Elevated NEWS2',
            recommendation='Close monitoring',
            decision_logic={},
            multi_param_details={'worsening_count': 0, 'pattern': 'stable', 'contributing_vitals': []}
        )
        assessment.vital_signs.add(vital)

        response = self.client.get(f'/vitals/api/v1/risk-assessments/{assessment.id}/explain/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('executive_summary', response.data)
        self.assertIn('contributing_factors', response.data)
        self.assertIn('next_actions', response.data)

    def test_risk_timeline(self):
        """Get risk timeline for patient"""
        now = timezone.now()

        # Create 3 vitals/assessments (vitals trigger signal handler)
        for i in range(3):
            VitalSigns.objects.create(
                patient=self.patient,
                recorded_by=self.user,
                heart_rate=75 + (i * 10),
                respiratory_rate=16 + (i * 2),
                oxygen_saturation=Decimal('97.0') - Decimal(str(i * 0.5)),
                bp_systolic=120,
                bp_diastolic=80,
                temperature=Decimal('37.0'),
                recorded_at=now - timedelta(hours=2-i)
            )

        response = self.client.get(f'/vitals/api/v1/risk-timeline/?patient_id={self.patient.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should have assessments (at least 3, possibly more from signal handler)
        self.assertGreaterEqual(len(response.data['timeline']), 3)
        self.assertGreaterEqual(response.data['assessment_count'], 3)

    def test_vital_contribution(self):
        """Get how vital contributed to risk"""
        vital = VitalSigns.objects.create(
            patient=self.patient,
            recorded_by=self.user,
            heart_rate=105,
            respiratory_rate=26,
            oxygen_saturation=Decimal('92.0'),
            bp_systolic=140,
            bp_diastolic=90,
            temperature=Decimal('38.2'),
        )

        assessment = RiskAssessment.objects.create(
            patient=self.patient,
            assessed_at=timezone.now(),
            news2_total=7,
            news2_hr_score=1,
            news2_rr_score=3,
            news2_spo2_score=2,
            news2_bp_score=0,
            news2_temp_score=1,
            trend_score=0,
            trend_level='low',
            multi_param_score=0,
            multi_param_pattern='stable',
            combined_risk=7,
            risk_level='high',
            explanation_text='Elevated',
            recommendation='Monitor',
            decision_logic={},
            multi_param_details={'worsening_count': 0, 'pattern': 'stable', 'contributing_vitals': []}
        )
        assessment.vital_signs.add(vital)

        response = self.client.get(f'/vitals/api/v1/vitals/{vital.id}/contribution/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('vital_contributions', response.data)

    def test_patient_risk_summary(self):
        """Get patient risk summary"""
        vital = VitalSigns.objects.create(
            patient=self.patient,
            recorded_by=self.user,
            heart_rate=105,
            respiratory_rate=26,
            oxygen_saturation=Decimal('92.0'),
            bp_systolic=140,
            bp_diastolic=90,
            temperature=Decimal('38.2'),
        )

        assessment = RiskAssessment.objects.create(
            patient=self.patient,
            assessed_at=timezone.now(),
            news2_total=7,
            news2_hr_score=1,
            news2_rr_score=3,
            news2_spo2_score=2,
            news2_bp_score=0,
            news2_temp_score=1,
            trend_score=0,
            trend_level='low',
            multi_param_score=0,
            multi_param_pattern='stable',
            combined_risk=7,
            risk_level='high',
            explanation_text='Elevated',
            recommendation='Close monitoring required',
            decision_logic={},
            multi_param_details={'worsening_count': 0, 'pattern': 'stable', 'contributing_vitals': []}
        )
        assessment.vital_signs.add(vital)

        response = self.client.get(f'/vitals/api/v1/patient-risk-summary/?patient_id={self.patient.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('current_status', response.data)
        self.assertIn('contributing_factors', response.data)
        self.assertIn('next_actions', response.data)
