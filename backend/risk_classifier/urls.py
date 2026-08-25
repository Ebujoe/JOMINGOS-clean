from django.urls import path
from . import views

urlpatterns = [
    path("predict/<int:patient_id>/", views.get_ml_risk_prediction, name="ml_risk_prediction"),
    path("check/", views.vitals_check_view, name="vitals_check"),
]