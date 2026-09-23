"""Pruebas de POST /api/v1/documents/upload/ y /batch-upload/ (US-002, US-004, US-005, US-006, US-011)."""
import hashlib
import time

import pytest
from django.core.files.storage import default_storage

from apps.documents.models import AuditLog, Document
from apps.documents.services import FILING_NUMBER_PATTERN

UPLOAD_URL = "/api/v1/documents/upload/"
BATCH_URL = "/api/v1/documents/batch-upload/"


@pytest.mark.django_db
class TestDocumentUpload:
    def test_upload_registers_document_and_queues_processing(
        self, api_client, user, pdf_factory, mock_celery_delay, django_capture_on_commit_callbacks
    ):
        file = pdf_factory("cuenta_cobro_sep.pdf", size=1_048_576)
        expected_hash = hashlib.sha256(file.read()).hexdigest()
        file.seek(0)

        started = time.perf_counter()
        with django_capture_on_commit_callbacks(execute=True):
            response = api_client.post(
                UPLOAD_URL,
                {"file": file, "source_channel": "DIGITAL_INTERNO"},
                format="multipart",
                HTTP_USER_AGENT="pytest-agent/1.0",
                REMOTE_ADDR="10.1.2.3",
            )
        elapsed = time.perf_counter() - started

        assert response.status_code == 201, response.content
        body = response.json()
        assert set(body) == {
            "id", "filing_number", "original_filename", "file_size_bytes",
            "source_channel", "processing_status", "created_at",
        }
        assert FILING_NUMBER_PATTERN.match(body["filing_number"])
        assert body["processing_status"] == "RECIBIDO"
        assert body["source_channel"] == "DIGITAL_INTERNO"
        assert body["original_filename"] == "cuenta_cobro_sep.pdf"
        assert body["file_size_bytes"] == 1_048_576
        assert elapsed < 2.0

        document = Document.objects.get(pk=body["id"])
        assert document.file_hash == expected_hash
        assert document.mime_type == "application/pdf"
        assert document.registered_by == user
        assert document.digital_record is None
        assert document.file_path.startswith("radicados/sin_clasificar/")
        assert document.file_path.endswith(f"{document.filing_number}_cuenta_cobro_sep.pdf")
        assert default_storage.exists(document.file_path)
        assert default_storage.size(document.file_path) == 1_048_576

        log = document.audit_logs.get()
        assert log.action == AuditLog.Action.UPLOAD
        assert log.performed_by == user
        assert log.ip_address == "10.1.2.3"
        assert log.user_agent == "pytest-agent/1.0"
        assert log.details["file_hash"] == expected_hash
        assert log.details["source_channel"] == "DIGITAL_INTERNO"

        mock_celery_delay.assert_called_once_with(str(document.pk))

    def test_upload_with_contract_stores_file_in_record_prefix(self, api_client, pdf_factory, contract):
        response = api_client.post(
            UPLOAD_URL,
            {"file": pdf_factory("poliza.pdf"), "source_channel": "FISICO_ESCANEADO", "contract_id": str(contract.pk)},
            format="multipart",
        )

        assert response.status_code == 201, response.content
        document = Document.objects.get(pk=response.json()["id"])
        assert document.digital_record == contract.digital_record
        assert document.source_channel == Document.SourceChannel.PHYSICAL
        assert document.file_path.startswith("expedientes/CONT-2026-042/")
        assert document.audit_logs.get().details["contract_number"] == "CONT-2026-042"

    def test_upload_stores_document_metadata(self, api_client, pdf_factory):
        response = api_client.post(
            UPLOAD_URL,
            {
                "file": pdf_factory("metadatos.pdf"),
                "document_date": "2026-09-20",
                "external_sender_name": "Carolina Restrepo",
            },
            format="multipart",
        )

        assert response.status_code == 201, response.content
        document = Document.objects.get(pk=response.json()["id"])
        assert document.document_date.isoformat() == "2026-09-20"
        assert document.external_sender_name == "Carolina Restrepo"

    def test_upload_uses_forwarded_ip_behind_proxy(self, api_client, pdf_factory):
        response = api_client.post(
            UPLOAD_URL,
            {"file": pdf_factory()},
            format="multipart",
            HTTP_X_FORWARDED_FOR="200.10.20.30, 10.0.0.1",
        )
        assert response.status_code == 201
        assert Document.objects.get().audit_logs.get().ip_address == "200.10.20.30"

    def test_upload_accepts_png_and_jpg(self, api_client):
        from django.core.files.uploadedfile import SimpleUploadedFile

        png = SimpleUploadedFile("escaneo.png", b"\x89PNG\r\n" + b"0" * 100, content_type="image/png")
        jpg = SimpleUploadedFile("foto.JPG", b"\xff\xd8\xff" + b"0" * 100, content_type="image/jpeg")

        assert api_client.post(UPLOAD_URL, {"file": png}, format="multipart").status_code == 201
        assert api_client.post(UPLOAD_URL, {"file": jpg}, format="multipart").status_code == 201
        assert set(Document.objects.values_list("mime_type", flat=True)) == {"image/png", "image/jpeg"}

    def test_rejects_unknown_contract(self, api_client, pdf_factory):
        response = api_client.post(
            UPLOAD_URL,
            {"file": pdf_factory(), "contract_id": "7b8e5c1a-3d2f-4a6b-9c8e-1f2e3d4c5b6a"},
            format="multipart",
        )
        assert response.status_code == 400
        assert "contract_id" in response.json()
        assert Document.objects.count() == 0

    def test_rejects_disallowed_extension(self, api_client, mock_celery_delay):
        from django.core.files.uploadedfile import SimpleUploadedFile

        file = SimpleUploadedFile("malware.exe", b"MZ" + b"0" * 100, content_type="application/octet-stream")
        response = api_client.post(UPLOAD_URL, {"file": file}, format="multipart")

        assert response.status_code == 400
        assert "file" in response.json()
        assert Document.objects.count() == 0
        mock_celery_delay.assert_not_called()

    def test_valid_upload_succeeds_after_rejected_attempt(self, api_client, pdf_factory):
        from django.core.files.uploadedfile import SimpleUploadedFile

        rejected = api_client.post(
            UPLOAD_URL,
            {"file": SimpleUploadedFile("malware.exe", b"MZ", content_type="application/octet-stream")},
            format="multipart",
        )
        assert rejected.status_code == 400
        assert Document.objects.count() == 0

        accepted = api_client.post(UPLOAD_URL, {"file": pdf_factory("recuperado.pdf")}, format="multipart")

        assert accepted.status_code == 201, accepted.content
        assert accepted.json()["original_filename"] == "recuperado.pdf"
        assert Document.objects.count() == 1

    def test_rejects_mismatched_mime_type(self, api_client, pdf_factory):
        response = api_client.post(
            UPLOAD_URL, {"file": pdf_factory("falso.pdf", content_type="text/plain")}, format="multipart"
        )
        assert response.status_code == 400
        assert Document.objects.count() == 0

    def test_rejects_invalid_document_date_format(self, api_client, pdf_factory):
        response = api_client.post(
            UPLOAD_URL,
            {"file": pdf_factory("fecha-invalida.pdf"), "document_date": "20/09/2026"},
            format="multipart",
        )

        assert response.status_code == 400
        assert "document_date" in response.json()
        assert Document.objects.count() == 0

    def test_rejects_file_over_size_limit(self, api_client, pdf_factory, settings):
        settings.UPLOAD_MAX_SIZE_BYTES = 1024

        response = api_client.post(UPLOAD_URL, {"file": pdf_factory(size=2048)}, format="multipart")

        assert response.status_code == 400
        assert "supera" in str(response.json()["file"])
        assert Document.objects.count() == 0

    def test_rejects_empty_file(self, api_client):
        from django.core.files.uploadedfile import SimpleUploadedFile

        response = api_client.post(
            UPLOAD_URL, {"file": SimpleUploadedFile("vacio.pdf", b"", content_type="application/pdf")}, format="multipart"
        )
        assert response.status_code == 400

    def test_rejects_registration_without_required_file(self, api_client):
        response = api_client.post(UPLOAD_URL, {}, format="multipart")

        assert response.status_code == 400
        assert "file" in response.json()
        assert Document.objects.count() == 0

    def test_rejects_portal_channel_from_internal_endpoint(self, api_client, pdf_factory):
        response = api_client.post(
            UPLOAD_URL, {"file": pdf_factory(), "source_channel": "PORTAL_WEB"}, format="multipart"
        )
        assert response.status_code == 400
        assert "source_channel" in response.json()

    def test_requires_authentication(self, anonymous_client, pdf_factory):
        response = anonymous_client.post(UPLOAD_URL, {"file": pdf_factory()}, format="multipart")
        assert response.status_code == 401


@pytest.mark.django_db
class TestBatchUpload:
    def test_batch_upload_registers_every_file(
        self, api_client, pdf_factory, mock_celery_delay, django_capture_on_commit_callbacks
    ):
        files = [pdf_factory(f"doc{i}.pdf") for i in range(1, 4)]

        with django_capture_on_commit_callbacks(execute=True):
            response = api_client.post(
                BATCH_URL, {"files": files, "source_channel": "FISICO_ESCANEADO"}, format="multipart"
            )

        assert response.status_code == 202, response.content
        body = response.json()
        assert body["message"] == "3 documentos recibidos para radicación y procesamiento asíncrono."
        assert [item["filename"] for item in body["items"]] == ["doc1.pdf", "doc2.pdf", "doc3.pdf"]
        assert all(item["status"] == "RECIBIDO" for item in body["items"])

        numbers = [item["filing_number"] for item in body["items"]]
        assert len(set(numbers)) == 3
        assert [int(n.rsplit("-", 1)[1]) for n in numbers] == [1, 2, 3]

        assert Document.objects.count() == 3
        assert AuditLog.objects.filter(action=AuditLog.Action.UPLOAD).count() == 3
        assert mock_celery_delay.call_count == 3

    def test_batch_with_contract_links_all_documents(self, api_client, pdf_factory, contract):
        response = api_client.post(
            BATCH_URL,
            {"files": [pdf_factory("a.pdf"), pdf_factory("b.pdf")], "contract_id": str(contract.pk)},
            format="multipart",
        )
        assert response.status_code == 202
        assert contract.digital_record.documents.count() == 2

    def test_batch_is_rejected_entirely_if_one_file_is_invalid(self, api_client, pdf_factory):
        from django.core.files.uploadedfile import SimpleUploadedFile

        files = [pdf_factory("ok.pdf"), SimpleUploadedFile("malo.txt", b"hola", content_type="text/plain")]
        response = api_client.post(BATCH_URL, {"files": files}, format="multipart")

        assert response.status_code == 400
        assert "files" in response.json()
        assert Document.objects.count() == 0

    def test_batch_requires_at_least_one_file(self, api_client):
        response = api_client.post(BATCH_URL, {"source_channel": "FISICO_ESCANEADO"}, format="multipart")
        assert response.status_code == 400
        assert "files" in response.json()
