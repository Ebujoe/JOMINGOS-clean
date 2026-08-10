"""
Phase 8: Evaluation Pipeline - Unit Tests

Tests for evaluation pipeline, NEWS2 scoring, and comparison analysis.
"""

import unittest
import numpy as np
import pandas as pd
from .evaluation_pipeline import EvaluationPipeline, ComparisonAnalysis


class EvaluationPipelineTests(unittest.TestCase):
    """Test evaluation pipeline functionality"""

    def setUp(self):
        """Create mock test dataset"""
        n_obs = 100
        self.test_df = pd.DataFrame({
            'Patient ID': np.repeat(np.arange(10), n_obs // 10),
            'Heart Rate': np.random.randint(50, 120, n_obs),
            'Respiratory Rate': np.random.randint(10, 25, n_obs),
            'Oxygen Saturation': np.random.uniform(90, 99, n_obs),
            'Systolic BP': np.random.randint(100, 160, n_obs),
            'Diastolic BP': np.random.randint(60, 100, n_obs),
            'Temperature': np.random.uniform(36, 39, n_obs),
            'Risk Category': np.random.choice(['Low', 'High'], n_obs),
        })

    def test_pipeline_initialization(self):
        """Initialize evaluation pipeline"""
        pipeline = EvaluationPipeline(self.test_df)
        self.assertIsNotNone(pipeline)
        self.assertEqual(len(pipeline.test_df), len(self.test_df))

    def test_vitals_extraction(self):
        """Extract vitals from observation"""
        pipeline = EvaluationPipeline(self.test_df)
        obs = self.test_df.iloc[0]

        vitals = pipeline.extract_vitals(obs)

        self.assertIn('heart_rate', vitals)
        self.assertIn('respiratory_rate', vitals)
        self.assertIn('oxygen_saturation', vitals)
        self.assertIn('systolic_bp', vitals)

    def test_ground_truth_extraction(self):
        """Extract ground truth labels"""
        pipeline = EvaluationPipeline(self.test_df)

        # Test high risk
        obs_high = pd.Series({'Risk Category': 'High'})
        self.assertEqual(pipeline.get_ground_truth(obs_high), 1)

        # Test low risk
        obs_low = pd.Series({'Risk Category': 'Low'})
        self.assertEqual(pipeline.get_ground_truth(obs_low), 0)

        # Test medium risk
        obs_medium = pd.Series({'Risk Category': 'Medium'})
        self.assertEqual(pipeline.get_ground_truth(obs_medium), 0)

    def test_news2_score_calculation(self):
        """Calculate NEWS2 score"""
        pipeline = EvaluationPipeline(self.test_df)

        vitals_normal = {
            'heart_rate': 70,
            'respiratory_rate': 16,
            'oxygen_saturation': 98,
            'systolic_bp': 120,
            'diastolic_bp': 80,
            'temperature': 37,
        }

        score_normal = pipeline.calculate_news2_score(vitals_normal)
        self.assertEqual(score_normal, 0)  # All normal

        vitals_abnormal = {
            'heart_rate': 130,
            'respiratory_rate': 25,
            'oxygen_saturation': 90,
            'systolic_bp': 90,
            'diastolic_bp': 60,
            'temperature': 39.5,
        }

        score_abnormal = pipeline.calculate_news2_score(vitals_abnormal)
        self.assertGreater(score_abnormal, 5)  # Should have points

    def test_trend_score_calculation(self):
        """Calculate trend score"""
        pipeline = EvaluationPipeline(self.test_df)

        vitals_normal = {
            'heart_rate': 70,
            'respiratory_rate': 16,
            'oxygen_saturation': 98,
            'systolic_bp': 120,
            'diastolic_bp': 80,
            'temperature': 37,
        }

        score_normal = pipeline.calculate_trend_score(vitals_normal)
        self.assertLess(score_normal, 2)  # Low trend score for normal

        vitals_abnormal = {
            'heart_rate': 140,
            'respiratory_rate': 28,
            'oxygen_saturation': 88,
            'systolic_bp': 85,
            'diastolic_bp': 50,
            'temperature': 37,
        }

        score_abnormal = pipeline.calculate_trend_score(vitals_abnormal)
        self.assertGreater(score_abnormal, 5)  # High trend score

    def test_evaluation_runs(self):
        """Run complete evaluation"""
        pipeline = EvaluationPipeline(self.test_df)
        results = pipeline.run_evaluation()

        self.assertIn('news2_only', results)
        self.assertIn('news2_plus_trends', results)
        self.assertIn('comparison', results)
        self.assertEqual(results['test_set_size'], len(self.test_df))

    def test_evaluation_produces_metrics(self):
        """Evaluation produces valid metrics"""
        pipeline = EvaluationPipeline(self.test_df)
        results = pipeline.run_evaluation()

        news2_metrics = results['news2_only']
        combined_metrics = results['news2_plus_trends']

        # Check for required metrics
        for metric in ['sensitivity', 'specificity', 'ppv', 'f1_score']:
            self.assertIn(metric, news2_metrics)
            self.assertIn(metric, combined_metrics)

            # Metrics should be between 0 and 1
            self.assertGreaterEqual(news2_metrics[metric], 0)
            self.assertLessEqual(news2_metrics[metric], 1)
            self.assertGreaterEqual(combined_metrics[metric], 0)
            self.assertLessEqual(combined_metrics[metric], 1)

    def test_metric_comparison(self):
        """Metrics comparison between approaches"""
        pipeline = EvaluationPipeline(self.test_df)
        results = pipeline.run_evaluation()

        comparison = results['comparison']

        # Check comparison structure
        for metric in ['sensitivity', 'specificity', 'ppv', 'f1_score']:
            self.assertIn(metric, comparison)
            self.assertIn('news2_only', comparison[metric])
            self.assertIn('news2_plus_trends', comparison[metric])
            self.assertIn('improvement_pct', comparison[metric])
            self.assertIn('improvement_abs', comparison[metric])


class ComparisonAnalysisTests(unittest.TestCase):
    """Test comparison analysis"""

    def setUp(self):
        """Create mock evaluation results"""
        self.eval_results = {
            'test_set_size': 100,
            'test_set_observations': 1000,
            'news2_only': {
                'sensitivity': 0.75,
                'specificity': 0.88,
                'ppv': 0.72,
                'f1_score': 0.73,
                'miss_rate': 0.25,
                'false_alarm_rate': 0.28,
            },
            'news2_plus_trends': {
                'sensitivity': 0.92,
                'specificity': 0.94,
                'ppv': 0.86,
                'f1_score': 0.89,
                'miss_rate': 0.08,
                'false_alarm_rate': 0.14,
            },
            'comparison': {
                'sensitivity': {
                    'news2_only': 0.75,
                    'news2_plus_trends': 0.92,
                    'improvement_pct': 22.7,
                    'improvement_abs': 0.17,
                },
                'specificity': {
                    'news2_only': 0.88,
                    'news2_plus_trends': 0.94,
                    'improvement_pct': 6.8,
                    'improvement_abs': 0.06,
                },
                'ppv': {
                    'news2_only': 0.72,
                    'news2_plus_trends': 0.86,
                    'improvement_pct': 19.4,
                    'improvement_abs': 0.14,
                },
                'f1_score': {
                    'news2_only': 0.73,
                    'news2_plus_trends': 0.89,
                    'improvement_pct': 21.9,
                    'improvement_abs': 0.16,
                },
            },
        }

    def test_comparison_analysis_initialization(self):
        """Initialize comparison analysis"""
        analysis = ComparisonAnalysis(self.eval_results)
        self.assertIsNotNone(analysis)

    def test_comparison_report_generation(self):
        """Generate comparison report"""
        analysis = ComparisonAnalysis(self.eval_results)
        report = analysis.generate_comparison_report()

        self.assertIn('KAGGLE DATASET EVALUATION REPORT', report)
        self.assertIn('NEWS2 ONLY vs NEWS2 + TRENDS', report)
        self.assertIn('Sensitivity', report)
        self.assertIn('Specificity', report)
        self.assertIn('Alert Accuracy', report)

    def test_comparison_dict(self):
        """Convert comparison to dictionary"""
        analysis = ComparisonAnalysis(self.eval_results)
        result = analysis.get_comparison_dict()

        self.assertIn('test_set_size', result)
        self.assertIn('news2_only', result)
        self.assertIn('news2_plus_trends', result)
        self.assertIn('improvement_summary', result)

    def test_success_criteria_check(self):
        """Check success criteria"""
        analysis = ComparisonAnalysis(self.eval_results)
        check = analysis.get_success_criteria_check()

        self.assertIn('criteria', check)
        self.assertIn('passed', check)
        self.assertIn('total', check)
        self.assertIn('success', check)

        # This example should meet most criteria
        self.assertGreater(check['passed'], 2)

    def test_success_criteria_interpretation(self):
        """Interpret success criteria results"""
        analysis = ComparisonAnalysis(self.eval_results)
        check = analysis.get_success_criteria_check()

        criteria = check['criteria']

        # These should pass with the mock data
        self.assertTrue(criteria['sensitivity_>90%'])
        self.assertTrue(criteria['specificity_>95%'] or criteria['ppv_>85%'])

    def test_clinical_impact_calculation(self):
        """Calculate clinical impact"""
        analysis = ComparisonAnalysis(self.eval_results)
        report = analysis.generate_comparison_report()

        # Report should mention lives potentially saved
        self.assertIn('Lives potentially saved', report)
        self.assertIn('deteriorating patients', report)


class SafeConversionTests(unittest.TestCase):
    """Test safe value conversion"""

    def test_safe_float_conversion(self):
        """Test safe float conversion"""
        pipeline = EvaluationPipeline(pd.DataFrame())

        self.assertEqual(pipeline._safe_float(3.14), 3.14)
        self.assertEqual(pipeline._safe_float("42"), 42.0)
        self.assertIsNone(pipeline._safe_float(np.nan))
        self.assertIsNone(pipeline._safe_float("invalid"))


if __name__ == '__main__':
    unittest.main()
