from django.urls import path
from . import views
from .test_views import vitals_test_dashboard, vitals_api

urlpatterns = [
    path('', views.vitals_list, name='vitals_list'),  # Global vitals dashboard
    path('test/', vitals_test_dashboard, name='vitals_test_dashboard'),  # Simple test dashboard
    path('api/', vitals_api, name='vitals_api'),  # JSON API
    path('<int:patient_pk>/add/', views.add_vitals, name='add_vitals'),
    path('<int:patient_pk>/', views.patient_vitals_list, name='patient_vitals_list'),
    path('<int:patient_pk>/history/', views.patient_vital_history, name='patient_vital_history'),  # Detailed history with predictions
]
