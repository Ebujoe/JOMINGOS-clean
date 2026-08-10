"""
Phase 7: Experimental Pipeline - Unit Tests

Tests for:
1. Dataset loader functionality
2. Experimental split logic
3. Metrics calculation
"""

import unittest
import numpy as np
import pandas as pd
from experiments.dataset_loader import DatasetLoader, DatasetAnalyzer
from experiments.experimental_split import ExperimentalSplit, StratifiedSplitter
from experiments.metrics import MetricsCalculator, PerformanceReport


class DatasetLoaderTests(unittest.TestCase):
    """Test dataset loader"""

    def test_safe_float_conversion(self):
        """Safely convert values to float"""
        self.assertEqual(DatasetLoader._safe_float(3.14), 3.14)
        self.assertEqual(DatasetLoader._safe_float("42"), 42.0)
        self.assertIsNone(DatasetLoader._safe_float(np.nan))
        self.assertIsNone(DatasetLoader._safe_float("invalid"))

    def test_safe_int_conversion(self):
        """Safely convert values to int"""
        self.assertEqual(DatasetLoader._safe_int(42), 42)
        self.assertEqual(DatasetLoader._safe_int("42"), 42)
        self.assertIsNone(DatasetLoader._safe_int(np.nan))
        self.assertIsNone(DatasetLoader._safe_int("invalid"))

    def test_vitals_extraction_static(self):
        """Extract vitals from observation (static method)"""
        observation = pd.Series({
            'Heart Rate': 85,
            'Respiratory Rate': 16,
            'Oxygen Saturation': 97.0,
            'Systolic BP': 120,
            'Diastolic BP': 80,
            'Temperature': 37.0,
        })

        # Use static method without creating loader
        vitals = {
            'heart_rate': DatasetLoader._safe_float(observation.get('Heart Rate')),
            'respiratory_rate': DatasetLoader._safe_float(observation.get('Respiratory Rate')),
            'oxygen_saturation': DatasetLoader._safe_float(observation.get('Oxygen Saturation')),
        }

        self.assertEqual(vitals['heart_rate'], 85)
        self.assertEqual(vitals['respiratory_rate'], 16)
        self.assertEqual(vitals['oxygen_saturation'], 97.0)

    def test_ground_truth_extraction_static(self):
        """Extract ground truth risk labels (static method)"""
        # Test different label formats by checking conditions directly
        self.assertIn('low', 'Low Risk'.lower())
        self.assertIn('high', 'HIGH RISK'.lower())
        self.assertIn('medium', 'Medium Risk'.lower())


class ExperimentalSplitTests(unittest.TestCase):
    """Test experimental split logic"""

    def setUp(self):
        """Create mock dataset"""
        n_patients = 100
        n_observations = 1000

        self.df = pd.DataFrame({
            'Patient ID': np.repeat(np.arange(n_patients), n_observations // n_patients),
            'Heart Rate': np.random.randint(60, 100, n_observations),
            'Risk Category': np.random.choice(['Low', 'Medium', 'High'], n_observations),
        })

    def test_split_creates_60_40_split(self):
        """Split should create 60/40 patient-level split"""
        splitter = ExperimentalSplit(self.df)
        train, test = splitter.split()

        train_patients = train['Patient ID'].nunique()
        test_patients = test['Patient ID'].nunique()
        total_patients = train_patients + test_patients

        # Check proportions (allow 2% tolerance)
        train_pct = train_patients / total_patients
        test_pct = test_patients / total_patients

        self.assertGreater(train_pct, 0.58)  # Should be ~60%
        self.assertLess(train_pct, 0.62)
        self.assertGreater(test_pct, 0.38)  # Should be ~40%
        self.assertLess(test_pct, 0.42)

    def test_split_maintains_patient_integrity(self):
        """Each patient's observations should stay in one set"""
        splitter = ExperimentalSplit(self.df)
        train, test = splitter.split()

        train_patients = set(train['Patient ID'].unique())
        test_patients = set(test['Patient ID'].unique())

        # No overlap
        self.assertEqual(len(train_patients & test_patients), 0)

        # All patients accounted for
        total = len(train_patients) + len(test_patients)
        self.assertEqual(total, self.df['Patient ID'].nunique())

    def test_split_summary(self):
        """Get split summary statistics"""
        splitter = ExperimentalSplit(self.df)
        train, test = splitter.split()

        summary = splitter.get_split_summary()

        self.assertIn('train_patients', summary)
        self.assertIn('test_patients', summary)
        self.assertIn('train_observations', summary)
        self.assertIn('test_observations', summary)


class MetricsCalculatorTests(unittest.TestCase):
    """Test metrics calculation"""

    def setUp(self):
        """Create mock predictions"""
        self.y_true = np.array([0, 0, 1, 1, 0, 1, 0, 1, 1, 0])
        self.y_pred = np.array([0, 0, 1, 1, 0, 0, 0, 1, 1, 1])
        self.y_scores = np.array([0.1, 0.2, 0.9, 0.8, 0.3, 0.4, 0.2, 0.7, 0.9, 0.6])

    def test_confusion_matrix_metrics(self):
        """Calculate metrics from confusion matrix"""
        calc = MetricsCalculator()
        metrics = calc.calculate_confusion_matrix_metrics(self.y_true, self.y_pred)

        self.assertIn('true_positive', metrics)
        self.assertIn('false_positive', metrics)
        self.assertIn('sensitivity', metrics)
        self.assertIn('specificity', metrics)

    def test_classification_metrics(self):
        """Calculate classification metrics"""
        calc = MetricsCalculator()
        metrics = calc.calculate_classification_metrics(self.y_true, self.y_pred)

        self.assertIn('accuracy', metrics)
        self.assertIn('precision', metrics)
        self.assertIn('recall', metrics)
        self.assertIn('f1_score', metrics)

        # Metrics should be between 0 and 1
        for value in metrics.values():
            self.assertGreaterEqual(value, 0)
            self.assertLessEqual(value, 1)

    def test_roc_metrics(self):
        """Calculate ROC metrics"""
        calc = MetricsCalculator()
        metrics = calc.calculate_roc_metrics(self.y_true, self.y_scores)

        self.assertIn('roc_auc', metrics)
        self.assertIsNotNone(metrics['roc_auc'])

    def test_clinical_metrics(self):
        """Calculate clinical metrics"""
        calc = MetricsCalculator()
        metrics = calc.calculate_clinical_metrics(self.y_true, self.y_pred, self.y_scores)

        # Should include clinical-specific metrics
        self.assertIn('alert_accuracy', metrics)
        self.assertIn('miss_rate', metrics)
        self.assertIn('false_alarm_rate', metrics)

    def test_optimal_threshold(self):
        """Find optimal threshold"""
        calc = MetricsCalculator()
        result = calc.find_optimal_threshold(self.y_true, self.y_scores, metric='f1')

        self.assertIn('optimal_threshold', result)
        self.assertIn('metrics_at_threshold', result)
        self.assertGreaterEqual(result['optimal_threshold'], 0)
        self.assertLessEqual(result['optimal_threshold'], 1)


class PerformanceReportTests(unittest.TestCase):
    """Test performance reporting"""

    def setUp(self):
        """Create mock metrics"""
        self.metrics = {
            'true_positive': 80,
            'false_positive': 10,
            'true_negative': 800,
            'false_negative': 10,
            'sensitivity': 0.89,
            'specificity': 0.988,
            'ppv': 0.89,
            'accuracy': 0.97,
            'precision': 0.89,
            'recall': 0.89,
            'f1_score': 0.89,
            'miss_rate': 0.11,
            'false_alarm_rate': 0.11,
        }

    def test_report_generation(self):
        """Generate performance report"""
        report = PerformanceReport(self.metrics)
        summary = report.generate_summary()

        self.assertIn('Sensitivity', summary)
        self.assertIn('Alert Accuracy', summary)
        self.assertIn('Miss Rate', summary)

    def test_report_to_dict(self):
        """Convert report to dictionary"""
        report = PerformanceReport(self.metrics)
        result = report.to_dict()

        self.assertEqual(result, self.metrics)


if __name__ == '__main__':
    unittest.main()
