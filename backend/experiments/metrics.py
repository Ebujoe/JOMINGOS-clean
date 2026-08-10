"""
Evaluation Metrics Calculator

Calculates clinical and statistical metrics for deterioration detection.

Metrics:
- Sensitivity (TP/(TP+FN)): Catch deteriorating patients
- Specificity (TN/(TN+FP)): Avoid false alarms
- PPV (TP/(TP+FP)): Trust alert accuracy
- NPV (TN/(TN+FN)): Confidence in "no alert"
- ROC-AUC: Overall discrimination
- F1 Score: Balanced performance
"""

import numpy as np
from typing import Dict, List, Tuple
from sklearn.metrics import (
    confusion_matrix, accuracy_score, precision_score, recall_score,
    f1_score, roc_auc_score, roc_curve, precision_recall_curve
)
import logging

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """
    Calculate clinical evaluation metrics.
    """

    def __init__(self):
        """Initialize metrics calculator"""
        pass

    def calculate_confusion_matrix_metrics(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict:
        """
        Calculate metrics from confusion matrix.

        Args:
            y_true: Ground truth labels (0=normal, 1=deterioration)
            y_pred: Predicted labels (0=normal, 1=deterioration)

        Returns:
            Dictionary with TP, FP, TN, FN, sensitivity, specificity, PPV, NPV
        """
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()

        sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
        ppv = tp / (tp + fp) if (tp + fp) > 0 else 0  # Precision
        npv = tn / (tn + fn) if (tn + fn) > 0 else 0

        return {
            'true_positive': int(tp),
            'false_positive': int(fp),
            'true_negative': int(tn),
            'false_negative': int(fn),
            'sensitivity': round(sensitivity, 4),  # Recall
            'specificity': round(specificity, 4),
            'ppv': round(ppv, 4),  # Precision
            'npv': round(npv, 4),
        }

    def calculate_classification_metrics(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict:
        """
        Calculate standard classification metrics.

        Args:
            y_true: Ground truth labels
            y_pred: Predicted labels

        Returns:
            Dictionary with accuracy, precision, recall, F1
        """
        return {
            'accuracy': round(accuracy_score(y_true, y_pred), 4),
            'precision': round(precision_score(y_true, y_pred, zero_division=0), 4),
            'recall': round(recall_score(y_true, y_pred, zero_division=0), 4),
            'f1_score': round(f1_score(y_true, y_pred, zero_division=0), 4),
        }

    def calculate_roc_metrics(self, y_true: np.ndarray, y_scores: np.ndarray) -> Dict:
        """
        Calculate ROC curve metrics.

        Args:
            y_true: Ground truth labels (binary)
            y_scores: Prediction scores (probabilities or risk scores)

        Returns:
            Dictionary with ROC-AUC and threshold data
        """
        try:
            auc = roc_auc_score(y_true, y_scores)
            fpr, tpr, thresholds = roc_curve(y_true, y_scores)

            return {
                'roc_auc': round(auc, 4),
                'fpr': fpr.tolist(),
                'tpr': tpr.tolist(),
                'thresholds': thresholds.tolist(),
            }
        except Exception as e:
            logger.error(f"Error calculating ROC metrics: {e}")
            return {'roc_auc': None, 'error': str(e)}

    def calculate_pr_metrics(self, y_true: np.ndarray, y_scores: np.ndarray) -> Dict:
        """
        Calculate Precision-Recall curve metrics.

        Args:
            y_true: Ground truth labels
            y_scores: Prediction scores

        Returns:
            Dictionary with PR curve data
        """
        try:
            precision, recall, thresholds = precision_recall_curve(y_true, y_scores)

            return {
                'precision': precision.tolist(),
                'recall': recall.tolist(),
                'thresholds': thresholds.tolist(),
            }
        except Exception as e:
            logger.error(f"Error calculating PR metrics: {e}")
            return {'error': str(e)}

    def calculate_clinical_metrics(self, y_true: np.ndarray, y_pred: np.ndarray, risk_scores: np.ndarray) -> Dict:
        """
        Calculate clinical-specific metrics.

        Args:
            y_true: Ground truth labels (1=deterioration)
            y_pred: Predicted labels
            risk_scores: Continuous risk scores

        Returns:
            Dictionary with clinical metrics
        """
        cm_metrics = self.calculate_confusion_matrix_metrics(y_true, y_pred)
        clf_metrics = self.calculate_classification_metrics(y_true, y_pred)

        # Calculate alert accuracy (PPV is critical for clinical use)
        alert_accuracy = cm_metrics['ppv']  # When system alerts, how often correct?

        # Calculate miss rate (what % of true deterioration was missed)
        miss_rate = 1 - cm_metrics['sensitivity']

        # Calculate false alarm rate (what % of alerts are false)
        false_alarm_rate = 1 - alert_accuracy if alert_accuracy > 0 else 1

        return {
            **cm_metrics,
            **clf_metrics,
            'alert_accuracy': round(alert_accuracy, 4),  # PPV - most important for clinical
            'miss_rate': round(miss_rate, 4),  # 1 - Sensitivity
            'false_alarm_rate': round(false_alarm_rate, 4),  # 1 - PPV
            'mean_risk_score': round(np.mean(risk_scores), 2),
            'std_risk_score': round(np.std(risk_scores), 2),
        }

    def calculate_threshold_analysis(self, y_true: np.ndarray, y_scores: np.ndarray, thresholds: List[float] = None) -> Dict:
        """
        Analyze performance at different thresholds.

        Helps find optimal alert threshold.

        Args:
            y_true: Ground truth labels
            y_scores: Continuous risk scores
            thresholds: Thresholds to test (default: auto-generated)

        Returns:
            Dictionary with metrics at each threshold
        """
        if thresholds is None:
            thresholds = np.arange(0, 1.01, 0.1)

        results = {}
        for threshold in thresholds:
            y_pred = (y_scores >= threshold).astype(int)

            try:
                metrics = self.calculate_confusion_matrix_metrics(y_true, y_pred)
                results[round(threshold, 2)] = metrics
            except:
                pass

        return results

    def find_optimal_threshold(self, y_true: np.ndarray, y_scores: np.ndarray, metric: str = 'f1') -> Dict:
        """
        Find optimal threshold for alert decision.

        Args:
            y_true: Ground truth labels
            y_scores: Continuous risk scores
            metric: Metric to optimize ('f1', 'sensitivity', 'ppv')

        Returns:
            Dictionary with optimal threshold and metrics
        """
        thresholds = np.arange(0, 1.01, 0.05)
        best_threshold = 0
        best_score = 0
        best_metrics = {}

        for threshold in thresholds:
            y_pred = (y_scores >= threshold).astype(int)

            try:
                metrics = self.calculate_confusion_matrix_metrics(y_true, y_pred)

                # Select optimization metric
                if metric == 'f1':
                    score = 2 * (metrics['ppv'] * metrics['sensitivity']) / (metrics['ppv'] + metrics['sensitivity'] + 1e-6)
                elif metric == 'sensitivity':
                    score = metrics['sensitivity']
                elif metric == 'ppv':
                    score = metrics['ppv']
                else:
                    score = metrics.get(metric, 0)

                if score > best_score:
                    best_score = score
                    best_threshold = threshold
                    best_metrics = metrics
            except:
                pass

        return {
            'optimal_threshold': round(best_threshold, 2),
            'optimization_metric': metric,
            'best_score': round(best_score, 4),
            'metrics_at_threshold': best_metrics,
        }


class PerformanceReport:
    """
    Generate comprehensive performance report.
    """

    def __init__(self, metrics: Dict):
        """
        Initialize report with calculated metrics.

        Args:
            metrics: Dictionary of calculated metrics
        """
        self.metrics = metrics

    def generate_summary(self) -> str:
        """
        Generate text summary of performance.

        Returns:
            Formatted summary string
        """
        report = f"""
Deterioration Detection - Performance Report
{'='*60}

Confusion Matrix:
  TP (Caught deterioration): {self.metrics.get('true_positive', 0)}
  FP (False alarms): {self.metrics.get('false_positive', 0)}
  TN (Correctly normal): {self.metrics.get('true_negative', 0)}
  FN (Missed deterioration): {self.metrics.get('false_negative', 0)}

Clinical Metrics:
  Sensitivity (% caught): {self.metrics.get('sensitivity', 0)*100:.1f}%
  Specificity (% normal correct): {self.metrics.get('specificity', 0)*100:.1f}%
  Alert Accuracy (PPV): {self.metrics.get('ppv', 0)*100:.1f}%
  Miss Rate: {self.metrics.get('miss_rate', 0)*100:.1f}%
  False Alarm Rate: {self.metrics.get('false_alarm_rate', 0)*100:.1f}%

Classification Metrics:
  Accuracy: {self.metrics.get('accuracy', 0)*100:.1f}%
  Precision: {self.metrics.get('precision', 0)*100:.1f}%
  Recall: {self.metrics.get('recall', 0)*100:.1f}%
  F1 Score: {self.metrics.get('f1_score', 0)}

Interpretation:
  - High Sensitivity: System catches most deteriorating patients (goal: >95%)
  - High PPV: Alerts are accurate (goal: >80%)
  - Low False Alarm Rate: Reduces alert fatigue

Recommendation:
  {'✓ Good performance' if self.metrics.get('sensitivity', 0) > 0.9 and self.metrics.get('ppv', 0) > 0.75 else '⚠ Needs improvement'}
"""
        return report

    def to_dict(self) -> Dict:
        """Return metrics as dictionary"""
        return self.metrics
