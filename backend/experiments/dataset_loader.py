"""
Kaggle Dataset Loader

Loads human vital signs dataset (200,020 observations) for experimental evaluation.

Dataset Structure:
- 200,020 observations
- 17 columns: Patient ID, HR, RR, SpO2, BP, Temp, Age, Timestamp, Risk Category, etc.
- Ground truth: Risk Category (High Risk / Low Risk / Medium Risk)
- Single date: 2024-07-19

Reference: docs/DATASET_AUDIT.md
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Tuple, Dict, List
import logging

logger = logging.getLogger(__name__)


class DatasetLoader:
    """
    Load and preprocess Kaggle vital signs dataset.

    Attributes:
        dataset_path: Path to CSV file
        df: Loaded DataFrame
    """

    # Expected columns from Kaggle dataset
    REQUIRED_COLUMNS = [
        'Patient ID', 'Heart Rate', 'Respiratory Rate', 'Oxygen Saturation',
        'Systolic BP', 'Diastolic BP', 'Temperature', 'Age', 'Timestamp',
        'Risk Category', 'Gender', 'Medical Conditions', 'Current Medications',
        'Blood Glucose', 'Weight', 'Pain Score', 'Additional Notes'
    ]

    def __init__(self, dataset_path: str):
        """
        Initialize dataset loader.

        Args:
            dataset_path: Path to Kaggle CSV file
        """
        self.dataset_path = Path(dataset_path)
        self.df = None
        self._validate_path()

    def _validate_path(self):
        """Verify dataset file exists"""
        if not self.dataset_path.exists():
            raise FileNotFoundError(f"Dataset not found: {self.dataset_path}")
        logger.info(f"Dataset path valid: {self.dataset_path}")

    def load(self) -> pd.DataFrame:
        """
        Load dataset from CSV.

        Returns:
            DataFrame with all observations
        """
        if self.df is not None:
            return self.df

        logger.info(f"Loading dataset from {self.dataset_path}...")
        self.df = pd.read_csv(self.dataset_path)

        logger.info(f"Loaded {len(self.df)} observations")
        logger.info(f"Columns: {list(self.df.columns)}")

        # Validate structure
        self._validate_structure()

        return self.df

    def _validate_structure(self):
        """Validate dataset has expected structure"""
        # Check observation count
        if len(self.df) != 200020:
            logger.warning(f"Expected 200,020 observations, got {len(self.df)}")

        # Check required columns exist
        missing_cols = set(self.REQUIRED_COLUMNS) - set(self.df.columns)
        if missing_cols:
            logger.warning(f"Missing columns: {missing_cols}")

        # Check data types
        self._validate_data_types()

    def _validate_data_types(self):
        """Validate column data types"""
        numeric_columns = ['Heart Rate', 'Respiratory Rate', 'Oxygen Saturation',
                          'Systolic BP', 'Diastolic BP', 'Temperature', 'Age',
                          'Blood Glucose', 'Weight', 'Pain Score']

        for col in numeric_columns:
            if col in self.df.columns:
                try:
                    pd.to_numeric(self.df[col], errors='coerce')
                except:
                    logger.warning(f"Column {col} has non-numeric values")

    def get_statistics(self) -> Dict:
        """
        Get dataset statistics.

        Returns:
            Dictionary with dataset statistics
        """
        if self.df is None:
            self.load()

        stats = {
            'total_observations': len(self.df),
            'unique_patients': self.df['Patient ID'].nunique(),
            'date_range': {
                'min': self.df['Timestamp'].min() if 'Timestamp' in self.df.columns else None,
                'max': self.df['Timestamp'].max() if 'Timestamp' in self.df.columns else None,
            },
            'risk_distribution': self.df['Risk Category'].value_counts().to_dict() if 'Risk Category' in self.df.columns else {},
            'missing_values': self.df.isnull().sum().to_dict(),
        }

        return stats

    def get_patient_ids(self) -> np.ndarray:
        """
        Get unique patient IDs.

        Returns:
            Array of unique patient IDs
        """
        if self.df is None:
            self.load()

        return self.df['Patient ID'].unique()

    def get_patient_observations(self, patient_id: int) -> pd.DataFrame:
        """
        Get all observations for a patient.

        Args:
            patient_id: Patient ID to filter

        Returns:
            DataFrame with patient's observations (sorted by timestamp)
        """
        if self.df is None:
            self.load()

        patient_data = self.df[self.df['Patient ID'] == patient_id].copy()

        # Sort by timestamp if available
        if 'Timestamp' in patient_data.columns:
            patient_data = patient_data.sort_values('Timestamp')

        return patient_data

    def extract_vitals_for_model(self, observation: pd.Series) -> Dict:
        """
        Extract vital signs from observation.

        Converts dataset columns to model-compatible format.

        Args:
            observation: Single row from dataset

        Returns:
            Dictionary with vital signs
        """
        vitals = {
            'heart_rate': self._safe_float(observation.get('Heart Rate')),
            'respiratory_rate': self._safe_float(observation.get('Respiratory Rate')),
            'oxygen_saturation': self._safe_float(observation.get('Oxygen Saturation')),
            'bp_systolic': self._safe_float(observation.get('Systolic BP')),
            'bp_diastolic': self._safe_float(observation.get('Diastolic BP')),
            'temperature': self._safe_float(observation.get('Temperature')),
            'blood_glucose': self._safe_float(observation.get('Blood Glucose')),
            'weight_kg': self._safe_float(observation.get('Weight')),
            'pain_score': self._safe_int(observation.get('Pain Score')),
        }

        return vitals

    def get_ground_truth(self, observation: pd.Series) -> str:
        """
        Extract ground truth risk label from observation.

        Args:
            observation: Single row from dataset

        Returns:
            Risk category: 'low', 'medium', 'high'
        """
        risk_category = observation.get('Risk Category', 'unknown')

        if pd.isna(risk_category):
            return 'unknown'

        # Normalize to lowercase
        risk = str(risk_category).lower().strip()

        # Map to standard categories
        if 'low' in risk:
            return 'low'
        elif 'medium' in risk:
            return 'medium'
        elif 'high' in risk:
            return 'high'
        else:
            return 'unknown'

    @staticmethod
    def _safe_float(value) -> float:
        """Safely convert value to float"""
        try:
            if pd.isna(value):
                return None
            return float(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _safe_int(value) -> int:
        """Safely convert value to int"""
        try:
            if pd.isna(value):
                return None
            return int(value)
        except (ValueError, TypeError):
            return None

    def get_observation_count_by_patient(self) -> pd.Series:
        """
        Get number of observations per patient.

        Returns:
            Series with patient IDs as index, observation counts as values
        """
        if self.df is None:
            self.load()

        return self.df.groupby('Patient ID').size()

    def describe(self) -> str:
        """
        Generate dataset description string.

        Returns:
            Formatted description
        """
        if self.df is None:
            self.load()

        stats = self.get_statistics()

        description = f"""
Dataset Audit Report
{'='*50}

Total Observations: {stats['total_observations']:,}
Unique Patients: {stats['unique_patients']}

Risk Distribution:
{chr(10).join([f'  {k}: {v:,}' for k, v in stats['risk_distribution'].items()])}

Date Range: {stats['date_range']['min']} to {stats['date_range']['max']}

Missing Values:
{chr(10).join([f'  {k}: {v}' for k, v in sorted(stats['missing_values'].items()) if v > 0][:5])}

Dataset Ready for Experimental Pipeline.
"""
        return description


class DatasetAnalyzer:
    """
    Analyze dataset characteristics and distributions.
    """

    def __init__(self, df: pd.DataFrame):
        """
        Initialize analyzer with loaded dataset.

        Args:
            df: Pandas DataFrame with dataset
        """
        self.df = df

    def get_vital_statistics(self) -> Dict:
        """
        Calculate statistics for each vital sign.

        Returns:
            Dictionary with mean, std, min, max for each vital
        """
        vital_columns = ['Heart Rate', 'Respiratory Rate', 'Oxygen Saturation',
                        'Systolic BP', 'Diastolic BP', 'Temperature']

        stats = {}
        for col in vital_columns:
            if col in self.df.columns:
                numeric_data = pd.to_numeric(self.df[col], errors='coerce')
                stats[col] = {
                    'mean': numeric_data.mean(),
                    'std': numeric_data.std(),
                    'min': numeric_data.min(),
                    'max': numeric_data.max(),
                    'median': numeric_data.median(),
                    'missing': numeric_data.isna().sum(),
                }

        return stats

    def get_risk_correlations(self) -> Dict:
        """
        Calculate correlations between vital signs and risk.

        Returns:
            Dictionary with correlation coefficients
        """
        # Would calculate vitals vs risk correlations
        # Requires encoding risk categories to numeric
        pass

    def get_class_balance(self) -> Dict:
        """
        Get class distribution for risk categories.

        Returns:
            Dictionary with counts and percentages
        """
        if 'Risk Category' not in self.df.columns:
            return {}

        value_counts = self.df['Risk Category'].value_counts()
        total = len(self.df)

        return {
            category: {
                'count': int(count),
                'percentage': round(count / total * 100, 2)
            }
            for category, count in value_counts.items()
        }
