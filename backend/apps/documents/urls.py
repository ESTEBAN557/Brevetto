"""Rutas del módulo de documentos."""
from django.urls import path

from apps.documents.views import DocumentRegistrationView

urlpatterns = [
    path(
        "documents/",
        DocumentRegistrationView.as_view(),
        name="document-registration",
    ),
]
