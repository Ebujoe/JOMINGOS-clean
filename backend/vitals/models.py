from django.db import models
from django.utils import timezone
from accounts.models import User
from patients.models import Patient


class VitalSigns(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='vitals')
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='vitals_recorded')

    temperature = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, help_text='°C')
    bp_systolic = models.IntegerField(null=True, blank=True, help_text='mmHg')
    bp_diastolic = models.IntegerField(null=True, blank=True, help_text='mmHg')
    heart_rate = models.IntegerField(null=True, blank=True, help_text='bpm')
    respiratory_rate = models.IntegerField(null=True, blank=True, help_text='breaths/min')
    oxygen_saturation = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, help_text='%')
    blood_glucose = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, help_text='mmol/L')
    weight_kg = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    pain_score = models.IntegerField(null=True, blank=True, help_text='0-10 scale')

    recorded_at = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-recorded_at']
        verbose_name_plural = 'Vital Signs'

    def __str__(self):
        return f'Vitals for {self.patient} at {self.recorded_at.strftime("%d/%m/%Y %H:%M")}'

    @property
    def bp_display(self):
        if self.bp_systolic and self.bp_diastolic:
            return f'{self.bp_systolic}/{self.bp_diastolic}'
        return '—'

    @property
    def temp_status(self):
        if self.temperature is None:
            return 'secondary'
        t = float(self.temperature)
        if t < 36.0 or t > 37.5:
            return 'danger'
        return 'success'

    @property
    def spo2_status(self):
        if self.oxygen_saturation is None:
            return 'secondary'
        s = float(self.oxygen_saturation)
        if s < 94:
            return 'danger'
        if s < 96:
            return 'warning'
        return 'success'

    @property
    def hr_status(self):
        if self.heart_rate is None:
            return 'secondary'
        h = self.heart_rate
        if h < 50 or h > 100:
            return 'danger'
        return 'success'

    # ----------------------
    # NEWS2 SCORING SYSTEM
    # ----------------------

    @property
    def news2_respiratory_score(self):
        rr = self.respiratory_rate
        if rr is None:
            return 0
        if rr <= 8:
            return 3
        if rr <= 11:
            return 1
        if rr <= 20:
            return 0
        if rr <= 24:
            return 2
        return 3

    @property
    def news2_spo2_score(self):
        spo2 = self.oxygen_saturation
        if spo2 is None:
            return 0
        if spo2 <= 91:
            return 3
        if spo2 <= 93:
            return 2
        if spo2 <= 95:
            return 1
        return 0

    @property
    def news2_temp_score(self):
        temp = self.temperature
        if temp is None:
            return 0
        if temp <= 35.0:
            return 3
        if temp <= 36.0:
            return 1
        if temp <= 38.0:
            return 0
        if temp <= 39.0:
            return 1
        return 2

    @property
    def news2_bp_score(self):
        bp = self.bp_systolic
        if bp is None:
            return 0
        if bp <= 90:
            return 3
        if bp <= 100:
            return 2
        if bp <= 110:
            return 1
        if bp <= 219:
            return 0
        return 3

    @property
    def news2_hr_score(self):
        hr = self.heart_rate
        if hr is None:
            return 0
        if hr <= 40:
            return 3
        if hr <= 50:
            return 1
        if hr <= 90:
            return 0
        if hr <= 110:
            return 1
        if hr <= 130:
            return 2
        return 3

    @property
    def news2_total(self):
        return (
            self.news2_respiratory_score +
            self.news2_spo2_score +
            self.news2_temp_score +
            self.news2_bp_score +
            self.news2_hr_score
        )

    @property
    def news2_level(self):
        score = self.news2_total
        if score <= 4:
            return 'low'
        if score <= 6:
            return 'medium'
        return 'high'

    @property
    def news2_color(self):
        return {
            'low': 'success',
            'medium': 'warning',
            'high': 'danger'
        }.get(self.news2_level, 'secondary')

    @property
    def news2_label(self):
        return {
            'low': 'Low Risk',
            'medium': 'Medium Risk',
            'high': 'HIGH RISK'
        }.get(self.news2_level, '')


# ============================================================================
# AUTOMATIC DETERIORATION DETECTION
# ============================================================================
# This signal handler automatically detects when a patient is deteriorating
# as soon as vital signs are recorded. No manual intervention needed!

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

@receiver(post_save, sender=VitalSigns)
def auto_detect_deterioration(sender, instance, created, **kwargs):
    """
    PHASE 4: INTEGRATION - RESEARCH-BASED DETERIORATION DETECTION

    Uses Phase 3 RiskAssessmentEngine to:
    1. Combine NEWS2 scoring (Phase 1)
    2. Analyze vital trends (Phase 2)
    3. Detect multi-parameter deterioration (Phase 3)
    4. Create RiskAssessment records for traceability
    5. Generate alerts based on combined risk
    """

    if not created:
        return

    try:
        from vitals.utils import RiskAssessmentEngine
        from deterioration_alerts.models import DeteriorationAlert

        # ========== STEP 1: ASSESS PATIENT RISK ==========
        engine = RiskAssessmentEngine()
        assessment = engine.assess_patient(instance.patient)

        # ========== STEP 2: CREATE RISKASSESSMENT RECORD ==========
        if assessment['data_available']:
            risk_record = RiskAssessment.objects.create(
                patient=instance.patient,
                assessed_at=timezone.now(),
                # NEWS2 components
                news2_total=assessment['news2']['score'],
                news2_hr_score=assessment['news2']['hr_score'],
                news2_rr_score=assessment['news2']['rr_score'],
                news2_spo2_score=assessment['news2']['spo2_score'],
                news2_bp_score=assessment['news2']['bp_score'],
                news2_temp_score=assessment['news2']['temp_score'],
                # Trend analysis
                trend_score=assessment['trend']['score'],
                # Multi-parameter analysis
                multi_param_score=assessment['multi_parameter']['multi_param_score'],
                multi_param_details={
                    'pattern': assessment['multi_parameter']['pattern'],
                    'worsening_count': assessment['multi_parameter']['worsening_count'],
                    'deteriorating_together': assessment['multi_parameter']['deteriorating_together'],
                    'contributing_vitals': assessment['multi_parameter']['contributing_vitals'],
                },
                # Combined risk
                combined_risk=round(assessment['combined_risk']),
                risk_level=assessment['risk_level'],
                explanation_text=assessment['explanation'],
                decision_logic={
                    'news2_score': assessment['news2']['score'],
                    'trend_score': assessment['trend']['score'],
                    'multi_param_pattern': assessment['multi_parameter']['pattern'],
                    'combined_formula': f"NEWS2({assessment['news2']['score']}) + Trend*1.2({assessment['trend']['score']*1.2:.1f}) + MultiParam({assessment['multi_parameter']['multi_param_score']}) = {assessment['combined_risk']:.1f}",
                    'algorithm_version': '3.0-phase-4',
                },
            )
            risk_record.vital_signs.add(instance)

            # ========== STEP 3: DETERMINE IF ALERT NEEDED ==========
            should_alert, alert_reason = engine.should_create_alert(
                instance.patient,
                assessment['combined_risk']
            )

            # ========== STEP 4: CREATE ALERT IF NEEDED ==========
            if should_alert:
                priority_map = {
                    'critical': 'critical',
                    'high': 'high',
                    'medium': 'medium',
                    'low': 'low',
                }
                priority = priority_map.get(assessment['risk_level'], 'medium')

                DeteriorationAlert.objects.create(
                    patient=instance.patient,
                    alert_type='research_deterioration_detection',
                    priority=priority,
                    status='active',
                    trigger_value=float(assessment['combined_risk']),
                    trigger_reason=alert_reason,
                    related_vital=instance,
                    risk_assessment=risk_record,
                )

                # ========== STEP 5: LOG ALERT ==========
                print(f"\n{'='*70}")
                print(f"[DETERIORATION ALERT] {instance.patient.get_full_name()}")
                print(f"{'='*70}")
                print(f"Risk Level: {assessment['risk_level'].upper()}")
                print(f"Combined Risk: {assessment['combined_risk']:.1f}")
                print(f"  • NEWS2 Score: {assessment['news2']['score']}")
                print(f"  • Trend Score: {assessment['trend']['score']}")
                print(f"  • Multi-Parameter: {assessment['multi_parameter']['pattern']}")
                print(f"Explanation: {assessment['explanation']}")
                print(f"Recommendation: {assessment['recommendation']}")
                print(f"{'='*70}\n")

    except Exception as e:
        print(f"[ERROR] Deterioration detection failed: {e}")
        import traceback
        traceback.print_exc()


# ============================================================================
# RISK ASSESSMENT MODEL - FOR RESEARCH TRACEABILITY
# ============================================================================
# Stores complete decision trace for every risk assessment
# Enables "why this result?" explanations and research reproducibility

class RiskAssessment(models.Model):
    """
    Complete risk assessment record for traceability and explainability.

    This model stores:
    - All vital signs used in the assessment
    - NEWS2 component scores
    - Trend analysis results
    - Multi-parameter analysis
    - Combined risk calculation
    - Decision logic and reasoning
    - Clinical interpretation

    Enables reconstruction of "what did we know at timestamp T?"
    """

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='risk_assessments')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    assessed_at = models.DateTimeField()  # When assessment was made (not when stored)

    # Vital signs observations used in this assessment
    vital_signs = models.ManyToManyField(VitalSigns, related_name='risk_assessments')
    observation_count = models.IntegerField(default=1, help_text='Number of vital observations used')

    # ========================
    # NEWS2 COMPONENT SCORES
    # ========================
    news2_total = models.IntegerField()
    news2_hr_score = models.IntegerField()
    news2_rr_score = models.IntegerField()
    news2_spo2_score = models.IntegerField()
    news2_bp_score = models.IntegerField()
    news2_temp_score = models.IntegerField()

    # ========================
    # TREND ANALYSIS (3 WINDOWS)
    # ========================
    trend_window_4 = models.JSONField(default=dict, blank=True, help_text='Last 4 observations analysis')
    trend_window_8 = models.JSONField(default=dict, blank=True, help_text='Last 8 observations analysis')
    trend_window_12 = models.JSONField(default=dict, blank=True, help_text='Last 12 observations analysis')
    trend_score = models.IntegerField(default=0, help_text='Score from trend analysis (0+)')
    trend_level = models.CharField(max_length=20, default='low', choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')])

    # ========================
    # MULTI-PARAMETER ANALYSIS
    # ========================
    multi_param_score = models.IntegerField(default=0, help_text='Score from multiple vitals worsening together')
    multi_param_pattern = models.CharField(max_length=50, default='stable', help_text='Pattern of multi-parameter worsening')
    multi_param_details = models.JSONField(default=dict, blank=True, help_text='Which parameters moving together')

    # ========================
    # COMBINED RISK ASSESSMENT
    # ========================
    combined_risk = models.IntegerField(help_text='NEWS2 + trend + multi-parameter combined')

    RISK_LEVEL_CHOICES = [
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk'),
        ('critical', 'Critical'),
    ]
    risk_level = models.CharField(max_length=20, choices=RISK_LEVEL_CHOICES)

    # ========================
    # DECISION REASONING
    # ========================
    explanation_text = models.TextField(blank=True, help_text='Human-readable explanation of why this risk level')
    recommendation = models.TextField(blank=True, help_text='Clinical recommendation based on risk level')
    decision_logic = models.JSONField(default=dict, blank=True, help_text='Step-by-step reasoning in structured format')

    # ========================
    # SYSTEM INFORMATION
    # ========================
    algorithm_version = models.CharField(max_length=20, default='1.0.0')
    configuration_version = models.CharField(max_length=20, default='1.0.0')

    class Meta:
        ordering = ['-assessed_at']
        indexes = [
            models.Index(fields=['patient', '-assessed_at']),
        ]
        verbose_name_plural = 'Risk Assessments'

    def __str__(self):
        return f'Risk Assessment for {self.patient} at {self.assessed_at.strftime("%d/%m/%Y %H:%M")}'

    @property
    def risk_label(self):
        """Return human-readable risk label"""
        return dict(self.RISK_LEVEL_CHOICES).get(self.risk_level, 'Unknown')