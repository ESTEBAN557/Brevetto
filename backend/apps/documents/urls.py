from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.documents.views import AuditLogViewSet, DocumentViewSet, MetricsSummaryView

router = DefaultRouter()
router.register("documents", DocumentViewSet, basename="document")
router.register("audit", AuditLogViewSet, basename="audit")

urlpatterns = [
    path("metrics/summary/", MetricsSummaryView.as_view(), name="metrics-summary"),
    *router.urls,
]
