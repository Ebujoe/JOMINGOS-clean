"""
Django REST API Views for Vitals & Risk Assessments

Endpoints:
- GET /api/v1/patient/{patient_id}/risk-assessments/ - List all assessments
- GET /api/v1/patient/{patient_id}/risk-assessment/{assessment_id}/ - Assessment details
- GET /api/v1/patient/{patient_id}/risk-timeline/ - Risk progression timeline
- GET /api/v1/risk-assessment/{assessment_id}/explain/ - Detailed explainability
- GET /api/v1/vital/{vital_id}/contribution/ - How vital contributed to risk
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q

from vitals.models import VitalSigns, RiskAssessment
from vitals.serializers import (
    VitalSignsSerializer,
    RiskAssessmentSerializer,
    RiskTimelineSerializer,
    ExplainabilityResponseSerializer,
)
from vitals.utils.explainability import ExplainabilityEngine
from patients.models import Patient


class RiskAssessmentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for risk assessments.

    Provides read-only access to risk assessments with explainability.
    """

    queryset = RiskAssessment.objects.all().order_by('-assessed_at')
    serializer_class = RiskAssessmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter by patient if provided"""
        queryset = RiskAssessment.objects.all()

        # Filter by patient if patient_id in query params
        patient_id = self.request.query_params.get('patient_id')
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)

        return queryset.order_by('-assessed_at')

    @action(detail=True, methods=['get'])
    def explain(self, request, pk=None):
        """
        GET /api/v1/risk-assessment/{id}/explain/

        Returns detailed explainability for this assessment.
        """
        assessment = self.get_object()
        engine = ExplainabilityEngine()

        explanation = engine.explain_assessment(assessment)
        narrative = engine.generate_assessment_narrative(assessment)

        return Response({
            'assessment_id': assessment.id,
            'executive_summary': explanation['executive_summary'],
            'news2_explanation': explanation['news2_explanation'],
            'trend_explanation': explanation['trend_explanation'],
            'multi_param_explanation': explanation['multi_param_explanation'],
            'contributing_factors': explanation['contributing_factors'],
            'clinical_context': explanation['clinical_context'],
            'recommendation': explanation['recommendation'],
            'next_actions': explanation['next_actions'],
            'narrative': narrative,
        })

    @action(detail=False, methods=['get'])
    def by_patient(self, request):
        """
        GET /api/v1/risk-assessment/by_patient/?patient_id=123

        Returns all assessments for a patient.
        """
        patient_id = request.query_params.get('patient_id')
        if not patient_id:
            return Response(
                {'error': 'patient_id query parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        patient = get_object_or_404(Patient, id=patient_id)
        assessments = RiskAssessment.objects.filter(
            patient=patient
        ).order_by('-assessed_at')[:50]

        serializer = self.get_serializer(assessments, many=True)
        return Response({
            'patient_id': patient.id,
            'patient_name': patient.get_full_name(),
            'assessment_count': assessments.count(),
            'assessments': serializer.data,
        })


class VitalSignsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for vital signs.

    Provides read-only access to vital signs with NEWS2 scores.
    """

    queryset = VitalSigns.objects.all().order_by('-recorded_at')
    serializer_class = VitalSignsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter by patient if provided"""
        queryset = VitalSigns.objects.all()

        patient_id = self.request.query_params.get('patient_id')
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)

        return queryset.order_by('-recorded_at')

    @action(detail=True, methods=['get'])
    def contribution(self, request, pk=None):
        """
        GET /api/v1/vital/{id}/contribution/

        Returns how this vital contributed to its risk assessment.
        """
        vital = self.get_object()

        # Find the risk assessment that includes this vital
        assessment = RiskAssessment.objects.filter(
            vital_signs=vital
        ).order_by('-assessed_at').first()

        if not assessment:
            return Response(
                {'error': 'No risk assessment found for this vital'},
                status=status.HTTP_404_NOT_FOUND
            )

        engine = ExplainabilityEngine()
        contributions = engine.explain_vital_contribution(vital, assessment)

        return Response({
            'vital_id': vital.id,
            'vital_recorded_at': vital.recorded_at,
            'assessment_id': assessment.id,
            'risk_level': assessment.risk_level,
            'combined_risk': assessment.combined_risk,
            'vital_contributions': contributions,
        })


class RiskTimelineView(viewsets.ViewSet):
    """
    API endpoint for risk timeline.

    Returns the progression of risk over time for a patient.
    """

    permission_classes = [IsAuthenticated]

    def list(self, request):
        """
        GET /api/v1/risk-timeline/?patient_id=123

        Returns risk timeline for a patient.
        """
        patient_id = request.query_params.get('patient_id')
        if not patient_id:
            return Response(
                {'error': 'patient_id query parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        patient = get_object_or_404(Patient, id=patient_id)

        # Get all assessments for this patient
        assessments = RiskAssessment.objects.filter(
            patient=patient
        ).order_by('assessed_at')

        # Build timeline
        timeline = []
        for assessment in assessments:
            # Get latest vital for this assessment
            vital = assessment.vital_signs.latest('recorded_at')

            timeline.append({
                'timestamp': assessment.assessed_at,
                'vital_id': vital.id,
                'news2_score': assessment.news2_total,
                'trend_score': assessment.trend_score,
                'combined_risk': assessment.combined_risk,
                'risk_level': assessment.risk_level,
                'vital_values': {
                    'heart_rate': vital.heart_rate,
                    'respiratory_rate': vital.respiratory_rate,
                    'oxygen_saturation': float(vital.oxygen_saturation) if vital.oxygen_saturation else None,
                    'bp_systolic': vital.bp_systolic,
                    'temperature': float(vital.temperature) if vital.temperature else None,
                },
            })

        # Get current status
        latest_assessment = assessments.last()

        return Response({
            'patient_id': patient.id,
            'patient_name': patient.get_full_name(),
            'timeline': timeline,
            'current_risk_level': latest_assessment.risk_level if latest_assessment else 'unknown',
            'current_combined_risk': latest_assessment.combined_risk if latest_assessment else 0,
            'assessment_count': assessments.count(),
        })


class PatientRiskSummaryView(viewsets.ViewSet):
    """
    API endpoint for patient risk summary.

    Returns current risk status and recent history.
    """

    permission_classes = [IsAuthenticated]

    def list(self, request):
        """
        GET /api/v1/patient/{patient_id}/risk-summary/

        Returns current risk status and recent history.
        """
        patient_id = request.query_params.get('patient_id')
        if not patient_id:
            return Response(
                {'error': 'patient_id query parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        patient = get_object_or_404(Patient, id=patient_id)

        # Get latest assessment
        latest_assessment = RiskAssessment.objects.filter(
            patient=patient
        ).order_by('-assessed_at').first()

        if not latest_assessment:
            return Response({
                'patient_id': patient.id,
                'patient_name': patient.get_full_name(),
                'status': 'no_assessments',
                'message': 'No risk assessments available yet',
            })

        # Get recent assessments (last 5)
        recent_assessments = RiskAssessment.objects.filter(
            patient=patient
        ).order_by('-assessed_at')[:5]

        # Generate explanations
        engine = ExplainabilityEngine()
        latest_explanation = engine.explain_assessment(latest_assessment)

        return Response({
            'patient_id': patient.id,
            'patient_name': patient.get_full_name(),
            'current_status': {
                'risk_level': latest_assessment.risk_level,
                'combined_risk': latest_assessment.combined_risk,
                'assessed_at': latest_assessment.assessed_at,
                'executive_summary': latest_explanation['executive_summary'],
                'recommendation': latest_explanation['recommendation'],
            },
            'contributing_factors': latest_explanation['contributing_factors'],
            'next_actions': latest_explanation['next_actions'],
            'recent_history': [
                {
                    'assessed_at': a.assessed_at,
                    'risk_level': a.risk_level,
                    'combined_risk': a.combined_risk,
                    'news2_score': a.news2_total,
                }
                for a in recent_assessments
            ],
        })
