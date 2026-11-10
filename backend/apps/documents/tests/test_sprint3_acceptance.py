"""
Pruebas de aceptación del Sprint 3 (US-018 a US-027): una prueba por caso de prueba del backlog.

Cada prueba lleva en su nombre el identificador del caso (TC-086 … TC-130) definido en el issue de la
historia de usuario, para que la wiki ("Test Case Design - Sprint 3") pueda trazarlas una a una.
US-021 (imprimir) quedó como "Won't" en el backlog; su botón en la interfaz reutiliza la consulta
(US-019), por eso sus casos se cubren con las mismas pruebas de consulta y no tienen pruebas propias.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.utils import timezone

from apps.core.models import Client, DocumentType
from apps.core.services import create_contract
from apps.documents.models import AuditLog, Document, FilingSequence
from apps.documents.services.audit import log_action
from conftest import SAMPLE_PDF_BYTES, store_sample_file

CONTRACTS = "/api/v1/contracts/"
DOCUMENTS = "/api/v1/documents/"
VERIFY = "/api/v1/portal/verify-contract/"
SUBMIT = "/api/v1/portal/submit-document/"


# ---------------------------------------------------------------- fixtures --
@pytest.fixture(autouse=True)
def reset_throttle_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def record(contract):
    return contract.digital_record


def make_document(record, code: str | None, name: str, *, stored: bool = True, day=date(2026, 11, 3)):
    key = f"{record.storage_path.rstrip('/')}/{name}"
    return Document.objects.create(
        filing_number=FilingSequence.get_next_number(day),
        digital_record=record,
        document_type=DocumentType.objects.get(code=code) if code else None,
        file_path=store_sample_file(key) if stored else key,
        original_filename=name,
        file_hash="d" * 64,
        file_size_bytes=len(SAMPLE_PDF_BYTES),
        mime_type="application/pdf",
        processing_status=Document.ProcessingStatus.PROCESSED,
    )


@pytest.fixture
def filed_documents(record):
    """Expediente con documentos de tres tipos distintos."""
    return {
        "poliza": make_document(record, "POLIZA_CUMPLIMIENTO", "poliza.pdf"),
        "factura": make_document(record, "FACTURA", "factura.pdf"),
        "rut": make_document(record, "RUT", "rut.pdf"),
    }


@pytest.fixture
def second_contract(db):
    other = Client.objects.create(
        name="Comercializadora del Valle S.A.S.",
        identification_number="901.777.888-2",
        email="gerencia@cvalle.co",
    )
    return create_contract(
        contract_number="CONT-2026-100",
        client=other,
        property_address="Local 4, Centro Comercial Oviedo, Medellín",
        start_date=date(2026, 3, 1),
        end_date=date(2027, 2, 28),
    )


def results(response):
    assert response.status_code == 200, response.content
    return response.json()["results"]


# ========================================================== US-018 Buscar ===
@pytest.mark.django_db
class TestUS018SearchContractRecords:
    def test_tc086_search_by_contract_number(self, api_client, contract, second_contract):
        found = results(api_client.get(CONTRACTS, {"q": "CONT-2026-100"}))
        assert [c["contract_number"] for c in found] == ["CONT-2026-100"]

    def test_tc087_search_by_client_name_and_identification(self, api_client, contract, second_contract):
        by_name = results(api_client.get(CONTRACTS, {"q": "Logística Andina"}))
        assert [c["contract_number"] for c in by_name] == ["CONT-2026-042"]
        by_nit = results(api_client.get(CONTRACTS, {"q": "9017778882"}))
        assert [c["contract_number"] for c in by_nit] == ["CONT-2026-100"]

    def test_tc088_search_by_other_criterion_property_address(self, api_client, contract, second_contract):
        found = results(api_client.get(CONTRACTS, {"q": "Oviedo"}))
        assert [c["contract_number"] for c in found] == ["CONT-2026-100"]

    def test_tc089_search_without_matches_returns_empty_list(self, api_client, contract):
        response = api_client.get(CONTRACTS, {"q": "CONT-9999-999"})
        assert response.status_code == 200
        assert response.json()["count"] == 0  # la interfaz muestra "No hay contratos que coincidan"

    def test_tc090_selected_result_gives_access_to_the_record(self, api_client, contract, filed_documents):
        selected = results(api_client.get(CONTRACTS, {"q": "CONT-2026-042"}))[0]
        detail = api_client.get(f"{CONTRACTS}{selected['id']}/").json()
        documents = results(api_client.get(f"{CONTRACTS}{selected['id']}/documents/"))
        assert detail["digital_record"]["storage_path"].startswith("expedientes/CONT-2026-042")
        assert len(documents) == 3


# ============================================================= US-019 Ver ===
@pytest.mark.django_db
class TestUS019ViewDocument:
    def test_tc091_record_lists_its_documents(self, api_client, contract, filed_documents):
        documents = results(api_client.get(f"{CONTRACTS}{contract.pk}/documents/"))
        assert {d["original_filename"] for d in documents} == {"poliza.pdf", "factura.pdf", "rut.pdf"}

    def test_tc092_selected_document_gets_a_temporary_view_url(self, api_client, filed_documents):
        document = filed_documents["poliza"]
        response = api_client.get(f"{DOCUMENTS}{document.pk}/view-url/")
        assert response.status_code == 200
        assert response.json()["view_url"] and response.json()["expires_in_seconds"] == 900

    def test_tc093_viewing_does_not_modify_the_stored_document(self, api_client, filed_documents):
        document = filed_documents["poliza"]
        before = (document.file_path, document.file_hash, document.updated_at)
        api_client.get(f"{DOCUMENTS}{document.pk}/view-url/")
        document.refresh_from_db()
        assert (document.file_path, document.file_hash, document.updated_at) == before
        with default_storage.open(document.file_path, "rb") as handle:
            assert handle.read() == SAMPLE_PDF_BYTES

    def test_tc094_unavailable_file_is_reported_and_not_audited_as_viewed(self, api_client, record):
        missing = make_document(record, "RUT", "perdido.pdf", stored=False)
        response = api_client.get(f"{DOCUMENTS}{missing.pk}/view-url/")
        assert response.status_code == 404
        assert response.json()["code"] == "file_unavailable"
        assert "no está disponible" in response.json()["detail"]
        assert not missing.audit_logs.filter(action=AuditLog.Action.VIEW).exists()


# ======================================================== US-020 Descargar ===
@pytest.mark.django_db
class TestUS020DownloadDocument:
    def test_tc095_download_returns_a_link_with_the_original_name(self, api_client, filed_documents):
        document = filed_documents["factura"]
        body = api_client.get(f"{DOCUMENTS}{document.pk}/download-url/").json()
        assert body["download_url"] and body["original_filename"] == "factura.pdf"

    def test_tc096_downloaded_copy_matches_the_stored_bytes(self, api_client, filed_documents):
        document = filed_documents["factura"]
        url = api_client.get(f"{DOCUMENTS}{document.pk}/download-url/").json()["download_url"]
        # En pruebas el storage en memoria expone la clave en la URL: se lee el mismo objeto.
        assert document.file_path.split("/")[-1] in url
        with default_storage.open(document.file_path, "rb") as handle:
            assert handle.read() == SAMPLE_PDF_BYTES

    def test_tc097_unavailable_file_cannot_be_downloaded(self, api_client, record):
        missing = make_document(record, "FACTURA", "sin_archivo.pdf", stored=False)
        response = api_client.get(f"{DOCUMENTS}{missing.pk}/download-url/")
        assert response.status_code == 404
        assert "no se puede" in response.json()["detail"]
        assert not missing.audit_logs.filter(action=AuditLog.Action.DOWNLOAD).exists()

    def test_tc098_download_keeps_the_original_in_the_record(self, api_client, contract, filed_documents):
        document = filed_documents["factura"]
        api_client.get(f"{DOCUMENTS}{document.pk}/download-url/")
        documents = results(api_client.get(f"{CONTRACTS}{contract.pk}/documents/"))
        assert str(document.pk) in {d["id"] for d in documents}
        assert default_storage.exists(document.file_path)


# ================================================== US-022 Filtrar por tipo ===
@pytest.mark.django_db
class TestUS022FilterDocumentsByType:
    def test_tc103_record_exposes_several_types_to_filter(self, api_client, contract, filed_documents):
        documents = results(api_client.get(f"{CONTRACTS}{contract.pk}/documents/"))
        assert {d["document_type"]["code"] for d in documents} == {"POLIZA_CUMPLIMIENTO", "FACTURA", "RUT"}

    def test_tc104_filter_shows_only_the_selected_type(self, api_client, contract, filed_documents):
        documents = results(
            api_client.get(f"{CONTRACTS}{contract.pk}/documents/", {"document_type": "FACTURA"})
        )
        assert [d["original_filename"] for d in documents] == ["factura.pdf"]

    def test_tc105_removing_the_filter_shows_all_documents_again(self, api_client, contract, filed_documents):
        api_client.get(f"{CONTRACTS}{contract.pk}/documents/", {"document_type": "FACTURA"})
        assert len(results(api_client.get(f"{CONTRACTS}{contract.pk}/documents/"))) == 3

    def test_tc106_type_without_documents_returns_empty(self, api_client, contract, filed_documents):
        response = api_client.get(f"{CONTRACTS}{contract.pk}/documents/", {"document_type": "CONTRATO"})
        assert response.json()["count"] == 0  # la interfaz informa "No hay documentos de este tipo"

    def test_tc107_filtered_document_keeps_its_record(self, api_client, contract, filed_documents):
        document = results(api_client.get(f"{CONTRACTS}{contract.pk}/documents/", {"document_type": "RUT"}))[
            0
        ]
        detail = api_client.get(f"{DOCUMENTS}{document['id']}/").json()
        assert detail["contract_number"] == "CONT-2026-042"


# =============================================== US-023 Historial documento ===
def _timed_actions(document, user, actions):
    base = timezone.make_aware(datetime(2026, 11, 3, 9, 0, 0))
    with patch(
        "django.utils.timezone.now", side_effect=[base + timedelta(minutes=i) for i in range(len(actions))]
    ):
        for action, details in actions:
            log_action(document, action, user=user, details=details)
    return base


@pytest.mark.django_db
class TestUS023DocumentAuditHistory:
    def test_tc108_history_lists_the_document_actions(self, api_client, document, user):
        _timed_actions(document, user, [(AuditLog.Action.UPLOAD, {}), (AuditLog.Action.VIEW, {})])
        entries = results(api_client.get(f"{DOCUMENTS}{document.pk}/audit-trail/"))
        assert [e["action"] for e in entries] == ["CONSULTA_VISUAL", "CARGA"]

    def test_tc109_upload_event_shows_user_and_datetime(self, api_client, document, user):
        base = _timed_actions(document, user, [(AuditLog.Action.UPLOAD, {"channel": "DIGITAL_INTERNO"})])
        entry = results(api_client.get(f"{DOCUMENTS}{document.pk}/audit-trail/"))[0]
        assert entry["performed_by"] == "analista"
        assert datetime.fromisoformat(entry["timestamp"]) == base

    def test_tc110_modification_event_is_shown(self, api_client, document, document_type):
        api_client.patch(
            f"{DOCUMENTS}{document.pk}/metadata/", {"document_type": str(document_type.pk)}, format="json"
        )
        entry = results(api_client.get(f"{DOCUMENTS}{document.pk}/audit-trail/"))[0]
        assert entry["action"] == "ACTUALIZACION_METADATOS"
        assert entry["details"]["changes"]["document_type"]["after"] == "POLIZA_CUMPLIMIENTO"

    def test_tc111_consultation_event_is_shown(self, api_client, document):
        api_client.get(f"{DOCUMENTS}{document.pk}/view-url/")
        entry = results(api_client.get(f"{DOCUMENTS}{document.pk}/audit-trail/"))[0]
        assert entry["action"] == "CONSULTA_VISUAL"

    def test_tc112_document_without_events_returns_empty_history(self, api_client, document):
        response = api_client.get(f"{DOCUMENTS}{document.pk}/audit-trail/")
        assert response.status_code == 200 and response.json()["count"] == 0


# ============================================= US-024 Historial expediente ===
@pytest.mark.django_db
class TestUS024RecordAuditHistory:
    def test_tc113_record_history_aggregates_its_documents(self, api_client, contract, filed_documents, user):
        _timed_actions(filed_documents["poliza"], user, [(AuditLog.Action.UPLOAD, {})])
        _timed_actions(filed_documents["rut"], user, [(AuditLog.Action.UPLOAD, {})])
        entries = results(api_client.get(f"{CONTRACTS}{contract.pk}/audit-trail/"))
        assert {e["filing_number"] for e in entries} == {
            filed_documents["poliza"].filing_number,
            filed_documents["rut"].filing_number,
        }

    def test_tc114_upload_event_shows_user_and_datetime(self, api_client, contract, filed_documents, user):
        base = _timed_actions(filed_documents["poliza"], user, [(AuditLog.Action.UPLOAD, {})])
        entry = results(api_client.get(f"{CONTRACTS}{contract.pk}/audit-trail/"))[0]
        assert entry["performed_by"] == "analista"
        assert datetime.fromisoformat(entry["timestamp"]) == base

    def test_tc115_modification_event_is_shown(self, api_client, contract, filed_documents):
        document = filed_documents["poliza"]
        api_client.patch(
            f"{DOCUMENTS}{document.pk}/metadata/", {"expiration_date": "2027-06-30"}, format="json"
        )
        entries = results(
            api_client.get(f"{CONTRACTS}{contract.pk}/audit-trail/", {"action": "ACTUALIZACION_METADATOS"})
        )
        assert entries[0]["details"]["changes"]["expiration_date"]["after"] == "2027-06-30"

    def test_tc116_consultation_event_is_shown(self, api_client, contract, filed_documents):
        api_client.get(f"{DOCUMENTS}{filed_documents['rut'].pk}/view-url/")
        entries = results(
            api_client.get(f"{CONTRACTS}{contract.pk}/audit-trail/", {"action": "CONSULTA_VISUAL"})
        )
        assert len(entries) == 1 and entries[0]["filing_number"] == filed_documents["rut"].filing_number

    def test_tc117_record_without_events_returns_empty_history(self, api_client, second_contract):
        response = api_client.get(f"{CONTRACTS}{second_contract.pk}/audit-trail/")
        assert response.status_code == 200 and response.json()["count"] == 0


# ========================================== US-025 Registrar acciones ===
@pytest.mark.django_db
class TestUS025RecordDocumentActions:
    def test_tc118_action_is_recorded_in_document_history(self, api_client, document):
        api_client.get(f"{DOCUMENTS}{document.pk}/download-url/")
        assert document.audit_logs.filter(action=AuditLog.Action.DOWNLOAD).count() == 1

    def test_tc119_recorded_action_keeps_the_user(self, api_client, document, user):
        api_client.get(f"{DOCUMENTS}{document.pk}/download-url/")
        assert document.audit_logs.get(action=AuditLog.Action.DOWNLOAD).performed_by == user

    def test_tc120_recorded_action_keeps_the_timestamp(self, api_client, document):
        before = timezone.now()
        api_client.get(f"{DOCUMENTS}{document.pk}/download-url/")
        recorded = document.audit_logs.get(action=AuditLog.Action.DOWNLOAD).timestamp
        assert before - timedelta(seconds=1) <= recorded <= timezone.now() + timedelta(seconds=1)

    def test_tc121_modification_is_recorded_with_before_and_after(self, api_client, document):
        api_client.patch(
            f"{DOCUMENTS}{document.pk}/metadata/", {"external_sender_name": "Ana"}, format="json"
        )
        log = document.audit_logs.get(action=AuditLog.Action.METADATA_UPDATE)
        assert log.details["changes"]["external_sender_name"] == {"before": "", "after": "Ana"}

    def test_tc122_consultation_is_recorded(self, api_client, document):
        api_client.get(f"{DOCUMENTS}{document.pk}/view-url/", REMOTE_ADDR="10.1.2.3")
        log = document.audit_logs.get(action=AuditLog.Action.VIEW)
        assert log.document_id == document.pk and log.ip_address == "10.1.2.3"


# ===================================== US-026 / US-027 Radicación externa ===
def _portal_token(anonymous_client, contract_number="CONT-2026-042", identification="900.123.456-1"):
    return anonymous_client.post(
        VERIFY, {"contract_number": contract_number, "identification_number": identification}, format="json"
    )


@pytest.mark.django_db
class TestUS026SubmitDigitalDocument:
    def _submit(self, anonymous_client, token, file):
        return anonymous_client.post(
            SUBMIT,
            {"portal_token": token, "file": file, "document_type_code": "RUT", "sender_name": "Ana"},
            format="multipart",
        )

    def test_tc123_valid_document_is_accepted(self, anonymous_client, contract, pdf_factory):
        token = _portal_token(anonymous_client).json()["portal_token"]
        assert self._submit(anonymous_client, token, pdf_factory("rut.pdf")).status_code == 201

    def test_tc124_unsupported_document_is_rejected_with_message(
        self, anonymous_client, contract, pdf_factory
    ):
        token = _portal_token(anonymous_client).json()["portal_token"]
        response = self._submit(
            anonymous_client, token, pdf_factory("macro.exe", content_type="application/x-msdownload")
        )
        assert response.status_code == 400
        assert response.json()  # mensaje de validación para el cliente
        assert not Document.objects.exists()

    def test_tc125_submission_returns_a_receipt(self, anonymous_client, contract, pdf_factory):
        token = _portal_token(anonymous_client).json()["portal_token"]
        body = self._submit(anonymous_client, token, pdf_factory("rut.pdf")).json()
        assert body["filing_number"].startswith("RAD-") and body["receipt_signature"]

    def test_tc126_submitted_document_is_queued_for_processing(
        self, anonymous_client, contract, pdf_factory, mock_celery_delay, django_capture_on_commit_callbacks
    ):
        token = _portal_token(anonymous_client).json()["portal_token"]
        with django_capture_on_commit_callbacks(execute=True):
            body = self._submit(anonymous_client, token, pdf_factory("rut.pdf")).json()
        document = Document.objects.get(filing_number=body["filing_number"])
        assert document.processing_status == Document.ProcessingStatus.RECEIVED
        mock_celery_delay.assert_called_once_with(str(document.pk))


@pytest.mark.django_db
class TestUS027AssociateDocumentWithContract:
    def test_tc127_valid_contract_identifier_associates_the_document(
        self, anonymous_client, contract, pdf_factory
    ):
        token = _portal_token(anonymous_client).json()["portal_token"]
        body = anonymous_client.post(
            SUBMIT,
            {
                "portal_token": token,
                "file": pdf_factory("rut.pdf"),
                "document_type_code": "RUT",
                "sender_name": "Ana",
            },
            format="multipart",
        ).json()
        assert (
            Document.objects.get(filing_number=body["filing_number"]).digital_record
            == contract.digital_record
        )

    def test_tc128_unknown_contract_is_reported_and_nothing_is_created(self, anonymous_client, contract):
        response = _portal_token(anonymous_client, contract_number="CONT-0000-404")
        assert response.status_code == 404
        assert "No encontramos" in response.json()["detail"]
        assert not Document.objects.exists()

    def test_tc129_receipt_confirms_the_associated_contract(self, anonymous_client, contract, pdf_factory):
        token = _portal_token(anonymous_client).json()["portal_token"]
        body = anonymous_client.post(
            SUBMIT,
            {
                "portal_token": token,
                "file": pdf_factory("rut.pdf"),
                "document_type_code": "RUT",
                "sender_name": "Ana",
            },
            format="multipart",
        ).json()
        assert body["contract_number"] == "CONT-2026-042"

    def test_tc130_associated_document_is_available_in_the_contract_context(
        self, anonymous_client, api_client, contract, pdf_factory
    ):
        token = _portal_token(anonymous_client).json()["portal_token"]
        body = anonymous_client.post(
            SUBMIT,
            {
                "portal_token": token,
                "file": pdf_factory("rut.pdf"),
                "document_type_code": "RUT",
                "sender_name": "Ana",
            },
            format="multipart",
        ).json()
        documents = results(api_client.get(f"{CONTRACTS}{contract.pk}/documents/"))
        assert body["filing_number"] in {d["filing_number"] for d in documents}
