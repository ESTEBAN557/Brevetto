"""Rutas del módulo de documentos."""
from django.urls import path

from apps.documents.views import (
    DocumentRegistrationView,
    DocumentListCreateView,
    DocumentDetailView,
)

urlpatterns = [
    # US-004: registro formal de documento
    path("documents/register/", DocumentRegistrationView.as_view(), name="document-registration"),

    # Otra HU: listar / crear y ver detalle
    path("documents/", DocumentListCreateView.as_view(), name="document-list-create"),
    path("documents/<uuid:pk>/", DocumentDetailView.as_view(), name="document-detail"),
]
