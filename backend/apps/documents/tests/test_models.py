"""Pruebas de los modelos Document y AuditLog (inmutabilidad append-only)."""
import pytest
from django.db import DatabaseError, connection, transaction

from apps.documents.models import AuditLog, AuditLogImmutableError, Document


@pytest.mark.django_db
class TestDocument:
    def test_new_document_starts_in_received_status(self, document):
        assert document.processing_status == Document.ProcessingStatus.RECEIVED
        assert document.needs_human_review is False
        assert document.ai_extracted_data == {}
        assert document.ai_confidence_score is None

    def test_str_shows_filing_number_and_filename(self, document):
        assert str(document) == "RAD-20260920-000001 - cuenta_cobro_sep.pdf"

    def test_filing_number_is_unique(self, document, user):
        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            Document.objects.create(
                filing_number=document.filing_number,
                file_path="otro.pdf",
                original_filename="otro.pdf",
                file_hash="b" * 64,
                file_size_bytes=10,
                registered_by=user,
            )

    def test_document_can_be_linked_to_contract_digital_record(self, document, contract, document_type):
        document.digital_record = contract.digital_record
        document.document_type = document_type
        document.processing_status = Document.ProcessingStatus.PROCESSED
        document.save()

        document.refresh_from_db()
        assert document.digital_record.contract == contract
        assert contract.digital_record.documents.count() == 1
        assert document.document_type.code == "POLIZA_CUMPLIMIENTO"

    def test_needs_human_review_flag(self, document):
        document.processing_status = Document.ProcessingStatus.NEEDS_REVIEW
        assert document.needs_human_review is True


@pytest.mark.django_db
class TestAuditLogImmutability:
    def _create_log(self, document, user):
        return AuditLog.objects.create(
            document=document,
            action=AuditLog.Action.UPLOAD,
            performed_by=user,
            ip_address="10.0.0.15",
            user_agent="pytest",
            details={"filing_number": document.filing_number},
        )

    def test_insert_is_allowed(self, document, user):
        log = self._create_log(document, user)

        assert AuditLog.objects.filter(document=document).count() == 1
        assert log.timestamp is not None
        assert document.audit_logs.first() == log

    def test_orm_update_on_instance_is_rejected(self, document, user):
        log = self._create_log(document, user)
        log.action = AuditLog.Action.DOWNLOAD

        with pytest.raises(AuditLogImmutableError):
            log.save()

    def test_orm_delete_on_instance_is_rejected(self, document, user):
        log = self._create_log(document, user)

        with pytest.raises(AuditLogImmutableError):
            log.delete()
        assert AuditLog.objects.filter(pk=log.pk).exists()

    def test_queryset_update_is_rejected(self, document, user):
        self._create_log(document, user)

        with pytest.raises(AuditLogImmutableError):
            AuditLog.objects.filter(document=document).update(action=AuditLog.Action.VIEW)

    def test_queryset_delete_is_rejected(self, document, user):
        self._create_log(document, user)

        with pytest.raises(AuditLogImmutableError):
            AuditLog.objects.all().delete()

    def test_database_trigger_blocks_raw_update(self, document, user):
        """Incluso saltándose el ORM, PostgreSQL rechaza el UPDATE."""
        log = self._create_log(document, user)

        with pytest.raises(DatabaseError), transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE documents_auditlog SET action = %s WHERE id = %s",
                    [AuditLog.Action.DOWNLOAD, str(log.pk)],
                )

        log.refresh_from_db()
        assert log.action == AuditLog.Action.UPLOAD

    def test_database_trigger_blocks_raw_delete(self, document, user):
        log = self._create_log(document, user)

        with pytest.raises(DatabaseError), transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM documents_auditlog WHERE id = %s", [str(log.pk)])

        assert AuditLog.objects.filter(pk=log.pk).exists()

    def test_document_with_audit_trail_cannot_be_hard_deleted(self, document, user):
        """El borrado en cascada intentaría eliminar la bitácora y la BD lo impide."""
        self._create_log(document, user)

        with pytest.raises(DatabaseError), transaction.atomic():
            document.delete()

        assert Document.objects.filter(pk=document.pk).exists()
