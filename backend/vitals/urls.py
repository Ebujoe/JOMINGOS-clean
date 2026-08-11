from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .test_views import vitals_test_dashboard, vitals_api
from .api_views import (
    RiskAssessmentViewSet,
    VitalSignsViewSet,
    RiskTimelineView,
    PatientRiskSummaryView,
)
from .dashboard_views import (
    risk_dashboard,
    patient_risk_detail,
    alert_history,
    critical_patients_list,
    api_patient_risk_realtime,
    api_alert_stream,
    api_dashboard_summary,
)
from .real_time_views import RealTimeRecordingViewSet, FlowVisualizationView
from .api_predictive import (
    get_patient_prediction,
    get_cohort_predictions,
    get_prediction_details,
)
from .predictive_views import (
    predictive_dashboard,
    patient_predictive_detail,
    api_patient_predictive,
)

# DRF Router for API endpoints
router = DefaultRouter()
router.register(r'risk-assessments', RiskAssessmentViewSet, basename='risk-assessment')
router.register(r'vitals', VitalSignsViewSet, basename='vital-signs')
router.register(r'risk-timeline', RiskTimelineView, basename='risk-timeline')
router.register(r'patient-risk-summary', PatientRiskSummaryView, basename='patient-risk-summary')
router.register(r'real-time', RealTimeRecordingViewSet, basename='real-time-recording')

urlpatterns = [
    # Traditional views
    path('', views.vitals_list, name='vitals_list'),  # Global vitals dashboard
    path('test/', vitals_test_dashboard, name='vitals_test_dashboard'),  # Simple test dashboard
    path('api/', vitals_api, name='vitals_api'),  # JSON API
    path('<int:patient_pk>/add/', views.add_vitals, name='add_vitals'),
    path('<int:patient_pk>/', views.patient_vitals_list, name='patient_vitals_list'),
    path('<int:patient_pk>/history/', views.patient_vital_history, name='patient_vital_history'),  # Detailed history with predictions

    # Dashboard views (Phase 6)
    path('dashboard/', risk_dashboard, name='risk_dashboard'),
    path('patient/<int:patient_id>/risk/', patient_risk_detail, name='patient_risk_detail'),
    path('alerts/', alert_history, name='alert_history'),
    path('critical/', critical_patients_list, name='critical_patients'),

    # REST API endpoints (Phase 5)
    path('api/v1/', include(router.urls)),

    # Real-time API endpoints (Phase 6)
    path('api/patient/<int:patient_id>/risk-realtime/', api_patient_risk_realtime, name='api_patient_risk_realtime'),
    path('api/alert-stream/', api_alert_stream, name='api_alert_stream'),
    path('api/dashboard-summary/', api_dashboard_summary, name='api_dashboard_summary'),

    # Real-time recording endpoints (Phase 9)
    path('realtime-flow/', FlowVisualizationView.as_view(), name='realtime_flow'),

    # Predictive Forecasting endpoints (Phase 10)
    path('api/predict/patient/<int:patient_pk>/', get_patient_prediction, name='api_patient_prediction'),
    path('api/predict/cohort/', get_cohort_predictions, name='api_cohort_predictions'),
    path('api/predict/details/<int:prediction_id>/', get_prediction_details, name='api_prediction_details'),

    # Predictive Forecasting UI (Phase 10)
    path('predictive/', predictive_dashboard, name='predictive_dashboard'),
    path('<int:patient_pk>/predictive/', patient_predictive_detail, name='patient_predictive_detail'),
    path('api/patient/<int:patient_pk>/predictive/', api_patient_predictive, name='api_patient_predictive'),
]
