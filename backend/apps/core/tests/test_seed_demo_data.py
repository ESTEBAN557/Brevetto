"""Pruebas del comando `seed_demo_data` (datos de demostración idempotentes)."""
from io import StringIO

import pytest
from django.contrib.auth import authenticate
from django.core.files.storage import default_storage
from django.core.management import call_command

from apps.core.models import Client, Contract, DigitalRecord
from apps.documents.models import AuditLog, Document, FilingSequence


def run_seed(**options):
    out = StringIO()
    call_command("seed_demo_data", stdout=out, **options)
    return out.getvalue()


@pytest.mark.django_db
class TestSeedDemoData:
    def test_creates_demo_dataset(self):
        output = run_seed()

        assert Client.objects.count() == 3
        assert Contract.objects.filter(status=Contract.ContractStatus.ACTIVE).count() == 3
        assert DigitalRecord.objects.count() == 3
        assert Document.objects.count() == 5
        assert "Clientes:      3" in output

        statuses = sorted(Document.objects.values_list("processing_status", flat=True))
        assert statuses == ["PROCESADO", "PROCESADO", "PROCESADO", "REQUIERE_REVISION", "REQUIERE_REVISION"]

        # Todos los documentos tienen PDF real en el bucket y checksum coherente
        for doc in Document.objects.all():
            assert default_storage.exists(doc.file_path)
            assert default_storage.size(doc.file_path) == doc.file_size_bytes
            assert len(doc.file_hash) == 64
            assert doc.filing_number.startswith("RAD-")

        # Expedientes provisionados en el storage
        for record in DigitalRecord.objects.all():
            assert default_storage.exists(f"{record.storage_path}.expediente.json")

    def test_processed_documents_are_filed_and_review_documents_are_in_inbox(self):
        run_seed()

        processed = Document.objects.filter(processing_status=Document.ProcessingStatus.PROCESSED)
        assert all(doc.digital_record is not None and doc.document_type is not None for doc in processed)
        assert set(processed.values_list("document_type__code", flat=True)) == {"POLIZA_CUMPLIMIENTO", "FACTURA", "CAMARA_COMERCIO"}

        review = Document.objects.filter(processing_status=Document.ProcessingStatus.NEEDS_REVIEW)
        assert review.count() == 2
        assert review.filter(digital_record__isnull=True).count() == 2
        reasons = {doc.ai_extracted_data.get("contract_number") for doc in review}
        assert reasons == {None, "CONT-2019-555"}
        portal_doc = review.get(source_channel=Document.SourceChannel.WEB_PORTAL)
        assert portal_doc.external_sender_name == "Carolina Restrepo"
        assert portal_doc.registered_by is None

    def test_expiring_documents_and_alerts_are_ready_for_demo(self, api_client):
        run_seed()

        expiring = api_client.get("/api/v1/documents/expiring/").json()
        assert expiring["count"] == 2
        assert expiring["expired"] == 1 and expiring["expiring_soon"] == 1
        stages = {item["expiration_stage"] for item in expiring["results"]}
        assert stages == {"expired", "warning"}

        alerts = AuditLog.objects.filter(action=AuditLog.Action.EXPIRATION_ALERT)
        assert alerts.count() == 2
        assert AuditLog.objects.filter(action=AuditLog.Action.UPLOAD).count() == 5
        assert AuditLog.objects.filter(action=AuditLog.Action.AI_CLASSIFY).count() == 5

    def test_is_idempotent(self):
        first = run_seed()
        filing_numbers = set(Document.objects.values_list("filing_number", flat=True))
        sequence_after_first = FilingSequence.objects.get().last_number

        second = run_seed()

        assert Client.objects.count() == 3
        assert Contract.objects.count() == 3
        assert Document.objects.count() == 5
        assert set(Document.objects.values_list("filing_number", flat=True)) == filing_numbers
        assert FilingSequence.objects.get().last_number == sequence_after_first
        assert AuditLog.objects.filter(action=AuditLog.Action.EXPIRATION_ALERT).count() == 2
        assert "Creados: 0" in second.splitlines()[-1] or "Reutilizados: 12" in second
        assert "Creados: 12" in first

    def test_demo_user_can_log_in_with_given_password(self):
        run_seed(password="clave-demo-123")

        user = authenticate(username="demo", password="clave-demo-123")
        assert user is not None and user.is_staff

    def test_skip_alerts_flag(self):
        run_seed(skip_alerts=True)
        assert not AuditLog.objects.filter(action=AuditLog.Action.EXPIRATION_ALERT).exists()
