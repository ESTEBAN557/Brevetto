"""Enrutamiento raíz de Brevetto. Todos los endpoints REST viven bajo /api/v1/."""

from django.conf import settings
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.core.auth import StaffTokenObtainPairView


def health_check(_request):
    """Endpoint liviano para healthchecks de Docker / balanceadores."""
    return JsonResponse({"status": "ok", "service": "brevetto-backend"})


urlpatterns = [
    path(settings.DJANGO_ADMIN_URL, admin.site.urls),
    path("api/v1/health/", health_check, name="health-check"),
    path("api/v1/auth/token/", StaffTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/v1/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/v1/", include("apps.documents.urls")),
    path("api/v1/", include("apps.core.urls")),
    path("api/v1/", include("apps.portal.urls")),
    path("api/v1/", include("apps.customer.urls")),
]
