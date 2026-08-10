"""
JOMINGOS Vitals Utilities Package

Contains specialized modules for:
- Trend analysis (trend_engine.py - Phase 2)
- Risk assessment (risk_engine.py - Phase 3)
- Explainability (explainability.py - Phase 5)
"""

from .trend_engine import TrendAnalyzer
from .risk_engine import RiskAssessmentEngine

__all__ = ['TrendAnalyzer', 'RiskAssessmentEngine']
