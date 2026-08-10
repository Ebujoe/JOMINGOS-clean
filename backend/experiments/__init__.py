"""
Experiments Package - Phase 7

Experimental pipeline for evaluating deterioration detection system
on Kaggle dataset with 60/40 patient-level split.

Modules:
- dataset_loader: Load and preprocess Kaggle dataset
- experimental_split: Create 60/40 train/test split
- metrics: Calculate clinical evaluation metrics
- evaluation_pipeline: Run complete evaluation

Usage:
    from experiments import dataset_loader, experimental_split, metrics

    loader = dataset_loader.DatasetLoader('path/to/dataset.csv')
    df = loader.load()

    splitter = experimental_split.ExperimentalSplit(df)
    train_df, test_df = splitter.split(stratify_by='Risk Category')

    metrics_calc = metrics.MetricsCalculator()
    results = metrics_calc.calculate_clinical_metrics(y_true, y_pred)
"""

from .dataset_loader import DatasetLoader, DatasetAnalyzer
from .experimental_split import ExperimentalSplit, StratifiedSplitter
from .metrics import MetricsCalculator, PerformanceReport
from .evaluation_pipeline import EvaluationPipeline, ComparisonAnalysis

__all__ = [
    'DatasetLoader',
    'DatasetAnalyzer',
    'ExperimentalSplit',
    'StratifiedSplitter',
    'MetricsCalculator',
    'PerformanceReport',
    'EvaluationPipeline',
    'ComparisonAnalysis',
]
