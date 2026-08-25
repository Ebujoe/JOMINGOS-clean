# live_alerts/models.py
from django.db import models
from django.utils import timezone
from accounts.models import User
from patients.models import Patient


class FallAlert(models.Model):
    """A fall event detected by the pose model, logged automatically with a snapshot."""

    LABEL_CHOICES = [
         ('fallen', 'Fallen/Falling'),
    ]
    STATUS_CHOICES = [
        ('new', 'New'),
        ('acknowledged', 'Acknowledged'),
        ('dismissed', 'Dismissed'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='fall_alerts')
    acknowledged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='fall_alerts_acknowledged')

    snapshot = models.ImageField(upload_to='fall_alerts/')
    label = models.CharField(max_length=20, choices=LABEL_CHOICES)
    confidence = models.FloatField(blank=True, null=True)  # probability score from the pose model, for audit trail

    detected_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    acknowledged_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-detected_at']

    def __str__(self):
        return f'{self.get_label_display()} alert for {self.patient} at {self.detected_at}'

    @property
    def status_badge(self):
        colors = {'new': 'danger', 'acknowledged': 'success', 'dismissed': 'secondary'}
        return colors.get(self.status, 'secondary')