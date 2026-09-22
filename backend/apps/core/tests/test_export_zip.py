"""Pruebas de la exportación masiva del expediente en ZIP (US-020)."""
import hashlib
import io
import json
import zipfile

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from apps.documents.models import AuditLog, Document
from apps.documents.services.export import zip_entry_path

CONTRACTS = "/api/v1/contracts/"


def make_doc(filing, contract, document_type, content: bytes | None, **kwargs):
    path = f"expedientes/{contract.contract_number}/{filing}.pdf"
    if content is not None:
        default_storage.save(path, ContentFile(content))
    return Document.objects.create(
        filing_number=filing,
        digital_record=contract.digital_record,
        document_type=document_type,
        file_path=path,
        original_filename=kwargs.pop("original_filename", f"{filing}.pdf"),
        file_hash=hashlib.sha256(content or b"").hexdigest(),
        file_size_bytes=len(content or b""),
        processing_status=Document.ProcessingStatus.PROCESSED,
        **kwargs,
    )


def read_zip(response) -> zipfile.ZipFile:
    payload = b"".join(response.streaming_content)
    return zipfile.ZipFile(io.BytesIO(payload))


@pytest.mark.django_db
class TestExportZip:
    def test_streams_zip_with_documents_and_manifest(self, api_client, contract, document_type, invoice_type, user):
        policy = make_doc("RAD-20260921-000501", contract, document_type, b"%PDF-1.4 poliza " * 100, original_filename="poliza renovada 2026.pdf")
        invoice = make_doc("RAD-20260921-000502", contract, invoice_type, b"%PDF-1.4 factura", original_filename="factura.pdf")
        missing = make_doc("RAD-20260921-000503", contract, None, None, original_filename="perdido.pdf")

        response = api_client.get(f"{CONTRACTS}{contract.pk}/export-zip/", REMOTE_ADDR="10.7.7.7")

        assert response.status_code == 200
        assert response["Content-Type"] == "application/zip"
        assert response["Content-Disposition"].startswith('attachment; filename="expediente_CONT-2026-042_')
        assert response["X-Document-Count"] == "3"

        archive = read_zip(response)
        assert archive.testzip() is None
        names = set(archive.namelist())
        assert names == {
            "POLIZA/RAD-20260921-000501_poliza_renovada_2026.pdf",
            "FINANCIERO/RAD-20260921-000502_factura.pdf",
            "manifest.json",
        }
        assert archive.read("POLIZA/RAD-20260921-000501_poliza_renovada_2026.pdf") == b"%PDF-1.4 poliza " * 100
        assert archive.read("FINANCIERO/RAD-20260921-000502_factura.pdf") == b"%PDF-1.4 factura"

        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["export_type"] == "full_record_zip"
        assert manifest["generated_by"] == "analista"
        assert manifest["contract"]["contract_number"] == "CONT-2026-042"
        assert manifest["client"]["identification_number"] == "900123456-1"
        assert manifest["document_count"] == 2
        assert manifest["missing_files"] == [missing.filing_number]
        by_filing = {d["filing_number"]: d for d in manifest["documents"]}
        assert by_filing[policy.filing_number]["sha256"] == policy.file_hash
        assert by_filing[policy.filing_number]["document_type"] == "POLIZA_CUMPLIMIENTO"
        assert by_filing[policy.filing_number]["zip_path"] == zip_entry_path(policy)
        assert by_filing[invoice.filing_number]["size_bytes"] == len(b"%PDF-1.4 factura")
        assert by_filing[invoice.filing_number]["category"] == "FINANCIERO"

        # Se verifica la integridad: el hash del contenido exportado coincide con el manifest
        exported = archive.read(by_filing[policy.filing_number]["zip_path"])
        assert hashlib.sha256(exported).hexdigest() == by_filing[policy.filing_number]["sha256"]

    def test_export_is_audited_as_download_per_document(self, api_client, contract, document_type):
        docs = [make_doc(f"RAD-20260921-00060{i}", contract, document_type, b"%PDF" + bytes([i])) for i in range(3)]

        api_client.get(f"{CONTRACTS}{contract.pk}/export-zip/", REMOTE_ADDR="10.7.7.7")

        logs = AuditLog.objects.filter(action=AuditLog.Action.DOWNLOAD)
        assert logs.count() == 3
        assert {log.document_id for log in logs} == {d.pk for d in docs}
        details = logs.first().details
        assert details == {"export_type": "full_record_zip", "document_count": 3, "contract_number": "CONT-2026-042"}
        assert logs.first().performed_by.username == "analista"
        assert logs.first().ip_address == "10.7.7.7"

    def test_empty_record_exports_manifest_only(self, api_client, contract):
        response = api_client.get(f"{CONTRACTS}{contract.pk}/export-zip/")

        assert response.status_code == 200
        archive = read_zip(response)
        assert archive.namelist() == ["manifest.json"]
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["document_count"] == 0 and manifest["documents"] == []
        assert not AuditLog.objects.filter(action=AuditLog.Action.DOWNLOAD).exists()

    def test_documents_without_type_go_to_untyped_folder(self, contract):
        doc = make_doc("RAD-20260921-000701", contract, None, b"%PDF", original_filename="¿¿??.pdf")
        assert zip_entry_path(doc) == "SIN_TIPIFICAR/RAD-20260921-000701_.pdf" or zip_entry_path(doc).startswith("SIN_TIPIFICAR/RAD-20260921-000701_")

    def test_unknown_contract_and_anonymous_access(self, api_client, anonymous_client, contract):
        assert api_client.get(f"{CONTRACTS}9a1b2c3d-4e5f-6a7b-8c9d-0e1f2a3b4c5d/export-zip/").status_code == 404
        assert anonymous_client.get(f"{CONTRACTS}{contract.pk}/export-zip/").status_code == 401

    def test_contract_audit_trail_can_filter_by_action(self, api_client, contract, document_type):
        make_doc("RAD-20260921-000801", contract, document_type, b"%PDF")
        api_client.get(f"{CONTRACTS}{contract.pk}/export-zip/")

        trail = api_client.get(f"{CONTRACTS}{contract.pk}/audit-trail/", {"action": "DESCARGA"}).json()
        assert trail["count"] == 1
        assert trail["results"][0]["details"]["export_type"] == "full_record_zip"
        assert api_client.get(f"{CONTRACTS}{contract.pk}/audit-trail/", {"action": "CARGA"}).json()["count"] == 0
