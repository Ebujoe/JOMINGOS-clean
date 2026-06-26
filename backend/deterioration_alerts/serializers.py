from rest_framework import serializers
from .models import DeteriorationAlert, TrendAnalysis
from patients.models import Patient
from vitals.models import VitalSigns


class DeteriorationAlertSerializer(serializers.ModelSerializer):
    """Serializer for DeteriorationAlert - converts model to/from JSON"""
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    acknowledged_by_name = serializers.CharField(source='acknowledged_by.get_full_name', read_only=True, allow_null=True)

    class Meta:
        model = DeteriorationAlert
        fields = [
            'id', 'patient', 'patient_name', 'alert_type', 'priority', 'status',
            'trigger_value', 'trigger_reason', 'triggered_at', 'acknowledged_at',
            'acknowledged_by', 'acknowledged_by_name', 'is_suppressed'
        ]
        read_only_fields = ['triggered_at', 'acknowledged_at']


class TrendAnalysisSerializer(serializers.ModelSerializer):
    """Serializer for TrendAnalysis - converts model to/from JSON"""
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)

    class Meta:
        model = TrendAnalysis
        fields = [
            'id', 'patient', 'patient_name', 'window_size', 'news2_trend_slope',
            'news2_avg_current', 'news2_avg_previous', 'temp_trend', 'hr_trend',
            'rr_trend', 'spo2_trend', 'bp_systolic_trend', 'severity', 'risk_score',
            'analysed_at'
        ]
        read_only_fields = ['analysed_at']


class AlertDetailSerializer(serializers.ModelSerializer):
    """Detailed alert view with related vital signs data"""
    patient_details = serializers.SerializerMethodField()
    related_vital_data = serializers.SerializerMethodField()
    related_trend_data = serializers.SerializerMethodField()

    class Meta:
        model = DeteriorationAlert
        fields = '__all__'

    def get_patient_details(self, obj):
        return {
            'id': obj.patient.id,
            'name': obj.patient.get_full_name(),
            'age': obj.patient.get_age(),
            'care_level': obj.patient.care_level,
        }

    def get_related_vital_data(self, obj):
        if not obj.related_vital:
            return None
        return {
            'news2_score': obj.related_vital.news2_total,
            'news2_level': obj.related_vital.news2_level,
            'heart_rate': obj.related_vital.heart_rate,
            'respiratory_rate': obj.related_vital.respiratory_rate,
            'temperature': obj.related_vital.temperature,
            'oxygen_saturation': obj.related_vital.oxygen_saturation,
            'recorded_at': obj.related_vital.recorded_at,
        }

    def get_related_trend_data(self, obj):
        if not obj.related_trend:
            return None
        return {
            'severity': obj.related_trend.severity,
            'risk_score': obj.related_trend.risk_score,
            'news2_trend_slope': obj.related_trend.news2_trend_slope,
        }
