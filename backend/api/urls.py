from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.permissions import AllowAny
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from accounts.views_api import (
    RegisterView,
    LoginView,
    LogoutView,
    MeView,
    ChangePasswordView,
    ForgotPasswordView,
    ResetPasswordView,
    ProfileUpdateView,
)
from dashboard.views_api import DashboardStatsView, RoleDashboardView
from patients.views_api import PatientViewSet
from care_notes.views_api import CareNoteViewSet
from medications.views_api import MedicationViewSet
from vitals.views_api import VitalSignsViewSet
from deterioration_alerts.views_api import DeteriorationAlertViewSet

from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


router = DefaultRouter()
router.register(r"patients", PatientViewSet, basename="patient")
router.register(r"care-notes", CareNoteViewSet, basename="care-note")
router.register(r"medications", MedicationViewSet, basename="medication")
router.register(r"vitals", VitalSignsViewSet, basename="vitals")
router.register(r"alerts", DeteriorationAlertViewSet, basename="alert")


schema_view = get_schema_view(
    openapi.Info(
        title="Jomingos API",
        default_version="v1",
        description="REST API for the Jomingos care-home documentation platform.",
    ),
    public=True,
    permission_classes=[AllowAny],
)


urlpatterns = [
    path("", include(router.urls)),

    # Accounts / auth
    path("accounts/register/", RegisterView.as_view(), name="api-register"),
    path("accounts/login/", LoginView.as_view(), name="api-login"),
    path("accounts/logout/", LogoutView.as_view(), name="api-logout"),
    path("accounts/me/", MeView.as_view(), name="api-me"),
    path("accounts/profile/", ProfileUpdateView.as_view(), name="api-profile"),
    path("accounts/change-password/", ChangePasswordView.as_view(), name="api-change-password"),
    path("accounts/forgot-password/", ForgotPasswordView.as_view(), name="api-forgot-password"),
    path("accounts/reset-password/", ResetPasswordView.as_view(), name="api-reset-password"),

    # JWT helpers (optional)
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # Dashboard
    path("dashboard/stats/", DashboardStatsView.as_view(), name="api-dashboard-stats"),
    path("dashboard/<str:role>/", RoleDashboardView.as_view(), name="api-role-dashboard"),

    # API docs
    path("docs/swagger/", schema_view.with_ui("swagger", cache_timeout=0), name="swagger-ui"),
    path("docs/redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="redoc"),
]
