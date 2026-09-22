"""Pruebas del sistema de alertas de vencimiento (Requerimiento Coltebienes #6)."""
from datetime import date, timedelta

import pytest
from django.utils import timezone

from apps.documents.models import AuditLog, Document
from apps.documents.services.expirations import (
    STAGE_CRITICAL,
    STAGE_EXPIRED,
    STAGE_WARNING,
    alert_stage,
    check_expiring_documents,
    days_to_expiration,
    expiring_documents_queryset,
)
from apps.documents.tasks import check_expiring_documents_task

TODAY = date(2026, 9, 21)


def make_doc(filing, expiration, status=Document.ProcessingStatus.PROCESSED, **kwargs):
    return Document.objects.create(
        filing_number=filing,
        file_path=f"x/{filing}.pdf",
        original_filename=f"{filing}.pdf",
        file_hash="e" * 64,
        file_size_bytes=10,
        processing_status=status,
        expiration_date=expiration,
        **kwargs,
    )


class TestAlertStage:
    @pytest.mark.parametrize(
        "delta_days, expected",
        [(-1, STAGE_EXPIRED), (0, STAGE_CRITICAL), (7, STAGE_CRITICAL), (8, STAGE_WARNING), (30, STAGE_WARNING), (31, None)],
    )
    def test_stage_thresholds(self, delta_days, expected):
        assert alert_stage(TODAY + timedelta(days=delta_days), today=TODAY, window_days=30) == expected

    def test_no_expiration_means_no_stage(self):
        assert alert_stage(None, today=TODAY) is None
        assert days_to_expiration(None) is None
        assert days_to_expiration(TODAY + timedelta(days=3), TODAY) == 3


@pytest.mark.django_db
class TestCheckExpiringDocuments:
    def test_creates_one_alert_per_document_and_stage(self, contract, document_type):
        expired = make_doc("RAD-20260920-000301", TODAY - timedelta(days=3), digital_record=contract.digital_record, document_type=document_type)
        critical = make_doc("RAD-20260920-000302", TODAY + timedelta(days=5))
        warning = make_doc("RAD-20260920-000303", TODAY + timedelta(days=25))
        make_doc("RAD-20260920-000304", TODAY + timedelta(days=90))                                   # fuera de ventana
        make_doc("RAD-20260920-000305", TODAY - timedelta(days=1), status=Document.ProcessingStatus.FAILED)  # descartado
        make_doc("RAD-20260920-000306", None)                                                          # sin vigencia

        summary = check_expiring_documents(today=TODAY)

        assert summary["checked"] == 3
        assert summary["alerts_created"] == 3
        assert (summary["expired"], summary["critical"], summary["warning"]) == (1, 1, 1)

        alert = expired.audit_logs.get(action=AuditLog.Action.EXPIRATION_ALERT)
        assert alert.details["stage"] == STAGE_EXPIRED
        assert alert.details["days_left"] == -3
        assert alert.details["contract_number"] == "CONT-2026-042"
        assert alert.details["client_email"] == "contacto@logandina.co"
        assert alert.details["client_phone"] == "+57 604 123 4567"
        assert alert.details["document_type"] == "POLIZA_CUMPLIMIENTO"
        assert critical.audit_logs.get(action=AuditLog.Action.EXPIRATION_ALERT).details["stage"] == STAGE_CRITICAL
        assert warning.audit_logs.get(action=AuditLog.Action.EXPIRATION_ALERT).details["stage"] == STAGE_WARNING

    def test_rerun_does_not_duplicate_alerts(self):
        make_doc("RAD-20260920-000310", TODAY + timedelta(days=10))

        first = check_expiring_documents(today=TODAY)
        second = check_expiring_documents(today=TODAY)

        assert first["alerts_created"] == 1
        assert second["alerts_created"] == 0
        assert AuditLog.objects.filter(action=AuditLog.Action.EXPIRATION_ALERT).count() == 1

    def test_new_alert_when_stage_escalates(self):
        doc = make_doc("RAD-20260920-000311", TODAY + timedelta(days=10))

        check_expiring_documents(today=TODAY)                       # warning
        check_expiring_documents(today=TODAY + timedelta(days=5))   # critical (5 días restantes)
        check_expiring_documents(today=TODAY + timedelta(days=6))   # sigue critical: sin nueva alerta
        check_expiring_documents(today=TODAY + timedelta(days=11))  # expired

        stages = list(
            doc.audit_logs.filter(action=AuditLog.Action.EXPIRATION_ALERT).order_by("timestamp").values_list("details__stage", flat=True)
        )
        assert sorted(stages) == sorted([STAGE_WARNING, STAGE_CRITICAL, STAGE_EXPIRED])

    def test_renewed_expiration_date_generates_fresh_alert(self):
        doc = make_doc("RAD-20260920-000312", TODAY + timedelta(days=10))
        check_expiring_documents(today=TODAY)

        doc.expiration_date = TODAY + timedelta(days=20)  # nueva vigencia registrada por el analista
        doc.save()
        assert check_expiring_documents(today=TODAY)["alerts_created"] == 1

    def test_queryset_orders_by_expiration_and_respects_window(self):
        make_doc("RAD-20260920-000320", TODAY + timedelta(days=20))
        make_doc("RAD-20260920-000321", TODAY - timedelta(days=2))
        make_doc("RAD-20260920-000322", TODAY + timedelta(days=2))

        numbers = list(expiring_documents_queryset(30, today=TODAY).values_list("filing_number", flat=True))
        assert numbers == ["RAD-20260920-000321", "RAD-20260920-000322", "RAD-20260920-000320"]
        assert list(expiring_documents_queryset(30, include_expired=False, today=TODAY).values_list("filing_number", flat=True)) == [
            "RAD-20260920-000322",
            "RAD-20260920-000320",
        ]

    def test_celery_task_returns_summary_and_is_scheduled(self, settings):
        make_doc("RAD-20260920-000330", timezone.localdate() + timedelta(days=3))

        result = check_expiring_documents_task.apply().result

        assert result["alerts_created"] == 1
        assert result["critical"] == 1
        entry = settings.CELERY_BEAT_SCHEDULE["check-expiring-documents"]
        assert entry["task"] == check_expiring_documents_task.name == "documents.check_expiring_documents"


@pytest.mark.django_db
class TestExpiringEndpoint:
    def test_lists_expiring_documents_with_stage_and_contact_data(self, api_client, contract, document_type):
        today = timezone.localdate()
        make_doc("RAD-20260920-000401", today + timedelta(days=3), digital_record=contract.digital_record, document_type=document_type)
        make_doc("RAD-20260920-000402", today - timedelta(days=4), digital_record=contract.digital_record)
        make_doc("RAD-20260920-000403", today + timedelta(days=60))

        body = api_client.get("/api/v1/documents/expiring/").json()

        assert body["days"] == 30
        assert body["count"] == 2
        assert body["expired"] == 1 and body["expiring_soon"] == 1
        first, second = body["results"]
        assert first["filing_number"] == "RAD-20260920-000402"
        assert first["expiration_stage"] == STAGE_EXPIRED
        assert first["days_to_expiration"] == -4
        assert second["expiration_stage"] == STAGE_CRITICAL
        assert second["days_to_expiration"] == 3
        assert second["client_email"] == "contacto@logandina.co"
        assert second["client_phone"] == "+57 604 123 4567"
        assert second["document_type"]["code"] == "POLIZA_CUMPLIMIENTO"

    def test_window_and_include_expired_parameters(self, api_client):
        today = timezone.localdate()
        make_doc("RAD-20260920-000410", today - timedelta(days=1))
        make_doc("RAD-20260920-000411", today + timedelta(days=50))

        assert api_client.get("/api/v1/documents/expiring/", {"days": 60}).json()["count"] == 2
        assert api_client.get("/api/v1/documents/expiring/", {"days": 60, "include_expired": "false"}).json()["count"] == 1
        assert api_client.get("/api/v1/documents/expiring/", {"days": "abc"}).status_code == 400

    def test_requires_authentication(self, anonymous_client):
        assert anonymous_client.get("/api/v1/documents/expiring/").status_code == 401
