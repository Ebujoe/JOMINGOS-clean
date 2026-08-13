"""
Week 6: Clinical Preparation & Final Readiness Assessment

Generates materials for clinical expert review before Week 7 deployment.

Usage:
    python manage.py week6_clinical_prep
    python manage.py week6_clinical_prep --patient=1
    python manage.py week6_clinical_prep --report
"""

from django.core.management.base import BaseCommand
from patients.models import Patient
from vitals.models import PatientForecast
from vitals.utils.clinical_preparation import (
    ExtendedCrossValidationReport,
    MultiPatientCohortAnalysis,
    ClinicalCaseSummary,
    FinalReadinessChecklist,
    RiskAssessment,
)
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Week 6 clinical preparation with extended CV and readiness assessment"

    def add_arguments(self, parser):
        parser.add_argument('--patient', type=int, help='Specific patient ID')
        parser.add_argument('--report', action='store_true', help='Export JSON report')

    def handle(self, *args, **options):
        """Main command handler."""

        self.stdout.write(self.style.SUCCESS(f"\n{'='*70}"))
        self.stdout.write(self.style.SUCCESS("WEEK 6: CLINICAL PREPARATION"))
        self.stdout.write(self.style.SUCCESS(f"{'='*70}\n"))

        # Get patients
        if options['patient']:
            patients = Patient.objects.filter(id=options['patient'])
        else:
            patients = Patient.objects.all()

        if not patients.exists():
            self.stdout.write(self.style.ERROR("No patients found"))
            return

        report_data = {
            'timestamp': str(datetime.now()),
            'patients': {},
        }

        patients_forecasts = {}

        for patient in patients:
            forecasts = list(PatientForecast.objects.filter(patient=patient).values())

            if not forecasts:
                continue

            # Convert Decimal to float
            for f in forecasts:
                for key in ['forecast_value', 'actual_value', 'prediction_interval_90_lower',
                           'prediction_interval_90_upper', 'prediction_interval_95_lower',
                           'prediction_interval_95_upper']:
                    if f.get(key):
                        f[key] = float(f[key])

            patients_forecasts[patient.id] = forecasts

            # Extended CV report
            cv_report = ExtendedCrossValidationReport.generate_comprehensive_report(forecasts)

            self.stdout.write(f"\nPatient: {patient.get_full_name()} (ID: {patient.id})")
            self.stdout.write("-" * 70)
            self.stdout.write(f"  Forecasts: {cv_report.get('total_forecasts', 0)}")
            self.stdout.write(f"  Status: {cv_report.get('status', 'unknown')}")
            self.stdout.write(f"  MAE: {cv_report.get('mae', 0):.2f}")
            self.stdout.write(f"  Accuracy: {cv_report.get('accuracy_rate', 0)*100:.0f}%")
            self.stdout.write(f"  Recommendation: {cv_report.get('recommendation', 'TBD')}")

            report_data['patients'][patient.id] = {
                'patient_name': patient.get_full_name(),
                'cv_report': cv_report,
            }

        # Cohort analysis
        if len(patients_forecasts) > 1:
            self.stdout.write(f"\n{'='*70}")
            self.stdout.write("COHORT ANALYSIS")
            self.stdout.write(f"{'='*70}\n")

            cohort = MultiPatientCohortAnalysis.analyze_cohort_performance(patients_forecasts)

            self.stdout.write(f"Patients: {cohort.get('n_patients', 0)}")
            self.stdout.write(f"Total forecasts: {cohort.get('total_forecasts', 0)}")
            self.stdout.write(f"Mean accuracy: {cohort.get('cohort_mean_accuracy', 0)*100:.0f}% ± {cohort.get('cohort_std_accuracy', 0)*100:.0f}%")
            self.stdout.write(f"Mean MAE: {cohort.get('cohort_mean_mae', 0):.2f} ± {cohort.get('cohort_std_mae', 0):.2f}")

            report_data['cohort_analysis'] = cohort

        # Case summaries
        self.stdout.write(f"\n{'='*70}")
        self.stdout.write("CLINICAL CASE SUMMARIES")
        self.stdout.write(f"{'='*70}\n")

        all_forecasts = [f for forecasts in patients_forecasts.values() for f in forecasts]
        cases = ClinicalCaseSummary.generate_case_summaries({1: all_forecasts})

        for case in cases[:5]:
            self.stdout.write(f"  Case: {case['label']} ({case['vital']} @ {case['horizon']}h)")
            self.stdout.write(f"    Forecast: {case['forecast']:.1f}, Actual: {case['actual']:.1f}, Error: {case['error']:.1f}")
            pi_status = 'YES' if case['within_pi'] else 'NO'
            self.stdout.write(f"    Confidence: {case['confidence']:.0f}%, Within PI: {pi_status}")

        report_data['case_summaries'] = cases

        # Final readiness
        self.stdout.write(f"\n{'='*70}")
        self.stdout.write("FINAL READINESS ASSESSMENT")
        self.stdout.write(f"{'='*70}\n")

        cv_report = ExtendedCrossValidationReport.generate_comprehensive_report(all_forecasts) if all_forecasts else {}
        cohort = MultiPatientCohortAnalysis.analyze_cohort_performance(patients_forecasts) if len(patients_forecasts) > 1 else {}

        readiness = FinalReadinessChecklist.generate_checklist(cv_report, cohort, cases)
        risk = RiskAssessment.generate_risk_assessment(readiness)

        self.stdout.write(f"Readiness Score: {readiness['readiness_score']:.0f}/100")
        self.stdout.write(f"Status: {readiness['status']}")
        self.stdout.write(f"Risk Level: {risk['overall_risk_level']}")
        self.stdout.write(f"Recommendation: {risk['recommended_action']}")

        report_data['readiness'] = readiness
        report_data['risk_assessment'] = risk

        # Export report
        if options['report']:
            filename = f"week6_clinical_prep_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            self.stdout.write(self.style.SUCCESS(f"\n✓ Report exported to: {filename}"))

        # Final message
        self.stdout.write(f"\n{'='*70}")
        if readiness['readiness_score'] >= 75:
            self.stdout.write(self.style.SUCCESS("[OK] READY FOR WEEK 7 CLINICAL VALIDATION"))
        elif readiness['readiness_score'] >= 50:
            self.stdout.write(self.style.WARNING("[WARN] READY WITH MONITORING FOR WEEK 7"))
        else:
            self.stdout.write(self.style.ERROR("[FAIL] CONTINUE DEVELOPMENT BEFORE WEEK 7"))
