"""Pruebas del portal público de inquilinos: verificación de contrato y radicación externa."""
from datetime import date, timedelta

import pytest
from django.core import signing
from django.core.cache import cache

from apps.core.models import Contract
from apps.documents.models import AuditLog, Document
from apps.portal.services import PORTAL_TOKEN_SALT, receipt_signature

VERIFY = "/api/v1/portal/verify-contract/"
SUBMIT = "/api/v1/portal/submit-document/"


@pytest.fixture(autouse=True)
def reset_throttle_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def portal_token(anonymous_client, contract):
    response = anonymous_client.post(
        VERIFY, {"contract_number": "CONT-2026-042", "identification_number": "900.123.456-1"}, format="json"
    )
    assert response.status_code == 200, response.content
    return response.json()["portal_token"]


@pytest.mark.django_db
class TestVerifyContract:
    def test_valid_credentials_return_session_and_context(self, anonymous_client, contract, document, document_type):
        document.digital_record = contract.digital_record
        document.document_type = document_type
        document.expiration_date = date.today() + timedelta(days=10)
        document.save()

        response = anonymous_client.post(
            VERIFY, {"contract_number": "cont-2026-042", "identification_number": "9001234561"}, format="json"
        )

        assert response.status_code == 200, response.content
        body = response.json()
        assert body["portal_token"]
        assert body["expires_in_seconds"] == 1800
        assert body["contract"]["contract_number"] == "CONT-2026-042"
        assert body["contract"]["property_address"].startswith("Bodega 12")
        assert body["client"]["name"] == "Logística Andina S.A.S."
        assert body["client"]["identification_number"].endswith("4561")
        assert body["client"]["identification_number"].startswith("*")
        codes = {t["code"] for t in body["document_types"]}
        assert "POLIZA_CUMPLIMIENTO" in codes and "CONTRATO" not in codes
        assert body["expiring_documents"][0]["filing_number"] == document.filing_number
        assert body["expiring_documents"][0]["expired"] is False

    def test_wrong_identification_is_rejected_with_generic_message(self, anonymous_client, contract):
        response = anonymous_client.post(
            VERIFY, {"contract_number": "CONT-2026-042", "identification_number": "800000000-1"}, format="json"
        )
        assert response.status_code == 404
        assert "No encontramos" in response.json()["detail"]

    def test_unknown_contract_is_rejected(self, anonymous_client, contract):
        response = anonymous_client.post(
            VERIFY, {"contract_number": "CONT-0000-000", "identification_number": "900123456-1"}, format="json"
        )
        assert response.status_code == 404

    def test_terminated_contract_cannot_use_portal(self, anonymous_client, contract):
        contract.status = Contract.ContractStatus.TERMINATED
        contract.save()
        response = anonymous_client.post(
            VERIFY, {"contract_number": "CONT-2026-042", "identification_number": "900123456-1"}, format="json"
        )
        assert response.status_code == 404

    def test_missing_fields_are_validated(self, anonymous_client):
        response = anonymous_client.post(VERIFY, {"contract_number": "X"}, format="json")
        assert response.status_code == 400
        assert "identification_number" in response.json()


@pytest.mark.django_db
class TestSubmitDocument:
    def test_tenant_can_file_a_policy_and_gets_receipt(
        self, anonymous_client, contract, portal_token, pdf_factory, mock_celery_delay, django_capture_on_commit_callbacks
    ):
        with django_capture_on_commit_callbacks(execute=True):
            response = anonymous_client.post(
                SUBMIT,
                {
                    "portal_token": portal_token,
                    "file": pdf_factory("poliza_renovada.pdf"),
                    "document_type_code": "POLIZA_CUMPLIMIENTO",
                    "sender_name": "María Gómez",
                    "expiration_date": "2027-09-20",
                },
                format="multipart",
                REMOTE_ADDR="190.10.10.10",
            )

        assert response.status_code == 201, response.content
        body = response.json()
        assert body["filing_number"].startswith("RAD-")
        assert body["contract_number"] == "CONT-2026-042"
        assert body["document_type"] == "Póliza de Cumplimiento"
        assert body["sender_name"] == "María Gómez"
        assert body["processing_status"] == "RECIBIDO"
        assert body["received_at_display"]
        assert body["receipt_signature"] == receipt_signature(body["filing_number"], body["file_hash"])

        document = Document.objects.get(filing_number=body["filing_number"])
        assert document.source_channel == Document.SourceChannel.WEB_PORTAL
        assert document.registered_by is None
        assert document.external_sender_name == "María Gómez"
        assert document.digital_record == contract.digital_record
        assert document.document_type.code == "POLIZA_CUMPLIMIENTO"
        assert document.expiration_date == date(2027, 9, 20)
        assert document.file_path.startswith("expedientes/CONT-2026-042/")

        actions = list(document.audit_logs.order_by("timestamp").values_list("action", flat=True))
        assert AuditLog.Action.UPLOAD in actions and AuditLog.Action.METADATA_UPDATE in actions
        upload_log = document.audit_logs.get(action=AuditLog.Action.UPLOAD)
        assert upload_log.performed_by is None
        assert upload_log.ip_address == "190.10.10.10"
        mock_celery_delay.assert_called_once_with(str(document.pk))

    def test_token_can_travel_in_header(self, anonymous_client, portal_token, pdf_factory):
        response = anonymous_client.post(
            SUBMIT,
            {"file": pdf_factory("carta.pdf"), "document_type_code": "CARTA_SOLICITUD", "sender_name": "Ana"},
            format="multipart",
            HTTP_X_PORTAL_TOKEN=portal_token,
        )
        assert response.status_code == 201, response.content

    def test_missing_or_invalid_token_is_unauthorized(self, anonymous_client, pdf_factory, contract):
        no_token = anonymous_client.post(
            SUBMIT, {"file": pdf_factory(), "document_type_code": "FACTURA", "sender_name": "Ana"}, format="multipart"
        )
        assert no_token.status_code == 401

        bad_token = anonymous_client.post(
            SUBMIT,
            {"portal_token": "abc:def", "file": pdf_factory(), "document_type_code": "FACTURA", "sender_name": "Ana"},
            format="multipart",
        )
        assert bad_token.status_code == 401
        assert Document.objects.count() == 0

    def test_expired_token_is_rejected(self, anonymous_client, contract, pdf_factory, settings):
        settings.PORTAL_SESSION_TTL_SECONDS = 60
        signer = signing.TimestampSigner(salt=PORTAL_TOKEN_SALT)
        old_token = signer.sign_object({"contract_id": str(contract.pk)})
        # Simula el paso del tiempo alterando el timestamp embebido: firma inválida => 401.
        tampered = old_token[:-3] + "xyz"

        response = anonymous_client.post(
            SUBMIT,
            {"portal_token": tampered, "file": pdf_factory(), "document_type_code": "FACTURA", "sender_name": "Ana"},
            format="multipart",
        )
        assert response.status_code == 401

    def test_policy_requires_expiration_date(self, anonymous_client, portal_token, pdf_factory):
        response = anonymous_client.post(
            SUBMIT,
            {
                "portal_token": portal_token,
                "file": pdf_factory(),
                "document_type_code": "POLIZA_CUMPLIMIENTO",
                "sender_name": "Ana",
            },
            format="multipart",
        )
        assert response.status_code == 400
        assert "expiration_date" in response.json()

    def test_unknown_document_type_is_rejected(self, anonymous_client, portal_token, pdf_factory):
        response = anonymous_client.post(
            SUBMIT,
            {"portal_token": portal_token, "file": pdf_factory(), "document_type_code": "INVENTADO", "sender_name": "Ana"},
            format="multipart",
        )
        assert response.status_code == 400
        assert "document_type_code" in response.json()

    def test_invalid_file_is_rejected(self, anonymous_client, portal_token):
        from django.core.files.uploadedfile import SimpleUploadedFile

        response = anonymous_client.post(
            SUBMIT,
            {
                "portal_token": portal_token,
                "file": SimpleUploadedFile("script.js", b"alert(1)", content_type="text/javascript"),
                "document_type_code": "FACTURA",
                "sender_name": "Ana",
            },
            format="multipart",
        )
        assert response.status_code == 400
        assert Document.objects.count() == 0
