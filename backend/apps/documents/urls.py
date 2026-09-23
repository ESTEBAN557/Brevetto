from django.urls import path

from apps.documents.views import (
    DocumentDetailView,
    DocumentListCreateView,
    DocumentRegistrationView,
)

urlpatterns = [
    path("documents/", DocumentListCreateView.as_view(), name="document-list-create"),
    path("documents/register/", DocumentRegistrationView.as_view(), name="document-registration"),
    path("documents/<uuid:pk>/", DocumentDetailView.as_view(), name="document-detail"),
]
