"""
Django REST Framework Serializers for Vitals & Risk Assessments

Exposes VitalSigns and RiskAssessment data via API endpoints.
"""

from rest_framework import serializers
from vitals.models import VitalSigns, RiskAssessment
from vitals.utils.explainability import ExplainabilityEngine


class VitalSignsSerializer(serializers.ModelSerializer):
    """Serialize VitalSigns with NEWS2 scores"""

    news2_total = serializers.ReadOnlyField()
    news2_color = serializers.ReadOnlyField()
    news2_label = serializers.ReadOnlyField()
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)

    class Meta:
        model = VitalSigns
        fields = [
            'id',
            'patient',
            'patient_name',
            'recorded_by',
            'heart_rate',
            'respiratory_rate',
            'oxygen_saturation',
            'bp_systolic',
            'bp_diastolic',
            'temperature',
            'blood_glucose',
            'weight_kg',
            'pain_score',
            'recorded_at',
            'notes',
            'news2_total',
            'news2_hr_score',
            'news2_respiratory_score',
            'news2_spo2_score',
            'news2_bp_score',
            'news2_temp_score',
            'news2_color',
            'news2_label',
        ]
        read_only_fields = [
            'id',
            'recorded_by',
            'recorded_at',
            'news2_total',
            'news2_hr_score',
            'news2_respiratory_score',
            'news2_spo2_score',
            'news2_bp_score',
            'news2_temp_score',
            'news2_color',
            'news2_label',
        ]


class RiskAssessmentSerializer(serializers.ModelSerializer):
    """Serialize RiskAssessment with full decision logic"""

    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    vital_signs = VitalSignsSerializer(many=True, read_only=True)

    class Meta:
        model = RiskAssessment
        fields = [
            'id',
            'patient',
            'patient_name',
            'created_at',
            'assessed_at',
            'observation_count',
            'vital_signs',
            'news2_total',
            'news2_hr_score',
            'news2_rr_score',
            'news2_spo2_score',
            'news2_bp_score',
            'news2_temp_score',
            'trend_score',
            'trend_level',
            'trend_window_4',
            'trend_window_8',
            'trend_window_12',
            'multi_param_score',
            'multi_param_pattern',
            'multi_param_details',
            'combined_risk',
            'risk_level',
            'explanation_text',
            'recommendation',
            'decision_logic',
            'algorithm_version',
            'configuration_version',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'assessed_at',
            'patient_name',
            'vital_signs',
        ]


class RiskTimelineItemSerializer(serializers.Serializer):
    """Serialize a single point in risk timeline"""

    timestamp = serializers.DateTimeField()
    vital_id = serializers.IntegerField()
    news2_score = serializers.IntegerField()
    trend_score = serializers.IntegerField()
    combined_risk = serializers.FloatField()
    risk_level = serializers.CharField()
    vital_values = serializers.DictField()

    class Meta:
        fields = [
            'timestamp',
            'vital_id',
            'news2_score',
            'trend_score',
            'combined_risk',
            'risk_level',
            'vital_values',
        ]


class RiskTimelineSerializer(serializers.Serializer):
    """Serialize complete risk timeline for a patient"""

    patient_id = serializers.IntegerField()
    timeline = RiskTimelineItemSerializer(many=True)
    current_risk_level = serializers.CharField()
    current_combined_risk = serializers.FloatField()
    assessment_count = serializers.IntegerField()

    class Meta:
        fields = [
            'patient_id',
            'timeline',
            'current_risk_level',
            'current_combined_risk',
            'assessment_count',
        ]


class ExplainabilityResponseSerializer(serializers.Serializer):
    """Serialize detailed explainability response"""

    assessment_id = serializers.IntegerField()
    executive_summary = serializers.CharField()
    news2_explanation = serializers.CharField()
    trend_explanation = serializers.CharField()
    multi_param_explanation = serializers.CharField()
    contributing_factors = serializers.ListField(
        child=serializers.DictField()
    )
    clinical_context = serializers.CharField()
    recommendation = serializers.CharField()
    next_actions = serializers.ListField(
        child=serializers.CharField()
    )
    narrative = serializers.CharField()

    class Meta:
        fields = [
            'assessment_id',
            'executive_summary',
            'news2_explanation',
            'trend_explanation',
            'multi_param_explanation',
            'contributing_factors',
            'clinical_context',
            'recommendation',
            'next_actions',
            'narrative',
        ]
