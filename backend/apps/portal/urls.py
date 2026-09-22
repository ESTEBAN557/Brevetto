from django.urls import path

from apps.portal.views import SubmitDocumentView, VerifyContractView

urlpatterns = [
    path("portal/verify-contract/", VerifyContractView.as_view(), name="portal-verify-contract"),
    path("portal/submit-document/", SubmitDocumentView.as_view(), name="portal-submit-document"),
]
