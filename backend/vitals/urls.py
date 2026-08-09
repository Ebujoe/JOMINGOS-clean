from django.urls import path
from . import views

urlpatterns = [
    path('', views.vitals_list, name='vitals_list'),  # Global vitals dashboard
    path('<int:patient_pk>/add/', views.add_vitals, name='add_vitals'),
    path('<int:patient_pk>/', views.patient_vitals_list, name='patient_vitals_list'),
    path('<int:patient_pk>/history/', views.patient_vital_history, name='patient_vital_history'),  # Detailed history with predictions
]
