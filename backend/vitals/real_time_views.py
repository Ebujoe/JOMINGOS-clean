"""
Phase 9: Real-time Views for Data Recording & Flow Visualization

Provides endpoints to record real-time data and view the flow.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import JsonResponse, HttpResponse
from django.views import View
from .real_time_recorder import RealTimeDataRecorder, FlowVisualizer
import json


class RealTimeRecordingViewSet(viewsets.ViewSet):
    """
    Real-time data recording API endpoint.

    POST /api/v1/real-time/record/
    Body: {
        "patient_id": 1,
        "heart_rate": 85,
        "respiratory_rate": 16,
        "oxygen_saturation": 97.0,
        "systolic_bp": 120,
        "diastolic_bp": 80,
        "temperature": 37.0
    }
    """

    @action(detail=False, methods=['post'])
    def record(self, request):
        """
        Record vital signs and get flow result.

        Returns:
            Complete flow data with all processing steps
        """
        try:
            patient_id = request.data.get('patient_id')
            if not patient_id:
                return Response(
                    {'error': 'patient_id required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            vitals = {
                'heart_rate': request.data.get('heart_rate'),
                'respiratory_rate': request.data.get('respiratory_rate'),
                'oxygen_saturation': request.data.get('oxygen_saturation'),
                'systolic_bp': request.data.get('systolic_bp'),
                'diastolic_bp': request.data.get('diastolic_bp'),
                'temperature': request.data.get('temperature'),
            }

            recorder = RealTimeDataRecorder(patient_id)
            result = recorder.record_vital_signs(vitals)

            return Response(result, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def flow(self, request):
        """
        Get current flow visualization.

        Parameters:
            patient_id: (required) Patient ID to get flow for
        """
        try:
            patient_id = request.query_params.get('patient_id')
            if not patient_id:
                return Response(
                    {'error': 'patient_id parameter required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            recorder = RealTimeDataRecorder(int(patient_id))
            flow_data = recorder.get_full_flow()

            return Response(flow_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Get summary of all recordings for a patient.

        Parameters:
            patient_id: (required) Patient ID to get summary for
        """
        try:
            patient_id = request.query_params.get('patient_id')
            if not patient_id:
                return Response(
                    {'error': 'patient_id parameter required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            recorder = RealTimeDataRecorder(int(patient_id))
            summary = recorder.get_summary()

            return Response(summary, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FlowVisualizationView(View):
    """
    HTML view for visualizing the data flow.

    GET /realtime-flow/?patient_id=1
    """

    def get(self, request):
        """Display flow visualization in HTML format."""
        patient_id = request.GET.get('patient_id')

        if not patient_id:
            return HttpResponse(
                '<h1>Error</h1><p>patient_id parameter required</p>',
                status=400
            )

        try:
            recorder = RealTimeDataRecorder(int(patient_id))
            flow_data = recorder.get_full_flow()
            summary = recorder.get_summary()

            diagram = FlowVisualizer.generate_flow_diagram(flow_data)
            summary_table = FlowVisualizer.generate_summary_table(summary)

            html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Real-time Flow Visualization</title>
    <style>
        body {{
            font-family: 'Courier New', monospace;
            background-color: #0d1117;
            color: #c9d1d9;
            margin: 20px;
            overflow-x: auto;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        h1 {{
            color: #58a6ff;
            border-bottom: 2px solid #30363d;
            padding-bottom: 10px;
        }}
        .flow-diagram {{
            background-color: #161b22;
            border: 1px solid #30363d;
            padding: 20px;
            margin: 20px 0;
            border-radius: 6px;
            white-space: pre-wrap;
            overflow-x: auto;
        }}
        .summary-table {{
            background-color: #161b22;
            border: 1px solid #30363d;
            padding: 20px;
            margin: 20px 0;
            border-radius: 6px;
            white-space: pre;
            overflow-x: auto;
        }}
        .info {{
            background-color: #0d3922;
            border-left: 4px solid #238636;
            padding: 10px;
            margin: 10px 0;
            border-radius: 4px;
        }}
        .alert {{
            background-color: #3d2621;
            border-left: 4px solid #da3633;
            padding: 10px;
            margin: 10px 0;
            border-radius: 4px;
        }}
        .button {{
            background-color: #238636;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            margin: 5px;
            font-size: 14px;
        }}
        .button:hover {{
            background-color: #2ea043;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Real-time Deterioration Detection Flow</h1>

        <div class="info">
            <strong>Patient ID:</strong> {patient_id}<br>
            <strong>Total Recordings:</strong> {summary.get('total_recordings', 0)}<br>
            <strong>Alerts Generated:</strong> {summary.get('alerts_generated', 0)}<br>
            <strong>Total Time:</strong> {summary.get('total_time_seconds', 0):.1f} seconds
        </div>

        <h2>Data Flow Sequence</h2>
        <div class="flow-diagram">{diagram}</div>

        <h2>Recording Summary Table</h2>
        <div class="summary-table">{summary_table}</div>

        <h2>How to Test This System</h2>
        <div class="info">
            <p><strong>Step 1: Record First Data Point</strong></p>
            <pre>curl -X POST http://localhost:8000/api/v1/real-time/record/ \
  -H "Content-Type: application/json" \
  -d '{{
    "patient_id": 1,
    "heart_rate": 75,
    "respiratory_rate": 16,
    "oxygen_saturation": 98.0,
    "systolic_bp": 120,
    "diastolic_bp": 80,
    "temperature": 37.0
  }}'</pre>
        </div>

        <div class="info">
            <p><strong>Step 2: Record More Data Points to Show Deterioration</strong></p>
            <pre>curl -X POST http://localhost:8000/api/v1/real-time/record/ \
  -H "Content-Type: application/json" \
  -d '{{
    "patient_id": 1,
    "heart_rate": 95,
    "respiratory_rate": 22,
    "oxygen_saturation": 94.0,
    "systolic_bp": 110,
    "diastolic_bp": 75,
    "temperature": 38.5
  }}'</pre>
        </div>

        <div class="alert">
            <p><strong>Step 3: Refresh This Page to See Updated Flow</strong></p>
            <p>Each new recording will appear in the sequence above, showing how the system processes the data.</p>
        </div>

        <h2>Understanding the Output</h2>
        <div class="info">
            <p><strong>What You're Seeing:</strong></p>
            <ul>
                <li><strong>Sequence #:</strong> Order of recordings (1st, 2nd, 3rd data point)</li>
                <li><strong>STEP 1 (VITALS RECEIVED):</strong> Raw vital signs from sensor</li>
                <li><strong>STEP 2 (STORED IN DATABASE):</strong> Data persisted to database</li>
                <li><strong>STEP 3 (RISK ASSESSMENT):</strong> Clinical scoring calculated</li>
                <li><strong>STEP 4 (RISK RECORD CREATED):</strong> Risk assessment saved</li>
                <li><strong>STEP 5 (DECISION LOGIC):</strong> Alert decision made</li>
                <li><strong>STEP 6 (FINAL DECISION):</strong> ALERT or NORMAL</li>
            </ul>
        </div>

        <h2>Example Test Scenario</h2>
        <div class="info">
            <p><strong>Panel Demo Sequence:</strong></p>
            <ol>
                <li><strong>First Data:</strong> Normal vitals (HR 75, SpO2 98%) → NORMAL</li>
                <li><strong>Second Data:</strong> Slight elevation (HR 85, SpO2 96%) → NORMAL</li>
                <li><strong>Third Data:</strong> Deterioration (HR 110, SpO2 92%) → ALERT</li>
                <li><strong>Fourth Data:</strong> Critical (HR 120, SpO2 88%) → ALERT (CRITICAL)</li>
            </ol>
            <p>The flow visualization will show each step of the system's decision-making process.</p>
        </div>

        <div style="margin-top: 40px; border-top: 1px solid #30363d; padding-top: 20px;">
            <p style="color: #8b949e; font-size: 12px;">
                System automatically updates in real-time. Refresh this page after recording new data points.
            </p>
        </div>
    </div>
</body>
</html>
            """
            return HttpResponse(html)

        except Exception as e:
            return HttpResponse(f'<h1>Error</h1><p>{str(e)}</p>', status=500)
