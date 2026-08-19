"""
Django Views for Fall Detection System

Handles:
- Real-time video streaming from webcam
- Fall detection processing
- JSON API for frontend
- Explainable alerts
"""

import cv2
import json
import base64
import logging
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from vitals.fall_detection import FallDetectionSystem

logger = logging.getLogger(__name__)

# Global fall detection system
fall_detection = FallDetectionSystem()
current_fall_status = {
    'posture': 'unknown',
    'risk_score': 0,
    'risk_level': 'UNKNOWN',
    'explanation': '',
    'active': False
}


@api_view(['POST'])
@csrf_exempt
def process_fall_detection_frame(request):
    """
    Process single frame for fall detection.

    Expects:
    {
        'image_base64': base64 encoded image,
        'patient_id': patient ID (optional)
    }

    Returns:
    {
        'posture': str,
        'risk_score': float,
        'risk_level': str,
        'explanation': str,
        'timestamp': datetime
    }
    """
    try:
        data = json.loads(request.body)
        image_base64 = data.get('image_base64')
        patient_id = data.get('patient_id')

        if not image_base64:
            return JsonResponse({'error': 'No image provided'}, status=400)

        # Decode base64 image
        image_data = base64.b64decode(image_base64)
        nparr = np.frombuffer(image_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            return JsonResponse({'error': 'Invalid image'}, status=400)

        # Process frame
        result = fall_detection.process_frame(frame)

        # Update global status
        current_fall_status.update(result)

        return JsonResponse({
            'posture': result['posture'],
            'risk_score': result['risk_score'],
            'risk_level': result['risk_level'],
            'explanation': result['explanation'],
            'success': result['success'],
            'patient_id': patient_id
        })

    except Exception as e:
        logger.error(f"Fall detection error: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@api_view(['GET'])
def get_fall_status(request):
    """Get current fall detection status."""
    return JsonResponse({
        'posture': current_fall_status['posture'],
        'risk_score': current_fall_status['risk_score'],
        'risk_level': current_fall_status['risk_level'],
        'explanation': current_fall_status['explanation'],
        'active': current_fall_status['active']
    })


@api_view(['POST'])
def activate_fall_detection(request, patient_id):
    """Activate fall detection for patient."""
    current_fall_status['active'] = True
    logger.info(f"Fall detection activated for patient {patient_id}")
    return JsonResponse({'status': 'activated', 'patient_id': patient_id})


@api_view(['POST'])
def deactivate_fall_detection(request, patient_id):
    """Deactivate fall detection for patient."""
    current_fall_status['active'] = False
    logger.info(f"Fall detection deactivated for patient {patient_id}")
    return JsonResponse({'status': 'deactivated', 'patient_id': patient_id})
