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

# DRF Router for API endpoints
router = DefaultRouter()
router.register(r'risk-assessments', RiskAssessmentViewSet, basename='risk-assessment')
router.register(r'vitals', VitalSignsViewSet, basename='vital-signs')
router.register(r'risk-timeline', RiskTimelineView, basename='risk-timeline')
router.register(r'patient-risk-summary', PatientRiskSummaryView, basename='patient-risk-summary')

urlpatterns = [
    # Traditional views
    path('', views.vitals_list, name='vitals_list'),  # Global vitals dashboard
    path('test/', vitals_test_dashboard, name='vitals_test_dashboard'),  # Simple test dashboard
    path('api/', vitals_api, name='vitals_api'),  # JSON API
    path('<int:patient_pk>/add/', views.add_vitals, name='add_vitals'),
    path('<int:patient_pk>/', views.patient_vitals_list, name='patient_vitals_list'),
    path('<int:patient_pk>/history/', views.patient_vital_history, name='patient_vital_history'),  # Detailed history with predictions

    # REST API endpoints (Phase 5)
    path('api/v1/', include(router.urls)),
]
