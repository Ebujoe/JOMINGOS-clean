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
    This function runs AUTOMATICALLY every time a new VitalSigns record is created.

    It's like a trigger: When vital signs are recorded → This function runs

    Think of it like: A doorbell that rings when someone records vitals
    """

    # Only run for NEW vitals (not when updating existing ones)
    if not created:
        return

    try:
        from deterioration_alerts.inference_service import get_detector
        from deterioration_alerts.models import DeteriorationAlert

        # Step 1: Get the detector (loads the brain/model)
        detector = get_detector()

        # Step 2: Prepare the vital signs data for prediction
        # This is EXACTLY the same format the model was trained on
        vital_data = {
            'news2_total': instance.news2_total,
            'rr_score': instance.news2_respiratory_score,
            'spo2_score': instance.news2_spo2_score,
            'sbp_score': instance.news2_bp_score,
            'hr_score': instance.news2_hr_score,
            'temp_score': instance.news2_temp_score,
            'o2_score': 0,  # You can get this from instance if available
            'heart_rate_roc': 0,  # Will calculate properly later
            'resp_rate_roc': 0,
            'spo2_roc': 0,
            'systolic_bp_roc': 0,
            'trend_score': 0,
            'combined_risk_score': 0,
        }

        # Step 3: Make prediction
        prediction = detector.predict(vital_data)

        # Step 4: If the model says it's critical, create an alert
        if prediction['is_critical'] or prediction['alert_level'] in ['AMBER', 'RED']:
            # Create an alert in the database
            DeteriorationAlert.objects.create(
                patient=instance.patient,
                alert_type='ml_prediction',
                priority='critical' if prediction['alert_level'] == 'RED' else 'high',
                status='active',
                trigger_value=prediction['probability'],
                trigger_reason=f"ML model prediction: {prediction['alert_level']} ({prediction['confidence']:.1f}%)",
                related_vital=instance,
            )

            # Print to console so you can see it working
            print(f"[ALERT] {instance.patient}: {prediction['alert_level']} alert generated")

    except Exception as e:
        # If something goes wrong, print the error (don't crash the app)
        print(f"[ERROR] Deterioration detection failed: {e}")