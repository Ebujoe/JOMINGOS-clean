from django.urls import path
from . import views

urlpatterns = [
    path('<int:patient_pk>/', views.live_alert_form, name='live_alert_form'),
    path('<int:patient_pk>/log/', views.live_alert_log, name='live_alert_log'),
    path('<int:patient_pk>/<int:alert_pk>/acknowledge/', views.acknowledge_alert, name='acknowledge_alert'),
    path('<int:patient_pk>/<int:alert_pk>/delete/', views.delete_alert, name='delete_alert'),
]