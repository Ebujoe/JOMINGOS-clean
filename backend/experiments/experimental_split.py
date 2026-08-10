"""
60/40 Patient-Level Experimental Split

Implements stratified train/test split at patient level.

Methodology:
- 60% of patients → training set
- 40% of patients → test set
- All observations for each patient stay together (no data leakage)
- Stratification by risk category (maintain distribution)

Reference: Master Build Prompt Section 27 (60/40 Experiment)
"""

import numpy as np
import pandas as pd
from typing import Tuple, List, Dict
from sklearn.model_selection import train_test_split
import logging

logger = logging.getLogger(__name__)


class ExperimentalSplit:
    """
    Create reproducible 60/40 train/test split at patient level.
    """

    RANDOM_SEED = 42  # For reproducibility

    def __init__(self, df: pd.DataFrame, random_seed: int = RANDOM_SEED):
        """
        Initialize splitter with dataset.

        Args:
            df: Dataset with patient-level observations
            random_seed: Seed for reproducibility
        """
        self.df = df
        self.random_seed = random_seed
        self.train_patients = None
        self.test_patients = None
        self.train_df = None
        self.test_df = None

    def split(self, stratify_by: str = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Create 60/40 patient-level split.

        Args:
            stratify_by: Column to stratify by (e.g., 'Risk Category')

        Returns:
            Tuple of (train_df, test_df)
        """
        logger.info("Creating 60/40 patient-level experimental split...")

        # Get unique patients
        unique_patients = self.df['Patient ID'].unique()
        n_patients = len(unique_patients)

        logger.info(f"Total unique patients: {n_patients}")

        # Get patient-level risk category if stratifying
        if stratify_by and stratify_by in self.df.columns:
            patient_risk = self.df.groupby('Patient ID')[stratify_by].first()
            stratify = patient_risk.values
        else:
            stratify = None

        # Split patients (60/40)
        self.train_patients, self.test_patients = train_test_split(
            unique_patients,
            test_size=0.4,  # 40% test
            train_size=0.6,  # 60% train
            random_state=self.random_seed,
            stratify=stratify
        )

        logger.info(f"Train patients: {len(self.train_patients)} ({len(self.train_patients)/n_patients*100:.1f}%)")
        logger.info(f"Test patients: {len(self.test_patients)} ({len(self.test_patients)/n_patients*100:.1f}%)")

        # Create dataframes
        self.train_df = self.df[self.df['Patient ID'].isin(self.train_patients)].copy()
        self.test_df = self.df[self.df['Patient ID'].isin(self.test_patients)].copy()

        logger.info(f"Train observations: {len(self.train_df):,}")
        logger.info(f"Test observations: {len(self.test_df):,}")

        # Verify no overlap
        assert len(set(self.train_patients) & set(self.test_patients)) == 0, "Patient overlap detected!"
        logger.info("✓ No patient overlap between train and test")

        return self.train_df, self.test_df

    def get_train_data(self) -> pd.DataFrame:
        """Get training dataset"""
        if self.train_df is None:
            raise RuntimeError("Must call split() first")
        return self.train_df

    def get_test_data(self) -> pd.DataFrame:
        """Get test dataset"""
        if self.test_df is None:
            raise RuntimeError("Must call split() first")
        return self.test_df

    def get_split_summary(self) -> Dict:
        """
        Get summary statistics about the split.

        Returns:
            Dictionary with split statistics
        """
        if self.train_df is None or self.test_df is None:
            raise RuntimeError("Must call split() first")

        summary = {
            'total_patients': len(self.train_patients) + len(self.test_patients),
            'train_patients': len(self.train_patients),
            'test_patients': len(self.test_patients),
            'train_observations': len(self.train_df),
            'test_observations': len(self.test_df),
            'train_percentage': round(len(self.train_patients) / (len(self.train_patients) + len(self.test_patients)) * 100, 1),
            'test_percentage': round(len(self.test_patients) / (len(self.train_patients) + len(self.test_patients)) * 100, 1),
        }

        # Risk distribution
        if 'Risk Category' in self.train_df.columns:
            summary['train_risk_distribution'] = self.train_df['Risk Category'].value_counts().to_dict()
            summary['test_risk_distribution'] = self.test_df['Risk Category'].value_counts().to_dict()

        return summary

    def get_patient_count_per_set(self) -> Tuple[int, int]:
        """
        Get patient counts for train and test.

        Returns:
            Tuple of (train_count, test_count)
        """
        return len(self.train_patients), len(self.test_patients)

    def get_observation_count_per_set(self) -> Tuple[int, int]:
        """
        Get observation counts for train and test.

        Returns:
            Tuple of (train_count, test_count)
        """
        return len(self.train_df), len(self.test_df)

    def print_summary(self):
        """Print split summary to logger"""
        summary = self.get_split_summary()

        print(f"""
Experimental Split Summary
{'='*50}

Patient Distribution:
  Total patients: {summary['total_patients']}
  Train: {summary['train_patients']} ({summary['train_percentage']}%)
  Test: {summary['test_patients']} ({summary['test_percentage']}%)

Observation Distribution:
  Total observations: {summary['train_observations'] + summary['test_observations']:,}
  Train: {summary['train_observations']:,} observations
  Test: {summary['test_observations']:,} observations

Risk Distribution (Train):
{chr(10).join([f"  {k}: {v:,}" for k, v in summary.get('train_risk_distribution', {}).items()])}

Risk Distribution (Test):
{chr(10).join([f"  {k}: {v:,}" for k, v in summary.get('test_risk_distribution', {}).items()])}

Split maintained at patient level (no data leakage).
Random seed: {self.random_seed}
""")


class StratifiedSplitter:
    """
    Create stratified split ensuring balanced classes in both sets.
    """

    def __init__(self, df: pd.DataFrame):
        """Initialize stratified splitter"""
        self.df = df

    def stratified_split(self, stratify_column: str, test_size: float = 0.4) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Create stratified split by patient groups.

        Ensures both train and test sets maintain similar class distributions.

        Args:
            stratify_column: Column to stratify by (e.g., 'Risk Category')
            test_size: Fraction of patients for test set

        Returns:
            Tuple of (train_df, test_df)
        """
        # Get patient-level stratification
        patient_groups = self.df.groupby('Patient ID')[stratify_column].first()

        unique_patients = patient_groups.index.values
        patient_classes = patient_groups.values

        # Split with stratification
        train_patients, test_patients = train_test_split(
            unique_patients,
            test_size=test_size,
            random_state=42,
            stratify=patient_classes
        )

        train_df = self.df[self.df['Patient ID'].isin(train_patients)].copy()
        test_df = self.df[self.df['Patient ID'].isin(test_patients)].copy()

        return train_df, test_df

    def verify_stratification(self, train_df: pd.DataFrame, test_df: pd.DataFrame, stratify_column: str) -> Dict:
        """
        Verify stratification maintained class balance.

        Args:
            train_df: Training data
            test_df: Test data
            stratify_column: Column that was stratified

        Returns:
            Dictionary with distribution comparison
        """
        train_dist = train_df[stratify_column].value_counts(normalize=True).to_dict()
        test_dist = test_df[stratify_column].value_counts(normalize=True).to_dict()

        return {
            'train_distribution': train_dist,
            'test_distribution': test_dist,
            'balanced': abs(sum(train_dist.values()) - sum(test_dist.values())) < 0.01
        }
