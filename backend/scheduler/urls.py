from django.urls import path
from . import views

urlpatterns = [
    path(
        "",
        views.scheduler_dashboard,
        name="scheduler_dashboard"
    ),
]