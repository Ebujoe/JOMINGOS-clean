"""
Evaluate the real Jomingos NEWS2 + trend scoring (matching the exact thresholds
in vitals/models.py and the TREND_MULTIPLIER in vitals/utils/risk_engine.py)
against real ICU patients from PhysioNet/CinC Challenge 2012 (set-a), using
real in-hospital mortality as ground truth.

Usage:
    python manage.py run_physionet_evaluation

Data: experiments/data/physionet_2012_seta_cleaned.csv - one row per patient,
first and last vital sign readings over 48h, real in-hospital mortality outcome,
GCS-derived consciousness. Built from PhysioNet's openly published set-a records;
see experiments/data/README.md for how it was built and how to regenerate it.

An earlier candidate dataset (a 200,020-row Kaggle "human vital signs" set) was
tested and rejected first: every vital sign in it was confined to normal
physiological ranges, making it unfit for validating a clinical threshold-based
scorer. This PhysioNet dataset replaced it.
"""
from django.core.management.base import BaseCommand
from pathlib import Path
import pandas as pd
import numpy as np

from experiments.metrics import MetricsCalculator
from sklearn.model_selection import train_test_split

DATA_PATH = Path(__file__).resolve().parent.parent.parent / 'data' / 'physionet_2012_seta_cleaned.csv'


def news2_rr(rr):
    if rr is None or pd.isna(rr): return 0
    if rr <= 8: return 3
    if rr <= 11: return 1
    if rr <= 20: return 0
    if rr <= 24: return 2
    return 3

def news2_spo2(spo2):
    if spo2 is None or pd.isna(spo2): return 0
    if spo2 <= 91: return 3
    if spo2 <= 93: return 2
    if spo2 <= 95: return 1
    return 0

def news2_temp(t):
    if t is None or pd.isna(t): return 0
    if t <= 35.0: return 3
    if t <= 36.0: return 1
    if t <= 38.0: return 0
    if t <= 39.0: return 1
    return 2

def news2_bp(sbp):
    if sbp is None or pd.isna(sbp): return 0
    if sbp <= 90: return 3
    if sbp <= 100: return 2
    if sbp <= 110: return 1
    if sbp <= 219: return 0
    return 3

def news2_hr(hr):
    if hr is None or pd.isna(hr): return 0
    if hr <= 40: return 3
    if hr <= 50: return 1
    if hr <= 90: return 0
    if hr <= 110: return 1
    if hr <= 130: return 2
    return 3

def news2_consciousness(c):
    return 0 if c == 'A' else 3


def news2_total(row):
    return (
        news2_rr(row['Respiratory Rate']) + news2_spo2(row['Oxygen Saturation']) +
        news2_temp(row['Temperature']) + news2_bp(row['Systolic BP']) +
        news2_hr(row['Heart Rate']) + news2_consciousness(row['Consciousness'])
    )


def trend_score(row):
    """Real first-vs-last 48h delta per vital - a genuine trend signal, not a
    re-scoring of the same single reading. A simplification of the full rolling
    4/8/12-reading window in vitals/utils/trend_engine.py, necessitated by this
    dataset only offering first/last snapshots rather than a dense reading series."""
    score = 0.0
    def delta(a, b):
        if pd.isna(a) or pd.isna(b):
            return None
        return b - a

    d_hr = delta(row['Heart Rate'], row['Heart Rate (last)'])
    if d_hr is not None:
        if abs(d_hr) >= 20: score += 2
        elif abs(d_hr) >= 10: score += 1

    d_rr = delta(row['Respiratory Rate'], row['Respiratory Rate (last)'])
    if d_rr is not None:
        if abs(d_rr) >= 6: score += 2
        elif abs(d_rr) >= 3: score += 1

    d_spo2 = delta(row['Oxygen Saturation'], row['Oxygen Saturation (last)'])
    if d_spo2 is not None:
        if d_spo2 <= -4: score += 3
        elif d_spo2 <= -2: score += 1.5

    d_sbp = delta(row['Systolic BP'], row['Systolic BP (last)'])
    if d_sbp is not None:
        if d_sbp <= -20: score += 2
        elif d_sbp <= -10: score += 1

    return min(score, 10.0)


class Command(BaseCommand):
    help = 'Evaluate NEWS2 vs NEWS2+Trend against real PhysioNet ICU outcome data'

    def add_arguments(self, parser):
        parser.add_argument('--test-size', type=float, default=0.4)
        parser.add_argument('--random-seed', type=int, default=42)
        parser.add_argument('--min-age', type=int, default=None,
                             help='Filter to patients at or above this age, e.g. 65 for the elderly '
                                  'cohort your research plan specifies. Omit to use all ages.')

    def handle(self, *args, **options):
        if not DATA_PATH.exists():
            self.stderr.write(self.style.ERROR(f'Dataset not found: {DATA_PATH}'))
            return

        df = pd.read_csv(DATA_PATH)
        if options['min_age'] is not None:
            before = len(df)
            df = df[df['Age'] >= options['min_age']].reset_index(drop=True)
            self.stdout.write(f"Filtered to age >= {options['min_age']}: {len(df)} / {before} patients kept\n")

        train_df, test_df = train_test_split(
            df, test_size=options['test_size'], random_state=options['random_seed'],
            stratify=df['In-hospital Death']
        )

        y_true = test_df['In-hospital Death'].astype(int).values
        news2_scores = test_df.apply(news2_total, axis=1).values
        trend_scores = test_df.apply(trend_score, axis=1).values
        combined_scores = news2_scores + (trend_scores * 1.2)  # matches risk_engine.py TREND_MULTIPLIER

        calc = MetricsCalculator()

        y_pred_news2 = (news2_scores >= 7).astype(int)
        y_pred_combined = (combined_scores >= 7).astype(int)
        news2_m = calc.calculate_clinical_metrics(y_true, y_pred_news2, news2_scores)
        combined_m = calc.calculate_clinical_metrics(y_true, y_pred_combined, combined_scores)
        news2_m['roc_auc'] = calc.calculate_roc_metrics(y_true, news2_scores)['roc_auc']
        combined_m['roc_auc'] = calc.calculate_roc_metrics(y_true, combined_scores)['roc_auc']

        self.stdout.write(self.style.SUCCESS(
            f'\nPhysioNet/CinC Challenge 2012 (set-a) evaluation\n'
            f'{"=" * 60}\n'
            f'Total patients: {len(df)} | Train: {len(train_df)} | Test: {len(test_df)}\n'
            f'Test set real deaths: {int(y_true.sum())} / {len(test_df)} ({y_true.mean()*100:.1f}%)\n'
        ))

        self.stdout.write(f'\nNEWS2 alone (threshold >= 7):')
        for k in ['sensitivity', 'specificity', 'ppv', 'npv', 'f1_score', 'roc_auc']:
            self.stdout.write(f'  {k}: {news2_m[k]}')

        self.stdout.write(f'\nNEWS2 + real 48h trend (threshold >= 7):')
        for k in ['sensitivity', 'specificity', 'ppv', 'npv', 'f1_score', 'roc_auc']:
            self.stdout.write(f'  {k}: {combined_m[k]}')

        self.stdout.write(self.style.WARNING(
            '\nNote: comparing both at the same fixed threshold favours whichever '
            'approach happens to be better-calibrated at that cutoff. See '
            'experiments/data/README.md for the fairer best-threshold comparison '
            'and full methodological caveats before citing these numbers.'
        ))
