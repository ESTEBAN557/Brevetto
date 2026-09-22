"""Pruebas del endpoint de métricas ejecutivas GET /api/v1/metrics/summary/."""
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.documents.models import AuditLog, Document
from apps.documents.services.audit import log_action

METRICS = "/api/v1/metrics/summary/"


def make_doc(filing, status, channel=Document.SourceChannel.DIGITAL_INTERNAL, **kwargs):
    return Document.objects.create(
        filing_number=filing,
        file_path=f"x/{filing}.pdf",
        original_filename=f"{filing}.pdf",
        file_hash="9" * 64,
        file_size_bytes=10,
        processing_status=status,
        source_channel=channel,
        **kwargs,
    )


@pytest.fixture
def metrics_dataset(contract, document_type, user, settings):
    settings.MANUAL_MINUTES_PER_DOCUMENT = 8
    today = timezone.localdate()
    auto_1 = make_doc("RAD-20260921-000901", Document.ProcessingStatus.PROCESSED, digital_record=contract.digital_record, document_type=document_type, ai_confidence_score=0.95, expiration_date=today + timedelta(days=5))
    auto_2 = make_doc("RAD-20260921-000902", Document.ProcessingStatus.PROCESSED, Document.SourceChannel.EMAIL, digital_record=contract.digital_record, ai_confidence_score=0.9)
    reviewed = make_doc("RAD-20260921-000903", Document.ProcessingStatus.PROCESSED, Document.SourceChannel.WEB_PORTAL, digital_record=contract.digital_record, ai_confidence_score=0.5)
    pending = make_doc("RAD-20260921-000904", Document.ProcessingStatus.NEEDS_REVIEW, Document.SourceChannel.PHYSICAL, ai_confidence_score=0.4)

    for doc in (auto_1, auto_2, reviewed, pending):
        log_action(doc, AuditLog.Action.UPLOAD, user=user)
    log_action(auto_1, AuditLog.Action.AI_CLASSIFY, details={"confidence": 0.95, "auto_associated": True})
    log_action(auto_2, AuditLog.Action.AI_CLASSIFY, details={"confidence": 0.9, "auto_associated": True})
    log_action(reviewed, AuditLog.Action.AI_CLASSIFY, details={"confidence": 0.5, "needs_human_validation": True})
    log_action(pending, AuditLog.Action.AI_CLASSIFY, details={"confidence": 0.4, "needs_human_validation": True})
    log_action(reviewed, AuditLog.Action.HUMAN_VALIDATE, user=user)
    # Un analista corrigió el tipo documental de un documento auto-clasificado: error de la IA.
    log_action(auto_2, AuditLog.Action.METADATA_UPDATE, user=user, details={"changes": {"document_type": {"before": "FACTURA", "after": "CUENTA_COBRO"}}})
    log_action(auto_1, AuditLog.Action.VIEW, user=user)
    return {"auto": [auto_1, auto_2], "reviewed": reviewed, "pending": pending}


@pytest.mark.django_db
class TestMetricsSummary:
    def test_summary_structure_and_document_counts(self, api_client, metrics_dataset):
        body = api_client.get(METRICS).json()

        assert set(body) == {"generated_at", "period_days", "documents", "ai", "processing", "expirations", "contracts", "audit"}
        docs = body["documents"]
        assert docs["total"] == 4
        assert docs["processed"] == 3
        assert docs["pending_review"] == 1
        assert docs["filed_in_period"] == 4 and docs["filed_last_24h"] == 4
        assert docs["portal_submissions"] == 1

        by_status = {row["alias"]: row for row in docs["by_status"]}
        assert by_status["CLASSIFIED"]["count"] == 3 and by_status["CLASSIFIED"]["code"] == "PROCESADO"
        assert by_status["NEEDS_REVIEW"]["count"] == 1
        assert by_status["FAILED"]["count"] == 0

        by_channel = {row["code"]: row["count"] for row in docs["by_channel"]}
        assert by_channel == {"FISICO_ESCANEADO": 1, "DIGITAL_INTERNO": 1, "PORTAL_WEB": 1, "CORREO": 1}
        assert docs["by_category"] == [{"category": "POLIZA", "count": 1}]

    def test_ai_automation_and_accuracy_rates(self, api_client, metrics_dataset):
        ai = api_client.get(METRICS).json()["ai"]

        assert ai["documents_analyzed"] == 4
        assert ai["auto_classified"] == 2
        assert ai["sent_to_review"] == 2
        assert ai["human_validated"] == 1
        assert ai["auto_corrected_by_staff"] == 1
        assert ai["automation_rate"] == 0.5
        assert ai["accuracy_rate"] == 0.5
        assert ai["average_confidence"] == round((0.95 + 0.9 + 0.5 + 0.4) / 4, 4)
        assert ai["confidence_threshold"] == 0.85

    def test_processing_and_savings_estimates(self, api_client, metrics_dataset):
        processing = api_client.get(METRICS).json()["processing"]

        assert processing["average_seconds_to_classification"] is not None
        assert processing["average_seconds_to_classification"] >= 0
        assert processing["manual_minutes_per_document_assumption"] == 8
        assert processing["estimated_minutes_saved"] == 16
        assert processing["estimated_hours_saved"] == 0.3

    def test_expirations_contracts_and_audit_blocks(self, api_client, metrics_dataset):
        body = api_client.get(METRICS).json()

        assert body["expirations"]["total"] == 1
        assert body["expirations"]["critical_7_days"] == 1
        assert body["expirations"]["expired"] == 0
        assert body["contracts"] == {"total": 1, "active": 1, "with_documents": 1}
        assert body["audit"]["total_events"] == AuditLog.objects.count() == 11
        assert body["audit"]["views_and_downloads"] == 1

    def test_period_parameter_is_validated_and_clamped(self, api_client, metrics_dataset):
        assert api_client.get(METRICS, {"days": 7}).json()["period_days"] == 7
        assert api_client.get(METRICS, {"days": 9999}).json()["period_days"] == 365
        assert api_client.get(METRICS, {"days": "x"}).status_code == 400

    def test_empty_database_returns_zeros_without_errors(self, api_client):
        body = api_client.get(METRICS).json()

        assert body["documents"]["total"] == 0
        assert body["ai"]["automation_rate"] is None and body["ai"]["accuracy_rate"] is None
        assert body["processing"]["average_seconds_to_classification"] is None
        assert body["processing"]["estimated_hours_saved"] == 0.0
        assert body["expirations"]["total"] == 0

    def test_requires_authentication(self, anonymous_client):
        assert anonymous_client.get(METRICS).status_code == 401
