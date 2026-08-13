"""
Week 7: Clinical Validation & Expert Panel Review

Orchestrates expert clinical review and approval workflow.

Usage:
    python manage.py week7_clinical_validation
    python manage.py week7_clinical_validation --patient=1
    python manage.py week7_clinical_validation --report
    python manage.py week7_clinical_validation --safety-only
    python manage.py week7_clinical_validation --utility-only
"""

from django.core.management.base import BaseCommand
from patients.models import Patient
from vitals.models import PatientForecast
from vitals.utils.clinical_validation import (
    ExpertPanelReviewMaterials,
    SafetyAssessment,
    UtilityAssessment,
    ClinicalApprovalWorkflow,
)
from vitals.utils.clinical_preparation import (
    ClinicalCaseSummary,
    MultiPatientCohortAnalysis,
)
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Week 7 clinical validation with expert panel review"

    def add_arguments(self, parser):
        parser.add_argument('--patient', type=int, help='Specific patient ID')
        parser.add_argument('--report', action='store_true', help='Export JSON report')
        parser.add_argument('--safety-only', action='store_true', help='Safety assessment only')
        parser.add_argument('--utility-only', action='store_true', help='Utility assessment only')

    def handle(self, *args, **options):
        """Main command handler."""

        self.stdout.write(self.style.SUCCESS(f"\n{'='*70}"))
        self.stdout.write(self.style.SUCCESS("WEEK 7: CLINICAL VALIDATION"))
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
        all_forecasts = []

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
            all_forecasts.extend(forecasts)

            self.stdout.write(f"\nPatient: {patient.get_full_name()} (ID: {patient.id})")
            self.stdout.write("-" * 70)
            self.stdout.write(f"  Total forecasts: {len(forecasts)}")

            report_data['patients'][patient.id] = {
                'patient_name': patient.get_full_name(),
                'total_forecasts': len(forecasts),
            }

        if not all_forecasts:
            self.stdout.write(self.style.WARNING(
                "\nNo forecasts with actual values found.\n"
                "Week 7 clinical validation requires forecast data from Weeks 3-6.\n"
                "\nTo generate test data and forecasts:\n"
                "  1. python manage.py generate_test_vitals --count=50\n"
                "  2. python manage.py generate_forecasts --store --all-horizons\n"
                "\nDemonstrating Week 7 framework structure...\n"
            ))
            self._demonstrate_framework()
            return

        # Clinical case summaries
        self.stdout.write(f"\n{'='*70}")
        self.stdout.write("EXPERT PANEL REVIEW MATERIALS")
        self.stdout.write(f"{'='*70}\n")

        case_summaries = ClinicalCaseSummary.generate_case_summaries(patients_forecasts)

        self.stdout.write(f"Clinical case summaries generated: {len(case_summaries)}")
        for i, case in enumerate(case_summaries[:3]):
            self.stdout.write(
                f"  {i+1}. {case['label']} ({case['vital']} @ {case['horizon']}h): "
                f"Forecast={case['forecast']:.1f}, Actual={case['actual']:.1f}, "
                f"Error={case['error']:.1f}"
            )

        # Cohort analysis
        cohort = MultiPatientCohortAnalysis.analyze_cohort_performance(patients_forecasts)

        self.stdout.write(f"\nCohort analysis:")
        self.stdout.write(f"  Patients: {cohort.get('n_patients', 0)}")
        self.stdout.write(f"  Mean accuracy: {cohort.get('cohort_mean_accuracy', 0)*100:.0f}%")

        report_data['cohort'] = cohort

        # Expert panel review materials
        review_materials = ExpertPanelReviewMaterials.prepare_review_materials(
            all_forecasts, case_summaries, cohort, n_review=50
        )

        self.stdout.write(f"\nReview materials prepared: {review_materials['n_cases_selected']} cases")

        report_data['review_materials'] = {
            'n_cases_selected': review_materials['n_cases_selected'],
            'target_n_cases': review_materials['target_n_cases'],
        }

        # Safety assessment
        if not options['utility_only']:
            self.stdout.write(f"\n{'='*70}")
            self.stdout.write("SAFETY ASSESSMENT")
            self.stdout.write(f"{'='*70}\n")

            safety = SafetyAssessment.generate_safety_assessment(all_forecasts)

            self.stdout.write(f"Total predictions reviewed: {safety.get('total_predictions', 0)}")
            self.stdout.write(f"Unsafe predictions: {safety.get('unsafe_predictions', 0)} ({safety.get('unsafe_rate', 0)*100:.1f}%)")
            self.stdout.write(f"Missed alerts: {safety.get('missed_alerts', 0)} ({safety.get('missed_alert_rate', 0)*100:.1f}%)")
            self.stdout.write(f"False positives: {safety.get('false_positives', 0)} ({safety.get('false_positive_rate', 0)*100:.1f}%)")
            self.stdout.write(f"Safety score: {safety.get('safety_score', 0):.0f}/100")
            self.stdout.write(f"Safety status: {safety.get('safety_status', 'UNKNOWN')}")

            if safety.get('key_risks'):
                self.stdout.write("\nKey risks:")
                for risk in safety['key_risks']:
                    self.stdout.write(f"  - {risk}")

            report_data['safety_assessment'] = safety

        # Utility assessment
        if not options['safety_only']:
            self.stdout.write(f"\n{'='*70}")
            self.stdout.write("UTILITY ASSESSMENT")
            self.stdout.write(f"{'='*70}\n")

            utility = UtilityAssessment.generate_utility_assessment(all_forecasts, cohort)

            self.stdout.write(f"Overall accuracy: {utility.get('overall_accuracy', 0)*100:.0f}%")
            self.stdout.write(f"High-confidence predictions: {utility.get('high_confidence_predictions', 0)}")
            self.stdout.write(f"High-confidence accuracy: {utility.get('high_confidence_accuracy', 0)*100:.0f}%")
            self.stdout.write(f"Utility score: {utility.get('utility_score', 0):.0f}/100")
            self.stdout.write(f"Utility status: {utility.get('utility_status', 'UNKNOWN')}")
            self.stdout.write(f"Clinical impact: {utility.get('clinical_impact', 'UNKNOWN')}")

            self.stdout.write("\nHorizon utility:")
            for horizon, h_util in utility.get('horizon_utility', {}).items():
                self.stdout.write(
                    f"  {horizon}h: {h_util.get('accuracy', 0)*100:.0f}% accuracy "
                    f"({h_util.get('n_predictions', 0)} predictions)"
                )

            report_data['utility_assessment'] = utility

        # Clinical approval
        if not options['safety_only'] and not options['utility_only']:
            self.stdout.write(f"\n{'='*70}")
            self.stdout.write("CLINICAL APPROVAL DECISION")
            self.stdout.write(f"{'='*70}\n")

            approval = ClinicalApprovalWorkflow.generate_approval_summary(
                safety, utility
            )

            self.stdout.write(f"Approval status: {approval['approval_status']}")
            self.stdout.write(f"Approval confidence: {approval['approval_confidence']}")
            self.stdout.write(f"Safety approved: {approval['safety_approved']}")
            self.stdout.write(f"Utility approved: {approval['utility_approved']}")

            if approval.get('deployment_conditions'):
                self.stdout.write("\nDeployment conditions:")
                for condition in approval['deployment_conditions']:
                    self.stdout.write(f"  - {condition}")

            if approval.get('monitoring_requirements'):
                self.stdout.write("\nMonitoring requirements:")
                for req in approval['monitoring_requirements']:
                    self.stdout.write(f"  - {req}")

            report_data['approval'] = approval

        # Export report
        if options['report']:
            filename = f"week7_clinical_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            self.stdout.write(self.style.SUCCESS(f"\n✓ Report exported to: {filename}"))

        # Final summary
        self.stdout.write(f"\n{'='*70}")
        if not options['safety_only'] and not options['utility_only']:
            if approval.get('approval_status') == 'APPROVED_FOR_DEPLOYMENT':
                self.stdout.write(self.style.SUCCESS("[OK] APPROVED FOR WEEK 8 DEPLOYMENT"))
            elif approval.get('approval_status') == 'APPROVED_FOR_RESEARCH_USE':
                self.stdout.write(self.style.WARNING("[WARN] APPROVED FOR RESEARCH USE ONLY"))
            else:
                self.stdout.write(self.style.ERROR("[FAIL] NOT APPROVED - CONTINUE DEVELOPMENT"))
        self.stdout.write(f"{'='*70}\n")

    def _demonstrate_framework(self):
        """Demonstrate Week 7 framework structure."""
        self.stdout.write(self.style.SUCCESS("\nWEEK 7 FRAMEWORK STRUCTURE"))
        self.stdout.write("=" * 70)

        self.stdout.write("\nExpertPanelReviewMaterials:")
        self.stdout.write("  - Selects 50 diverse predictions for expert review")
        self.stdout.write("  - Stratified sampling by vital and horizon")
        self.stdout.write("  - Returns review items with clinical assessment")

        self.stdout.write("\nSafetyAssessment:")
        self.stdout.write("  - Unsafe predictions: error > 10 units")
        self.stdout.write("  - Missed alerts: true abnormality not detected")
        self.stdout.write("  - False positives: predicted abnormality not observed")
        self.stdout.write("  - Safety score: 0-100")

        self.stdout.write("\nUtilityAssessment:")
        self.stdout.write("  - Overall accuracy: within 95% PI")
        self.stdout.write("  - High-confidence accuracy: confidence >= 70%")
        self.stdout.write("  - Horizon-specific utility")
        self.stdout.write("  - Utility score: 0-100")

        self.stdout.write("\nClinicalApprovalWorkflow:")
        self.stdout.write("  - Safety gate: score >= 70")
        self.stdout.write("  - Utility gate: score >= 70")
        self.stdout.write("  - Outcomes:")
        self.stdout.write("    * APPROVED_FOR_DEPLOYMENT (both gates)")
        self.stdout.write("    * APPROVED_FOR_RESEARCH_USE (safety only)")
        self.stdout.write("    * NOT_APPROVED (insufficient metrics)")

        self.stdout.write(f"\n{'='*70}")
