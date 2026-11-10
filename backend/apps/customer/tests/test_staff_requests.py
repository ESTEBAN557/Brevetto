"""Pruebas de la atención de requerimientos por el personal (/api/v1/service-requests/, JWT)."""

from __future__ import annotations

import pytest
from django.core import mail
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.customer.models import ServiceRequest, ServiceRequestMessage
from apps.customer.services import create_service_request

BASE = "/api/v1/service-requests/"


@pytest.fixture(autouse=True)
def reset_state(settings):
    cache.clear()
    settings.CLIENT_OTP_DEV_ECHO = True
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    yield
    cache.clear()


@pytest.fixture
def service_request(tenant, contract):
    return create_service_request(
        client=tenant,
        contract=contract,
        catalog_id=5,  # Documental · Actualización de pólizas o documentos vencidos
        subject="Necesito actualizar la póliza de cumplimiento",
        description="La póliza vence el próximo mes y quiero enviarles la renovación.",
        files=[],
    )


@pytest.fixture
def staff_user(user):
    user.first_name, user.last_name = "Laura", "Restrepo"
    user.save()
    return user


def detail_url(service_request, suffix=""):
    return f"{BASE}{service_request.pk}/{suffix}"


@pytest.mark.django_db
class TestStaffInbox:
    def test_lists_requests_with_client_and_counters(self, api_client, service_request):
        body = api_client.get(BASE).json()
        assert body["count"] == 1
        item = body["results"][0]
        assert item["client_name"] == "Logística Andina S.A.S."
        assert item["contract_number"] == "CONT-2026-042"
        assert item["status"] == "NUEVO" and item["message_count"] == 0

    def test_filters_by_status_and_search(self, api_client, service_request):
        assert api_client.get(BASE, {"status": "CERRADO"}).json()["count"] == 0
        assert api_client.get(BASE, {"status": "NUEVO,ASIGNADO"}).json()["count"] == 1
        assert api_client.get(BASE, {"q": "póliza"}).json()["count"] == 1
        assert api_client.get(BASE, {"q": f"#{service_request.pk}"}).json()["count"] == 1
        assert api_client.get(BASE, {"q": "no-existe"}).json()["count"] == 0

    def test_summary_counts_open_requests(self, api_client, service_request):
        body = api_client.get(f"{BASE}summary/").json()
        assert body["total"] == 1 and body["open"] == 1
        assert {s["code"]: s["count"] for s in body["by_status"]}["NUEVO"] == 1

    def test_requires_staff_jwt(self, anonymous_client, service_request):
        assert anonymous_client.get(BASE).status_code == 401
        client_session = APIClient()
        client_session.credentials(HTTP_AUTHORIZATION="Client cualquier-token")
        assert client_session.get(BASE).status_code == 401


@pytest.mark.django_db
class TestStaffManagement:
    def test_assigning_a_new_request_moves_it_to_assigned(self, staff_user, service_request):
        api = APIClient()
        api.force_authenticate(staff_user)
        body = api.patch(detail_url(service_request), {"assigned_to": "Laura Restrepo"}, format="json").json()
        assert body["status"] == "ASIGNADO" and body["assigned_to"] == "Laura Restrepo"
        last_event = body["events"][-1]
        assert last_event["status"] == "ASIGNADO" and last_event["actor"] == "Laura Restrepo"
        assert "ASIGNADO" in mail.outbox[-1].subject.upper() or "Asignado" in mail.outbox[-1].subject

    def test_status_change_is_traced_and_notifies_the_client(self, api_client, service_request):
        response = api_client.patch(
            detail_url(service_request),
            {"status": "EN_PROCESO", "note": "Revisando con jurídica"},
            format="json",
        )
        assert response.status_code == 200
        assert [e["status"] for e in response.json()["events"]] == ["NUEVO", "EN_PROCESO"]
        assert response.json()["events"][-1]["note"] == "Revisando con jurídica"
        assert mail.outbox[-1].to == ["contacto@logandina.co"]

    def test_resolving_requires_a_solution(self, api_client, service_request):
        rejected = api_client.patch(detail_url(service_request), {"status": "RESUELTO"}, format="json")
        assert rejected.status_code == 400 and "solution" in rejected.json()
        service_request.refresh_from_db()
        assert service_request.status == "NUEVO"

        accepted = api_client.patch(
            detail_url(service_request),
            {"status": "RESUELTO", "solution": "Se recibió la póliza renovada y se archivó."},
            format="json",
        )
        assert accepted.status_code == 200 and accepted.json()["status"] == "RESUELTO"
        assert "póliza renovada" in mail.outbox[-1].body

    def test_closed_request_rejects_changes_messages_and_attachments(
        self, api_client, service_request, pdf_factory
    ):
        api_client.patch(
            detail_url(service_request), {"status": "CERRADO", "solution": "Atendido."}, format="json"
        )
        assert (
            api_client.patch(detail_url(service_request), {"status": "EN_PROCESO"}, format="json").status_code
            == 409
        )
        assert (
            api_client.post(
                detail_url(service_request, "messages/"), {"body": "Hola"}, format="json"
            ).status_code
            == 409
        )
        assert (
            api_client.post(
                detail_url(service_request, "attachments/"), {"files": [pdf_factory()]}, format="multipart"
            ).status_code
            == 409
        )

    def test_empty_update_is_rejected(self, api_client, service_request):
        assert api_client.patch(detail_url(service_request), {}, format="json").status_code == 400

    def test_unknown_request_returns_404(self, api_client):
        assert api_client.get(f"{BASE}999999/").status_code == 404


@pytest.mark.django_db
class TestStaffChatAndAttachments:
    def test_staff_reply_is_visible_to_the_client_and_emailed(self, staff_user, service_request):
        api = APIClient()
        api.force_authenticate(staff_user)
        response = api.post(
            detail_url(service_request, "messages/"), {"body": "Recibido, ya lo revisamos."}, format="json"
        )
        assert response.status_code == 201
        message = ServiceRequestMessage.objects.get(request=service_request)
        assert message.author_type == ServiceRequestMessage.Author.STAFF
        assert message.author_name == "Laura Restrepo"
        assert "Recibido, ya lo revisamos." in mail.outbox[-1].body

    def test_blank_message_is_rejected(self, api_client, service_request):
        assert (
            api_client.post(detail_url(service_request, "messages/"), {"body": ""}, format="json").status_code
            == 400
        )

    def test_staff_attachment_upload_and_download(self, api_client, service_request, pdf_factory):
        bad = api_client.post(
            detail_url(service_request, "attachments/"),
            {"files": [pdf_factory("script.exe")]},
            format="multipart",
        )
        assert bad.status_code == 400
        ok = api_client.post(
            detail_url(service_request, "attachments/"),
            {"files": [pdf_factory("respuesta.pdf")]},
            format="multipart",
        )
        assert ok.status_code == 201 and ok.json()[0]["from_client"] is False
        attachment_id = ok.json()[0]["id"]
        download = api_client.get(detail_url(service_request, f"attachments/{attachment_id}/download/"))
        assert download.status_code == 200 and download.json()["original_filename"] == "respuesta.pdf"

    def test_detail_exposes_client_contact_for_the_staff(self, api_client, service_request):
        body = api_client.get(detail_url(service_request)).json()
        assert body["client_email"] == "contacto@logandina.co"
        assert body["client_identification"] == "900123456-1"
        assert body["description"].startswith("La póliza vence")


@pytest.mark.django_db
def test_closing_from_staff_api_is_seen_by_client(api_client, service_request):
    api_client.patch(detail_url(service_request), {"status": "CERRADO", "solution": "Listo."}, format="json")
    assert ServiceRequest.objects.get(pk=service_request.pk).is_closed
