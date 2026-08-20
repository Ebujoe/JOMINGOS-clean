from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="Jomingos API",
        default_version='v1',
        description="Healthcare Home Documentation Platform API - Complete REST API for patient records, care notes, medications, vitals, and staff management.",
        terms_of_service="https://www.jomingos.local/terms/",
        contact=openapi.Contact(email="support@jomingos.local"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # Swagger API Documentation
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('api/schema/', schema_view.without_ui(cache_timeout=0), name='schema-json'),

    # API endpoints
    path('api/', include('api.urls')),
    path('', include('dashboard.urls')),
    path('accounts/', include('accounts.urls')),
    path('patients/', include('patients.urls')),
    path('tasks/', include('tasks.urls')),
    path('care-notes/', include('care_notes.urls')),
    path('medications/', include('medications.urls')),
    path('vitals/', include('vitals.urls')),
    path('family/', include('family.urls')),
    path('ml-risk/', include('risk_classifier.urls')), # added by priyaraj
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
