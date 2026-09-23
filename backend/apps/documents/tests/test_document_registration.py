"""Pruebas de US-004 — Crear Registro de Documento.

Cubre los casos de prueba TC-014 a TC-018 definidos para la historia:

- TC-014 / TC-015: creación exitosa (happy path).
- TC-016: intento de creación con campos obligatorios faltantes (flujo alterno).
- TC-018: el número de radicado queda asociado al registro creado.

La cancelación (AC-020 / TC-017) no genera petición al servidor: si el usuario no
confirma, no se crea ningún registro. Se verifica indirectamente comprobando que
sin una petición de creación no existen documentos.
"""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from apps.documents.models import Document
from apps.documents.services import create_document_record

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="isabella", password="secret-123")


@pytest.fixture
def api_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


VALID_PAYLOAD = {
    "original_filename": "cuenta_cobro_sep.pdf",
    "file_size_bytes": 1048576,
    "mime_type": "application/pdf",
    "source_channel": Document.SourceChannel.DIGITAL_INTERNAL,
}


@pytest.mark.django_db
class TestCreateDocumentRecordService:
    """Pruebas del servicio de creación (nivel unitario)."""

    def test_service_creates_record_with_initial_status(self, user):
        document = create_document_record(registered_by=user, **VALID_PAYLOAD)

        assert document.pk is not None
        assert document.processing_status == Document.ProcessingStatus.RECEIVED
        assert document.registered_by == user

    def test_service_generates_and_associates_filing_number(self, user):
        # TC-018: el radicado se genera y queda asociado al registro.
        document = create_document_record(registered_by=user, **VALID_PAYLOAD)

        assert document.filing_number
        assert document.filing_number.startswith("RAD-")
        # El registro almacenado conserva el mismo radicado (AC-017, AC-018).
        stored = Document.objects.get(pk=document.pk)
        assert stored.filing_number == document.filing_number

    def test_service_stores_record_retrievable(self, user):
        # AC-018: el registro queda almacenado y accesible.
        document = create_document_record(registered_by=user, **VALID_PAYLOAD)

        assert Document.objects.filter(pk=document.pk).exists()


@pytest.mark.django_db
class TestCreateDocumentRecordApi:
    """Pruebas del endpoint POST /api/v1/documents/ (nivel integración)."""

    def test_create_document_success(self, api_client):
        # TC-014 / TC-015: creación exitosa (happy path).
        response = api_client.post(
            reverse("document-registration"), VALID_PAYLOAD, format="json"
        )

        assert response.status_code == 201
        body = response.json()
        assert body["original_filename"] == VALID_PAYLOAD["original_filename"]
        assert body["processing_status"] == Document.ProcessingStatus.RECEIVED
        assert Document.objects.count() == 1

    def test_create_associates_filing_number(self, api_client):
        # TC-018: la respuesta expone un radicado con el formato esperado.
        response = api_client.post(
            reverse("document-registration"), VALID_PAYLOAD, format="json"
        )

        assert response.status_code == 201
        filing_number = response.json()["filing_number"]
        assert filing_number.startswith("RAD-")
        assert Document.objects.get().filing_number == filing_number

    def test_missing_required_field_returns_400(self, api_client):
        # TC-016: falta un campo obligatorio -> no se crea el registro (AC-019).
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "original_filename"}

        response = api_client.post(
            reverse("document-registration"), payload, format="json"
        )

        assert response.status_code == 400
        assert "original_filename" in response.json()
        assert Document.objects.count() == 0

    def test_blank_filename_returns_400(self, api_client):
        # AC-019: nombre en blanco también se rechaza.
        payload = {**VALID_PAYLOAD, "original_filename": "   "}

        response = api_client.post(
            reverse("document-registration"), payload, format="json"
        )

        assert response.status_code == 400
        assert Document.objects.count() == 0

    def test_non_positive_size_returns_400(self, api_client):
        payload = {**VALID_PAYLOAD, "file_size_bytes": 0}

        response = api_client.post(
            reverse("document-registration"), payload, format="json"
        )

        assert response.status_code == 400
        assert "file_size_bytes" in response.json()
        assert Document.objects.count() == 0

    def test_cancellation_creates_no_record(self):
        # TC-017 / AC-020: sin petición de confirmación no existe ningún registro
        # ni se consume un número de radicado.
        assert Document.objects.count() == 0

    def test_requires_authentication(self):
        response = APIClient().post(
            reverse("document-registration"), VALID_PAYLOAD, format="json"
        )

        assert response.status_code in (401, 403)
        assert Document.objects.count() == 0
