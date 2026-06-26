from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from deterioration_alerts.models import DeteriorationAlert
from deterioration_alerts.serializers import DeteriorationAlertSerializer


class DeteriorationAlertViewSet(viewsets.ModelViewSet):
    """
    API endpoints for deterioration alerts.

    Think of this like a waiter in a restaurant:
    - Frontend asks "give me all alerts" → This returns them
    - Frontend asks "acknowledge this alert" → This marks it as seen
    - Frontend asks "predict this vital" → This makes a prediction
    """

    permission_classes = [IsAuthenticated]  # Only logged-in staff can access
    serializer_class = DeteriorationAlertSerializer
    queryset = DeteriorationAlert.objects.all()

    @action(detail=False, methods=['get'])
    def active_alerts(self, request):
        """
        GET /api/alerts/active_alerts/

        Returns: List of all unacknowledged alerts

        This is what the dashboard calls to show alerts to staff
        """
        alerts = DeteriorationAlert.objects.filter(
            status='active'
        ).order_by('-triggered_at')  # Newest first

        serializer = self.get_serializer(alerts, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def critical_alerts(self, request):
        """
        GET /api/alerts/critical_alerts/

        Returns: Only CRITICAL priority alerts

        This is for high-priority display (like red alerts)
        """
        alerts = DeteriorationAlert.objects.filter(
            priority='critical',
            status__in=['active', 'acknowledged']
        ).order_by('-triggered_at')

        serializer = self.get_serializer(alerts, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """
        POST /api/alerts/{id}/acknowledge/

        Staff clicks "acknowledge" on the dashboard → This marks the alert as seen
        """
        alert = self.get_object()
        alert.status = 'acknowledged'
        alert.acknowledged_by = request.user
        alert.acknowledged_at = timezone.now()
        alert.save()

        return Response({'status': 'acknowledged'})

    @action(detail=False, methods=['post'])
    def predict(self, request):
        """
        POST /api/alerts/predict/

        For testing: Send vital data and get a prediction back

        Example:
        POST /api/alerts/predict/
        {
            "vital_data": {
                "news2_total": 5,
                "rr_score": 1,
                ...
            }
        }

        Returns:
        {
            "is_critical": true,
            "probability": 0.75,
            "alert_level": "AMBER",
            "confidence": 75.0
        }
        """
        try:
            from deterioration_alerts.inference_service import get_detector
            vital_data = request.data.get('vital_data', {})
            detector = get_detector()
            prediction = detector.predict(vital_data)
            return Response(prediction)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
