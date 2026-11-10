from django.urls import path

from apps.customer import staff_views, views

urlpatterns = [
    # Atención de requerimientos por el personal (JWT)
    path("service-requests/", staff_views.StaffRequestListView.as_view(), name="staff-requests"),
    path(
        "service-requests/summary/",
        staff_views.StaffRequestSummaryView.as_view(),
        name="staff-requests-summary",
    ),
    path(
        "service-requests/<int:pk>/",
        staff_views.StaffRequestDetailView.as_view(),
        name="staff-request-detail",
    ),
    path(
        "service-requests/<int:pk>/messages/",
        staff_views.StaffRequestMessageView.as_view(),
        name="staff-request-messages",
    ),
    path(
        "service-requests/<int:pk>/attachments/",
        staff_views.StaffRequestAttachmentView.as_view(),
        name="staff-request-attachments",
    ),
    path(
        "service-requests/<int:pk>/attachments/<int:attachment_id>/download/",
        staff_views.StaffRequestAttachmentDownloadView.as_view(),
        name="staff-request-attachment-download",
    ),
    # Mi Portal (sesión de cliente)
    path("client-portal/auth/request-code/", views.RequestCodeView.as_view(), name="client-request-code"),
    path("client-portal/auth/verify-code/", views.VerifyCodeView.as_view(), name="client-verify-code"),
    path("client-portal/auth/login/", views.PasswordLoginView.as_view(), name="client-login"),
    path("client-portal/auth/set-password/", views.SetPasswordView.as_view(), name="client-set-password"),
    path("client-portal/me/", views.MeView.as_view(), name="client-me"),
    path("client-portal/home/", views.HomeView.as_view(), name="client-home"),
    path("client-portal/documents/", views.DocumentListView.as_view(), name="client-documents"),
    path(
        "client-portal/documents/options/",
        views.DocumentOptionsView.as_view(),
        name="client-document-options",
    ),
    path(
        "client-portal/documents/<uuid:pk>/download/",
        views.DocumentDownloadView.as_view(),
        name="client-document-download",
    ),
    path("client-portal/request-catalog/", views.CatalogView.as_view(), name="client-request-catalog"),
    path("client-portal/requests/", views.ServiceRequestListCreateView.as_view(), name="client-requests"),
    path(
        "client-portal/requests/<int:pk>/",
        views.ServiceRequestDetailView.as_view(),
        name="client-request-detail",
    ),
    path(
        "client-portal/requests/<int:pk>/messages/",
        views.ServiceRequestMessageView.as_view(),
        name="client-request-messages",
    ),
    path(
        "client-portal/requests/<int:pk>/attachments/",
        views.ServiceRequestAttachmentView.as_view(),
        name="client-request-attachments",
    ),
    path(
        "client-portal/requests/<int:pk>/attachments/<int:attachment_id>/download/",
        views.ServiceRequestAttachmentDownloadView.as_view(),
        name="client-request-attachment-download",
    ),
]
