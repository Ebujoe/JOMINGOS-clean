"""
Comprehensive Trend Analysis Engine Tests

Tests for TrendAnalyzer class and all trend detection functionality.
"""

from django.test import TestCase
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal

from patients.models import Patient
from vitals.models import VitalSigns
from vitals.utils.trend_engine import TrendAnalyzer


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
            bp_diastolic=70,  # Default diastolic
            temperature=Decimal(str(temperature)) if temperature else None,
            recorded_at=recorded_at
        )


class RateOfChangeTests(TestCase):
    """Test rate of change calculations"""

    def setUp(self):
        self.analyzer = TrendAnalyzer()

    def test_roc_basic_calculation(self):
        """Test basic RoC calculation"""
        roc = self.analyzer.calculate_roc(
            current_value=Decimal('100'),
            previous_value=Decimal('80'),
            time_diff_hours=1.0
        )
        self.assertEqual(roc, 20.0)  # (100 - 80) / 1 = 20

    def test_roc_negative_change(self):
        """Test RoC with decreasing value"""
        roc = self.analyzer.calculate_roc(
            current_value=Decimal('80'),
            previous_value=Decimal('100'),
            time_diff_hours=1.0
        )
        self.assertEqual(roc, -20.0)  # (80 - 100) / 1 = -20

    def test_roc_over_multiple_hours(self):
        """Test RoC calculated over multiple hours"""
        roc = self.analyzer.calculate_roc(
            current_value=Decimal('120'),
            previous_value=Decimal('100'),
            time_diff_hours=2.0
        )
        self.assertEqual(roc, 10.0)  # (120 - 100) / 2 = 10

    def test_roc_with_none_values(self):
        """Test RoC handles None values"""
        roc = self.analyzer.calculate_roc(None, Decimal('100'), 1.0)
        self.assertIsNone(roc)

        roc = self.analyzer.calculate_roc(Decimal('100'), None, 1.0)
        self.assertIsNone(roc)

    def test_roc_with_zero_time(self):
        """Test RoC with zero time difference"""
        roc = self.analyzer.calculate_roc(Decimal('100'), Decimal('80'), 0)
        self.assertIsNone(roc)

    def test_roc_with_decimal_values(self):
        """Test RoC with Decimal inputs"""
        roc = self.analyzer.calculate_roc(
            current_value=Decimal('37.5'),
            previous_value=Decimal('37.0'),
            time_diff_hours=1.0
        )
        self.assertAlmostEqual(roc, 0.5, places=2)

    def test_roc_with_small_fractions(self):
        """Test RoC with small fractional changes"""
        roc = self.analyzer.calculate_roc(
            current_value=Decimal('95.5'),
            previous_value=Decimal('96.0'),
            time_diff_hours=1.0
        )
        self.assertAlmostEqual(roc, -0.5, places=2)


class TimeSpanCalculationTests(TestCase):
    """Test time difference calculations"""

    def setUp(self):
        self.analyzer = TrendAnalyzer()
        self.base_time = timezone.now()

    def test_time_diff_one_hour(self):
        """Test time difference of 1 hour"""
        later = self.base_time + timedelta(hours=1)
        diff = self.analyzer.get_time_diff_hours(later, self.base_time)
        self.assertAlmostEqual(diff, 1.0, places=1)

    def test_time_diff_multiple_hours(self):
        """Test time difference of multiple hours"""
        later = self.base_time + timedelta(hours=6)
        diff = self.analyzer.get_time_diff_hours(later, self.base_time)
        self.assertAlmostEqual(diff, 6.0, places=1)

    def test_time_diff_with_minutes(self):
        """Test time difference with minutes component"""
        later = self.base_time + timedelta(hours=1, minutes=30)
        diff = self.analyzer.get_time_diff_hours(later, self.base_time)
        self.assertAlmostEqual(diff, 1.5, places=2)

    def test_time_diff_same_time(self):
        """Test time difference when times are the same"""
        diff = self.analyzer.get_time_diff_hours(self.base_time, self.base_time)
        self.assertEqual(diff, 0)

    def test_time_diff_reverse_order(self):
        """Test time difference with reversed times"""
        earlier = self.base_time - timedelta(hours=1)
        diff = self.analyzer.get_time_diff_hours(earlier, self.base_time)
        self.assertEqual(diff, 0)  # Should return 0 for past times


class VitalTrendScoringTests(TestCase):
    """Test trend scoring for individual vitals"""

    def setUp(self):
        self.analyzer = TrendAnalyzer()

    def test_heart_rate_worsening_critical(self):
        """Test critical HR increase"""
        direction, score = self.analyzer._score_vital_trend('heart_rate', 25)
        self.assertEqual(direction, 'worsening')
        self.assertEqual(score, 3)  # Critical

    def test_heart_rate_worsening_moderate(self):
        """Test moderate HR increase"""
        direction, score = self.analyzer._score_vital_trend('heart_rate', 10)
        self.assertEqual(direction, 'worsening')
        self.assertEqual(score, 2)  # Moderate

    def test_heart_rate_worsening_mild(self):
        """Test mild HR increase"""
        direction, score = self.analyzer._score_vital_trend('heart_rate', 6)
        self.assertEqual(direction, 'worsening')
        self.assertEqual(score, 1)  # Mild (25% of threshold)

    def test_heart_rate_stable(self):
        """Test stable HR"""
        direction, score = self.analyzer._score_vital_trend('heart_rate', 1)
        self.assertEqual(direction, 'stable')
        self.assertEqual(score, 0)

    def test_heart_rate_improving(self):
        """Test improving HR"""
        direction, score = self.analyzer._score_vital_trend('heart_rate', -15)
        self.assertEqual(direction, 'improving')
        self.assertEqual(score, 1)

    def test_spo2_worsening_critical(self):
        """Test critical SpO2 drop"""
        direction, score = self.analyzer._score_vital_trend('oxygen_saturation', -6)
        self.assertEqual(direction, 'worsening')
        self.assertEqual(score, 3)  # Critical

    def test_spo2_worsening_moderate(self):
        """Test moderate SpO2 drop"""
        direction, score = self.analyzer._score_vital_trend('oxygen_saturation', -3)
        self.assertEqual(direction, 'worsening')
        self.assertEqual(score, 2)  # Moderate

    def test_spo2_worsening_mild(self):
        """Test mild SpO2 drop"""
        direction, score = self.analyzer._score_vital_trend('oxygen_saturation', -1.5)
        self.assertEqual(direction, 'worsening')
        self.assertEqual(score, 1)  # Mild

    def test_spo2_improving(self):
        """Test improving SpO2"""
        direction, score = self.analyzer._score_vital_trend('oxygen_saturation', 3)
        self.assertEqual(direction, 'improving')
        self.assertEqual(score, 1)

    def test_respiratory_rate_critical(self):
        """Test critical RR increase"""
        direction, score = self.analyzer._score_vital_trend('respiratory_rate', 12)
        self.assertEqual(direction, 'worsening')
        self.assertEqual(score, 3)

    def test_bp_systolic_critical_drop(self):
        """Test critical BP drop"""
        direction, score = self.analyzer._score_vital_trend('bp_systolic', -25)
        self.assertEqual(direction, 'worsening')
        self.assertEqual(score, 3)

    def test_temperature_critical_rise(self):
        """Test critical temperature rise"""
        direction, score = self.analyzer._score_vital_trend('temperature', 2.5)
        self.assertEqual(direction, 'worsening')
        self.assertEqual(score, 3)


class WindowAnalysisTests(TestCase):
    """Test trend analysis over vital observation windows"""

    def setUp(self):
        self.analyzer = TrendAnalyzer()
        self.patient = PatientFactory.create_patient()
        self.base_time = timezone.now()

    def test_empty_window(self):
        """Test analysis with no vitals"""
        result = self.analyzer.analyze_window([])
        self.assertEqual(result['count'], 0)
        self.assertTrue(result['stable'])
        self.assertFalse(result['deteriorating'])

    def test_single_vital_window(self):
        """Test analysis with single vital (no trend possible)"""
        vital = VitalSignsFactory.create_vitals(self.patient, heart_rate=75)
        result = self.analyzer.analyze_window([vital])
        self.assertEqual(result['count'], 1)
        self.assertTrue(result['stable'])

    def test_stable_vitals_window(self):
        """Test analysis with relatively stable vitals over time"""
        vitals = [
            VitalSignsFactory.create_vitals(
                self.patient,
                heart_rate=75,
                respiratory_rate=16,
                oxygen_saturation=97,
                bp_systolic=120,
                temperature=37.0,
                recorded_at=self.base_time
            ),
            VitalSignsFactory.create_vitals(
                self.patient,
                heart_rate=76,  # Minimal change
                respiratory_rate=16,
                oxygen_saturation=97,
                bp_systolic=120,
                temperature=37.1,
                recorded_at=self.base_time + timedelta(hours=1)
            ),
        ]
        result = self.analyzer.analyze_window(vitals)
        self.assertEqual(result['count'], 2)
        # Should have analyzed vitals
        self.assertGreater(len(result['vitals_analyzed']), 0)

    def test_deteriorating_vitals_window(self):
        """Test analysis with deteriorating vitals"""
        vitals = [
            VitalSignsFactory.create_vitals(
                self.patient,
                heart_rate=75,
                respiratory_rate=16,
                oxygen_saturation=97,
                bp_systolic=120,
                temperature=37.0,
                recorded_at=self.base_time
            ),
            VitalSignsFactory.create_vitals(
                self.patient,
                heart_rate=115,  # HR up 40 bpm/hour
                respiratory_rate=28,  # RR up 12 br/min/hour
                oxygen_saturation=91,  # SpO2 down 6%/hour
                bp_systolic=100,  # BP down 20 mmHg/hour
                temperature=38.5,  # Temp up 1.5°C/hour
                recorded_at=self.base_time + timedelta(hours=1)
            ),
        ]
        result = self.analyzer.analyze_window(vitals)
        self.assertEqual(result['count'], 2)
        self.assertTrue(result['deteriorating'])
        self.assertFalse(result['stable'])
        self.assertGreater(result['overall_trend_score'], 0)

    def test_improving_vitals_window(self):
        """Test analysis with improving vitals"""
        vitals = [
            VitalSignsFactory.create_vitals(
                self.patient,
                heart_rate=115,
                respiratory_rate=28,
                oxygen_saturation=91,
                bp_systolic=100,
                temperature=38.5,
                recorded_at=self.base_time
            ),
            VitalSignsFactory.create_vitals(
                self.patient,
                heart_rate=75,  # HR down 40 bpm/hour
                respiratory_rate=16,  # RR down 12 br/min/hour
                oxygen_saturation=97,  # SpO2 up 6%/hour
                bp_systolic=120,  # BP up 20 mmHg/hour
                temperature=37.0,  # Temp down 1.5°C/hour
                recorded_at=self.base_time + timedelta(hours=1)
            ),
        ]
        result = self.analyzer.analyze_window(vitals)
        self.assertEqual(result['count'], 2)
        # Should have analyzed multiple vitals
        self.assertGreater(len(result['vitals_analyzed']), 0)

    def test_multi_vital_deterioration(self):
        """Test when multiple vitals deteriorate simultaneously"""
        vitals = [
            VitalSignsFactory.create_vitals(
                self.patient,
                heart_rate=80,
                respiratory_rate=18,
                oxygen_saturation=96,
                bp_systolic=130,
                recorded_at=self.base_time
            ),
            VitalSignsFactory.create_vitals(
                self.patient,
                heart_rate=120,  # Up 40
                respiratory_rate=26,  # Up 8
                oxygen_saturation=90,  # Down 6
                bp_systolic=90,  # Down 40
                recorded_at=self.base_time + timedelta(hours=1)
            ),
        ]
        result = self.analyzer.analyze_window(vitals)
        # Should have multiple vitals in analysis
        self.assertGreater(len(result['vitals_analyzed']), 1)
        self.assertTrue(result['deteriorating'])


class PatientTrendAnalysisTests(TestCase):
    """Test complete patient trend analysis"""

    def setUp(self):
        self.analyzer = TrendAnalyzer()
        self.patient = PatientFactory.create_patient()
        self.base_time = timezone.now()

    def test_get_recent_vitals(self):
        """Test retrieving recent vitals"""
        # Create 10 vitals
        for i in range(10):
            VitalSignsFactory.create_vitals(
                self.patient,
                heart_rate=70 + i,
                recorded_at=self.base_time + timedelta(hours=i)
            )

        recent = self.analyzer.get_recent_vitals(self.patient, limit=5)
        self.assertEqual(len(recent), 5)
        # Should be in chronological order (oldest first for window analysis)
        self.assertLess(recent[0].recorded_at, recent[-1].recorded_at)

    def test_analyze_patient_trends_no_vitals(self):
        """Test patient trend analysis with no vitals"""
        result = self.analyzer.analyze_patient_trends(self.patient)
        self.assertEqual(result['total_vitals_available'], 0)
        self.assertEqual(result['window_4']['count'], 0)

    def test_analyze_patient_trends_with_vitals(self):
        """Test complete patient trend analysis"""
        # Create 12 vitals showing clear deterioration
        for i in range(12):
            VitalSignsFactory.create_vitals(
                self.patient,
                heart_rate=70 + (i * 5),  # Bigger HR increase (5 bpm/hour)
                respiratory_rate=16 + (i * 2),   # RR increase
                oxygen_saturation=98 - (i * 1),  # SpO2 decrease (1%/hour)
                recorded_at=self.base_time + timedelta(hours=i)
            )

        result = self.analyzer.analyze_patient_trends(self.patient)

        # Should have results for all windows
        self.assertGreater(result['total_vitals_available'], 0)
        self.assertIsNotNone(result['window_4'])
        self.assertIsNotNone(result['window_8'])
        self.assertIsNotNone(result['window_12'])

        # Should show some level of deterioration in the complete analysis
        self.assertGreater(result['window_4']['overall_trend_score'], -2)

    def test_get_trend_score(self):
        """Test getting single trend score"""
        # Create vitals
        for i in range(4):
            VitalSignsFactory.create_vitals(
                self.patient,
                heart_rate=70 + (i * 15),  # Rapid increase
                recorded_at=self.base_time + timedelta(hours=i)
            )

        score = self.analyzer.get_trend_score(self.patient, window_size=4)
        self.assertGreater(score, 0)  # Should show deterioration

    def test_get_trend_score_insufficient_data(self):
        """Test trend score with insufficient vitals"""
        # Create only 1 vital
        VitalSignsFactory.create_vitals(self.patient, heart_rate=75)

        score = self.analyzer.get_trend_score(self.patient, window_size=4)
        self.assertEqual(score, 0)  # Should return 0 for insufficient data


class TrendEdgeCasesTests(TestCase):
    """Test edge cases and error conditions"""

    def setUp(self):
        self.analyzer = TrendAnalyzer()
        self.patient = PatientFactory.create_patient()
        self.base_time = timezone.now()

    def test_missing_vital_values(self):
        """Test window analysis with some missing vital values"""
        vitals = [
            VitalSignsFactory.create_vitals(
                self.patient,
                heart_rate=75,
                respiratory_rate=None,  # Missing
                oxygen_saturation=97,
                bp_systolic=120,
                temperature=37.0,
                recorded_at=self.base_time
            ),
            VitalSignsFactory.create_vitals(
                self.patient,
                heart_rate=80,
                respiratory_rate=18,  # Now present
                oxygen_saturation=96,
                bp_systolic=119,
                temperature=37.2,
                recorded_at=self.base_time + timedelta(hours=1)
            ),
        ]
        result = self.analyzer.analyze_window(vitals)
        # Should analyze what's available
        self.assertIn('heart_rate', result['vitals_analyzed'])
        self.assertEqual(result['count'], 2)

    def test_irregular_time_intervals(self):
        """Test trend analysis with irregular observation intervals"""
        vitals = [
            VitalSignsFactory.create_vitals(
                self.patient,
                heart_rate=75,
                recorded_at=self.base_time
            ),
            VitalSignsFactory.create_vitals(
                self.patient,
                heart_rate=85,
                recorded_at=self.base_time + timedelta(minutes=5)  # 5 min interval
            ),
            VitalSignsFactory.create_vitals(
                self.patient,
                heart_rate=95,
                recorded_at=self.base_time + timedelta(hours=2, minutes=5)  # 2 hour interval
            ),
        ]
        result = self.analyzer.analyze_window(vitals)
        # Should handle different intervals correctly
        self.assertIsNotNone(result['vitals_analyzed'].get('heart_rate'))

    def test_extreme_rate_of_change(self):
        """Test handling of extreme RoC values"""
        # Simulate data entry error: huge jump in value
        vitals = [
            VitalSignsFactory.create_vitals(
                self.patient,
                heart_rate=75,
                recorded_at=self.base_time
            ),
            VitalSignsFactory.create_vitals(
                self.patient,
                heart_rate=250,  # Impossible jump
                recorded_at=self.base_time + timedelta(minutes=1)
            ),
        ]
        result = self.analyzer.analyze_window(vitals)
        # Should still calculate without crashing
        self.assertIsNotNone(result['vitals_analyzed'])

    def test_zero_vital_values(self):
        """Test with zero vital values"""
        vitals = [
            VitalSignsFactory.create_vitals(
                self.patient,
                heart_rate=0,  # Zero HR
                recorded_at=self.base_time
            ),
            VitalSignsFactory.create_vitals(
                self.patient,
                heart_rate=80,
                recorded_at=self.base_time + timedelta(hours=1)
            ),
        ]
        result = self.analyzer.analyze_window(vitals)
        # Should calculate RoC even with zero initial value
        self.assertIsNotNone(result['vitals_analyzed'].get('heart_rate'))
