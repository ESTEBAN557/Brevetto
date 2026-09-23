from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework.test import APIClient

from apps.documents.models import Document, FilingSequence

DOCUMENTS_URL = "/api/v1/documents/"


@pytest.fixture
def api_client(db):
    user = get_user_model().objects.create_user(
        username="document-record-tester", password="test-password"
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def document_payload(**overrides):
    payload = {
        "original_filename": "contrato.pdf",
        "file_path": "pending/contrato.pdf",
        "file_size_bytes": 2048,
        "mime_type": "application/pdf",
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
class TestDocumentRecord:
    def test_create_assigns_and_persists_registration_number(self):
        document = Document.objects.create(**document_payload())

        assert document.filing_number == "RAD-20260922-000001"
        assert FilingSequence.objects.get(date=date(2026, 9, 22)).last_number == 1
        assert Document.objects.get(pk=document.pk).filing_number == document.filing_number

    def test_new_record_starts_as_received(self):
        document = Document.objects.create(**document_payload())

        assert document.processing_status == Document.ProcessingStatus.RECEIVED

    def test_multiple_records_receive_different_numbers(self):
        first = Document.objects.create(**document_payload())
        second = Document.objects.create(**document_payload(original_filename="otro.pdf"))

        assert first.filing_number != second.filing_number

    def test_duplicate_registration_number_is_rejected(self):
        Document.objects.create(**document_payload(filing_number="RAD-20260922-000099"))

        with pytest.raises(IntegrityError):
            Document.objects.create(
                **document_payload(
                    filing_number="RAD-20260922-000099",
                    original_filename="duplicado.pdf",
                )
            )


@pytest.mark.django_db
class TestDocumentRecordApi:
    def test_create_endpoint_returns_registered_document(self, api_client):
        response = api_client.post(DOCUMENTS_URL, document_payload(), format="json")

        assert response.status_code == 201, response.content
        body = response.json()
        assert body["filing_number"] == "RAD-20260922-000001"
        assert body["processing_status"] == "RECIBIDO"

    def test_detail_endpoint_displays_basic_document_information(self, api_client):
        document = Document.objects.create(**document_payload())

        response = api_client.get(f"{DOCUMENTS_URL}{document.pk}/")

        assert response.status_code == 200
        assert response.json() == {
            "id": str(document.pk),
            "filing_number": document.filing_number,
            "original_filename": "contrato.pdf",
            "file_path": "pending/contrato.pdf",
            "file_hash": "",
            "file_size_bytes": 2048,
            "mime_type": "application/pdf",
            "processing_status": "RECIBIDO",
            "created_at": response.json()["created_at"],
            "updated_at": response.json()["updated_at"],
        }

    def test_create_requires_basic_file_information(self, api_client):
        response = api_client.post(DOCUMENTS_URL, {"original_filename": "incompleto.pdf"}, format="json")

        assert response.status_code == 400
        assert "file_path" in response.json()
        assert "file_size_bytes" in response.json()
        assert "mime_type" in response.json()
