"""Pruebas de consulta, bandeja HITL, validación humana, metadatos (US-007) y URLs prefirmadas."""
from datetime import date

import pytest

from apps.documents.models import AuditLog, Document
from apps.documents.services.audit import log_action

BASE = "/api/v1/documents/"


def _detail(document, suffix=""):
    return f"{BASE}{document.pk}/{suffix}"


@pytest.fixture
def review_document(document):
    document.processing_status = Document.ProcessingStatus.NEEDS_REVIEW
    document.ai_extracted_data = {
        "contract_number": "CONT-2026-042",
        "document_type": "POLIZA",
        "expiration_date": "2027-09-20",
        "confidence_score": 0.62,
    }
    document.ai_confidence_score = 0.62
    document.save()
    return document


@pytest.mark.django_db
class TestDocumentQueries:
    def test_list_is_paginated_and_newest_first(self, api_client, document):
        response = api_client.get(BASE)

        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 1
        assert body["results"][0]["filing_number"] == document.filing_number
        assert body["results"][0]["needs_human_review"] is False
        assert body["results"][0]["contract_number"] is None
        assert body["results"][0]["registered_by"] == "analista"

    def test_retrieve_exposes_full_metadata(self, api_client, document, contract, document_type):
        document.digital_record = contract.digital_record
        document.document_type = document_type
        document.save()

        body = api_client.get(_detail(document)).json()

        assert body["contract_id"] == str(contract.pk)
        assert body["contract_number"] == "CONT-2026-042"
        assert body["client_name"] == "Logística Andina S.A.S."
        assert body["document_type"]["code"] == "POLIZA_CUMPLIMIENTO"
        assert body["file_hash"] == "a" * 64

    def test_filter_by_status_and_search_by_filing_number(self, api_client, document, review_document):
        assert document.pk == review_document.pk  # misma fila, ya en REQUIERE_REVISION
        other = Document.objects.create(
            filing_number="RAD-20260920-000099",
            file_path="x/y.pdf",
            original_filename="otro.pdf",
            file_hash="b" * 64,
            file_size_bytes=10,
        )

        by_status = api_client.get(BASE, {"processing_status": "REQUIERE_REVISION"}).json()
        assert [d["id"] for d in by_status["results"]] == [str(review_document.pk)]

        by_search = api_client.get(BASE, {"search": "000099"}).json()
        assert [d["id"] for d in by_search["results"]] == [str(other.pk)]

    def test_requires_authentication(self, anonymous_client, document):
        assert anonymous_client.get(BASE).status_code == 401
        assert anonymous_client.get(_detail(document, "view-url/")).status_code == 401


@pytest.mark.django_db
class TestPendingReviewInbox:
    def test_lists_only_documents_needing_review(self, api_client, review_document):
        Document.objects.create(
            filing_number="RAD-20260920-000050",
            file_path="x/z.pdf",
            original_filename="listo.pdf",
            file_hash="c" * 64,
            file_size_bytes=10,
            processing_status=Document.ProcessingStatus.PROCESSED,
        )

        body = api_client.get(f"{BASE}pending-review/").json()

        assert body["count"] == 1
        item = body["results"][0]
        assert item["id"] == str(review_document.pk)
        assert item["ai_confidence_score"] == 0.62
        assert item["ai_extracted_data"]["contract_number"] == "CONT-2026-042"
        assert item["needs_human_review"] is True


@pytest.mark.django_db
class TestHumanValidation:
    def test_validate_archives_document_in_contract_record(
        self, api_client, review_document, contract, document_type
    ):
        response = api_client.post(
            _detail(review_document, "validate/"),
            {
                "contract_id": str(contract.pk),
                "document_type_id": str(document_type.pk),
                "expiration_date": "2027-09-20",
            },
            format="json",
        )

        assert response.status_code == 200, response.content
        body = response.json()
        assert body["processing_status"] == "PROCESADO"
        assert body["contract_number"] == "CONT-2026-042"
        assert body["document_type"]["code"] == "POLIZA_CUMPLIMIENTO"
        assert body["expiration_date"] == "2027-09-20"

        review_document.refresh_from_db()
        assert review_document.digital_record == contract.digital_record
        assert review_document.expiration_date == date(2027, 9, 20)

        log = review_document.audit_logs.get(action=AuditLog.Action.HUMAN_VALIDATE)
        assert log.performed_by.username == "analista"
        assert log.details["previous"]["processing_status"] == "REQUIERE_REVISION"
        assert log.details["new"]["contract_number"] == "CONT-2026-042"
        assert log.details["ai_confidence_score"] == 0.62

    def test_validate_requires_expiration_for_types_with_validity(
        self, api_client, review_document, contract, document_type
    ):
        response = api_client.post(
            _detail(review_document, "validate/"),
            {"contract_id": str(contract.pk), "document_type_id": str(document_type.pk)},
            format="json",
        )
        assert response.status_code == 400
        assert "expiration_date" in response.json()
        review_document.refresh_from_db()
        assert review_document.processing_status == Document.ProcessingStatus.NEEDS_REVIEW

    def test_validate_without_expiration_is_fine_for_invoices(
        self, api_client, review_document, contract, invoice_type
    ):
        response = api_client.post(
            _detail(review_document, "validate/"),
            {"contract_id": str(contract.pk), "document_type_id": str(invoice_type.pk)},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["document_type"]["code"] == "FACTURA"

    def test_validate_rejects_unknown_contract_or_type(self, api_client, review_document, document_type):
        response = api_client.post(
            _detail(review_document, "validate/"),
            {"contract_id": "9a1b2c3d-4e5f-6a7b-8c9d-0e1f2a3b4c5d", "document_type_id": str(document_type.pk)},
            format="json",
        )
        assert response.status_code == 400
        assert "contract_id" in response.json()


@pytest.mark.django_db
class TestMetadataUpdate:
    def test_patch_logs_previous_and_new_values(self, api_client, document, invoice_type):
        response = api_client.patch(
            _detail(document, "metadata/"),
            {"document_type": str(invoice_type.pk), "expiration_date": "2027-09-20"},
            format="json",
        )

        assert response.status_code == 200, response.content
        assert response.json()["document_type"]["code"] == "FACTURA"
        assert response.json()["expiration_date"] == "2027-09-20"

        log = document.audit_logs.get(action=AuditLog.Action.METADATA_UPDATE)
        changes = log.details["changes"]
        assert changes["expiration_date"] == {"before": None, "after": "2027-09-20"}
        assert changes["document_type"] == {"before": None, "after": "FACTURA"}
        assert set(log.details["fields"]) == {"expiration_date", "document_type"}

    def test_patch_can_clear_expiration(self, api_client, document):
        document.expiration_date = date(2027, 1, 1)
        document.save()

        response = api_client.patch(_detail(document, "metadata/"), {"expiration_date": None}, format="json")

        assert response.status_code == 200
        document.refresh_from_db()
        assert document.expiration_date is None

    def test_patch_without_fields_is_rejected(self, api_client, document):
        response = api_client.patch(_detail(document, "metadata/"), {}, format="json")
        assert response.status_code == 400
        assert not document.audit_logs.exists()


@pytest.mark.django_db
class TestPresignedUrls:
    def test_view_url_returns_temporary_link_and_logs_view(self, api_client, document):
        response = api_client.get(_detail(document, "view-url/"), REMOTE_ADDR="10.9.9.9")

        assert response.status_code == 200
        body = response.json()
        assert body["filing_number"] == document.filing_number
        assert body["expires_in_seconds"] == 900
        assert document.file_path.split("/")[-1] in body["view_url"]

        log = document.audit_logs.get(action=AuditLog.Action.VIEW)
        assert log.ip_address == "10.9.9.9"
        assert log.details["storage_key"] == document.file_path

    def test_download_url_logs_download(self, api_client, document):
        response = api_client.get(_detail(document, "download-url/"))

        assert response.status_code == 200
        assert response.json()["original_filename"] == "cuenta_cobro_sep.pdf"
        assert document.audit_logs.filter(action=AuditLog.Action.DOWNLOAD).count() == 1


@pytest.mark.django_db
class TestAuditTrail:
    def test_audit_trail_lists_actions_newest_first(self, api_client, document, user):
        from datetime import datetime, timedelta, timezone as dt_timezone
        from unittest.mock import patch

        base = datetime(2026, 9, 20, 15, 0, 0, tzinfo=dt_timezone.utc)
        # Timestamps explícitos: el reloj de Windows puede repetir el mismo microsegundo.
        with patch("django.utils.timezone.now", side_effect=[base + timedelta(seconds=i) for i in range(3)]):
            log_action(document, AuditLog.Action.UPLOAD, user=user, details={"step": 1})
            log_action(document, AuditLog.Action.AI_CLASSIFY, details={"confidence": 0.5})
            log_action(document, AuditLog.Action.VIEW, user=user)

        body = api_client.get(_detail(document, "audit-trail/")).json()

        assert body["count"] == 3
        actions = [entry["action"] for entry in body["results"]]
        assert actions == ["CONSULTA_VISUAL", "CLASIFICACION_IA", "CARGA"]
        assert body["results"][0]["performed_by"] == "analista"
        assert body["results"][1]["performed_by"] is None
        assert body["results"][2]["action_label"] == "Carga y Radicación"
        assert body["results"][2]["details"] == {"step": 1}
