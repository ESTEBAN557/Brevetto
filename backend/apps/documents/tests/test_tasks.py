"""
Pruebas del pipeline de IA (US-009): tarea Celery, regla HITL y adaptador Gemini.

Gemini se simula con mocks: nunca se realizan llamadas de red.
"""
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from apps.core.models import Contract
from apps.documents.models import AuditLog, Document
from apps.documents.services.ai_extraction import (
    AIConfigurationError,
    AIExtractionError,
    GeminiExtractor,
    normalize_extraction,
    parse_model_json,
)
from apps.documents.services.classification import apply_classification, resolve_contract
from apps.documents.tasks import process_document_content_task

EXTRACT_PATH = "apps.documents.tasks.extract_document_metadata"


def ai_payload(**overrides):
    data = {
        "contract_number": "CONT-2026-042",
        "client_identification": "9001234561",
        "client_name": "Logística Andina S.A.S.",
        "document_type": "POLIZA",
        "document_date": "2026-01-10",
        "expiration_date": "2027-01-15",
        "extracted_text_summary": "Póliza de cumplimiento del contrato de arrendamiento.",
        "confidence_score": 0.93,
    }
    data.update(overrides)
    return data


@pytest.fixture
def stored_document(document):
    saved = default_storage.save(document.file_path, ContentFile(b"%PDF-1.4 contenido de prueba"))
    assert saved == document.file_path
    return document


# ------------------------------------------------------------- tarea Celery --
@pytest.mark.django_db
class TestProcessDocumentContentTask:
    def test_high_confidence_with_known_contract_is_auto_classified(self, stored_document, contract):
        with patch(EXTRACT_PATH, return_value=ai_payload()) as extract:
            result = process_document_content_task.apply(args=[str(stored_document.pk)])

        assert result.successful(), result.result
        extract.assert_called_once()
        _, mime = extract.call_args.args
        assert mime == "application/pdf"

        stored_document.refresh_from_db()
        assert stored_document.processing_status == Document.ProcessingStatus.PROCESSED
        assert stored_document.digital_record == contract.digital_record
        assert stored_document.document_type.code == "POLIZA_CUMPLIMIENTO"
        assert stored_document.ai_confidence_score == 0.93
        assert stored_document.expiration_date == date(2027, 1, 15)
        assert stored_document.document_date == date(2026, 1, 10)
        assert stored_document.ai_extracted_data["extracted_text_summary"].startswith("Póliza")

        log = stored_document.audit_logs.get(action=AuditLog.Action.AI_CLASSIFY)
        assert log.details["auto_associated"] is True
        assert log.details["confidence"] == 0.93
        assert log.details["contract_resolution"] == "contract_number"
        assert result.result["status"] == "PROCESADO"

    def test_low_confidence_goes_to_human_review(self, stored_document, contract):
        with patch(EXTRACT_PATH, return_value=ai_payload(confidence_score=0.6)):
            result = process_document_content_task.apply(args=[str(stored_document.pk)])

        assert result.successful()
        stored_document.refresh_from_db()
        assert stored_document.processing_status == Document.ProcessingStatus.NEEDS_REVIEW
        assert stored_document.digital_record is None
        assert stored_document.document_type is None
        assert stored_document.ai_confidence_score == 0.6
        assert stored_document.ai_extracted_data["contract_number"] == "CONT-2026-042"

        log = stored_document.audit_logs.get(action=AuditLog.Action.AI_CLASSIFY)
        assert log.details["needs_human_validation"] is True
        assert log.details["reason"] == "low_confidence"
        assert log.details["suggested_contract_number"] == "CONT-2026-042"
        assert log.details["suggested_document_type"] == "POLIZA_CUMPLIMIENTO"

    def test_threshold_is_inclusive(self, stored_document, contract):
        with patch(EXTRACT_PATH, return_value=ai_payload(confidence_score=0.85)):
            process_document_content_task.apply(args=[str(stored_document.pk)])

        stored_document.refresh_from_db()
        assert stored_document.processing_status == Document.ProcessingStatus.PROCESSED

    def test_high_confidence_but_unknown_contract_goes_to_review(self, stored_document, contract):
        with patch(EXTRACT_PATH, return_value=ai_payload(contract_number="CONT-9999-001", client_identification=None)):
            process_document_content_task.apply(args=[str(stored_document.pk)])

        stored_document.refresh_from_db()
        assert stored_document.processing_status == Document.ProcessingStatus.NEEDS_REVIEW
        log = stored_document.audit_logs.get(action=AuditLog.Action.AI_CLASSIFY)
        assert log.details["reason"] == "contract_not_found"
        assert log.details["contract_resolution"] == "none"

    def test_contract_resolved_by_client_identification(self, stored_document, contract):
        payload = ai_payload(contract_number=None, client_identification="900.123.456-1")
        with patch(EXTRACT_PATH, return_value=payload):
            process_document_content_task.apply(args=[str(stored_document.pk)])

        stored_document.refresh_from_db()
        assert stored_document.processing_status == Document.ProcessingStatus.PROCESSED
        assert stored_document.digital_record == contract.digital_record
        log = stored_document.audit_logs.get(action=AuditLog.Action.AI_CLASSIFY)
        assert log.details["contract_resolution"] == "client_identification"

    def test_ambiguous_client_with_several_active_contracts_goes_to_review(self, stored_document, contract, tenant):
        Contract.objects.create(
            contract_number="CONT-2026-043",
            client=tenant,
            property_address="Bodega 13",
            start_date=date(2026, 2, 1),
            end_date=date(2027, 1, 31),
        )
        with patch(EXTRACT_PATH, return_value=ai_payload(contract_number=None)):
            process_document_content_task.apply(args=[str(stored_document.pk)])

        stored_document.refresh_from_db()
        assert stored_document.processing_status == Document.ProcessingStatus.NEEDS_REVIEW
        log = stored_document.audit_logs.get(action=AuditLog.Action.AI_CLASSIFY)
        assert log.details["reason"] == "ambiguous_contract"
        assert log.details["candidate_contracts"] == 2

    def test_status_is_processing_while_model_runs(self, stored_document, contract):
        observed = {}

        def fake_extract(file_bytes, mime_type):
            observed["status"] = Document.objects.get(pk=stored_document.pk).processing_status
            observed["bytes"] = file_bytes
            return ai_payload()

        with patch(EXTRACT_PATH, side_effect=fake_extract):
            process_document_content_task.apply(args=[str(stored_document.pk)])

        assert observed["status"] == Document.ProcessingStatus.PROCESSING
        assert observed["bytes"].startswith(b"%PDF-1.4")

    def test_ai_not_configured_sends_document_to_review_without_failing(self, stored_document):
        with patch(EXTRACT_PATH, side_effect=AIConfigurationError("GEMINI_API_KEY no está configurada.")):
            result = process_document_content_task.apply(args=[str(stored_document.pk)])

        assert result.successful()
        stored_document.refresh_from_db()
        assert stored_document.processing_status == Document.ProcessingStatus.NEEDS_REVIEW
        assert "GEMINI_API_KEY" in stored_document.ai_extracted_data["error"]
        log = stored_document.audit_logs.get(action=AuditLog.Action.AI_CLASSIFY)
        assert log.details["reason"] == "ai_unavailable"

    def test_transient_error_is_retried_and_then_succeeds(self, stored_document, contract):
        with patch(EXTRACT_PATH, side_effect=[AIExtractionError("timeout"), ai_payload()]) as extract:
            result = process_document_content_task.apply(args=[str(stored_document.pk)])

        assert result.successful(), result.result
        assert extract.call_count == 2
        stored_document.refresh_from_db()
        assert stored_document.processing_status == Document.ProcessingStatus.PROCESSED

    def test_persistent_error_marks_document_failed_after_max_retries(self, stored_document):
        with patch(EXTRACT_PATH, side_effect=AIExtractionError("Gemini 503")) as extract:
            result = process_document_content_task.apply(args=[str(stored_document.pk)])

        assert result.failed()
        assert extract.call_count == process_document_content_task.max_retries + 1
        stored_document.refresh_from_db()
        assert stored_document.processing_status == Document.ProcessingStatus.FAILED
        log = stored_document.audit_logs.get(action=AuditLog.Action.AI_CLASSIFY)
        assert log.details["failed"] is True
        assert log.details["retries"] == process_document_content_task.max_retries
        assert "Gemini 503" in log.details["error"]

    def test_unknown_document_is_discarded_gracefully(self):
        result = process_document_content_task.apply(args=[str(uuid4())])

        assert result.successful()
        assert result.result["status"] == "NOT_FOUND"

    def test_task_is_registered_with_stable_name(self):
        assert process_document_content_task.name == "documents.process_document_content"
        assert process_document_content_task.max_retries == 3


# ----------------------------------------------------------- clasificación --
@pytest.mark.django_db
class TestClassificationService:
    def test_resolve_contract_is_case_insensitive(self, contract):
        resolution = resolve_contract({"contract_number": "cont-2026-042"})
        assert resolution.contract == contract
        assert resolution.method == "contract_number"

    def test_short_identifications_are_ignored(self, contract):
        resolution = resolve_contract({"contract_number": None, "client_identification": "123"})
        assert resolution.contract is None
        assert resolution.method == "none"

    def test_terminated_contracts_are_not_matched_by_identification(self, contract):
        contract.status = Contract.ContractStatus.TERMINATED
        contract.save()
        resolution = resolve_contract({"client_identification": "900123456"})
        assert resolution.contract is None

    def test_apply_classification_keeps_existing_dates_when_ai_has_none(self, document, contract):
        document.document_date = date(2026, 3, 3)
        document.save()

        status = apply_classification(
            document, ai_payload(document_date=None, expiration_date=None, document_type="OTRO")
        )

        assert status == Document.ProcessingStatus.PROCESSED
        document.refresh_from_db()
        assert document.document_date == date(2026, 3, 3)
        assert document.expiration_date is None
        assert document.document_type.code == "OTRO"


# ---------------------------------------------------------- adaptador Gemini --
class TestAIExtractionParsing:
    def test_parse_accepts_markdown_fences(self):
        assert parse_model_json('```json\n{"document_type": "FACTURA"}\n```') == {"document_type": "FACTURA"}

    def test_parse_rejects_invalid_json_and_non_objects(self):
        with pytest.raises(AIExtractionError):
            parse_model_json("no soy json")
        with pytest.raises(AIExtractionError):
            parse_model_json("[1, 2, 3]")
        with pytest.raises(AIExtractionError):
            parse_model_json("")

    def test_normalize_clamps_confidence_and_defaults_type(self):
        data = normalize_extraction({"confidence_score": "1.7", "document_type": "recibo", "contract_number": "null"})
        assert data["confidence_score"] == 1.0
        assert data["document_type"] == "OTRO"
        assert data["contract_number"] is None
        assert data["extracted_text_summary"] == ""

        assert normalize_extraction({"confidence_score": "abc"})["confidence_score"] == 0.0
        assert normalize_extraction(None)["document_type"] == "OTRO"


class TestGeminiExtractor:
    def test_requires_api_key(self, settings):
        settings.GEMINI_API_KEY = ""
        extractor = GeminiExtractor()
        assert extractor.is_configured is False
        with pytest.raises(AIConfigurationError):
            extractor.extract(b"%PDF", "application/pdf")

    def test_calls_sdk_with_structured_json_config(self, settings):
        settings.GEMINI_API_KEY = "test-key"
        settings.GEMINI_MODEL = "gemini-1.5-flash"
        fake_client = MagicMock()
        fake_client.models.generate_content.return_value = SimpleNamespace(
            text='{"document_type": "FACTURA", "confidence_score": 0.91, "contract_number": "CONT-1", '
            '"extracted_text_summary": "Factura de septiembre"}'
        )

        with patch("google.genai.Client", return_value=fake_client) as client_cls:
            data = GeminiExtractor().extract(b"%PDF-1.4", "application/pdf")

        client_cls.assert_called_once_with(api_key="test-key")
        kwargs = fake_client.models.generate_content.call_args.kwargs
        assert kwargs["model"] == "gemini-1.5-flash"
        assert kwargs["config"].response_mime_type == "application/json"
        assert kwargs["config"].temperature == 0.0
        assert len(kwargs["contents"]) == 2
        assert data["document_type"] == "FACTURA"
        assert data["confidence_score"] == 0.91
        assert data["client_identification"] is None

    def test_sdk_errors_are_wrapped_as_retryable(self, settings):
        settings.GEMINI_API_KEY = "test-key"
        settings.GEMINI_FALLBACK_MODEL = ""
        fake_client = MagicMock()
        fake_client.models.generate_content.side_effect = RuntimeError("503 Service Unavailable")

        with patch("google.genai.Client", return_value=fake_client):
            with pytest.raises(AIExtractionError, match="503"):
                GeminiExtractor().extract(b"%PDF-1.4", "application/pdf")
        assert fake_client.models.generate_content.call_count == 1

    def test_saturated_primary_model_falls_back_once(self, settings):
        settings.GEMINI_API_KEY = "test-key"
        settings.GEMINI_MODEL = "gemini-3.5-flash"
        settings.GEMINI_FALLBACK_MODEL = "gemini-3-flash-preview"
        fake_client = MagicMock()
        fake_client.models.generate_content.side_effect = [
            RuntimeError("503 UNAVAILABLE: This model is currently experiencing high demand"),
            SimpleNamespace(text='{"document_type": "POLIZA", "confidence_score": 0.9, "extracted_text_summary": "ok"}'),
        ]

        with patch("google.genai.Client", return_value=fake_client):
            data = GeminiExtractor().extract(b"%PDF-1.4", "application/pdf")

        models_called = [call.kwargs["model"] for call in fake_client.models.generate_content.call_args_list]
        assert models_called == ["gemini-3.5-flash", "gemini-3-flash-preview"]
        assert data["document_type"] == "POLIZA"
        assert data["model_used"] == "gemini-3-flash-preview"

    def test_non_transient_errors_do_not_trigger_fallback(self, settings):
        settings.GEMINI_API_KEY = "test-key"
        settings.GEMINI_FALLBACK_MODEL = "gemini-3-flash-preview"
        fake_client = MagicMock()
        fake_client.models.generate_content.side_effect = RuntimeError("400 INVALID_ARGUMENT: bad mime type")

        with patch("google.genai.Client", return_value=fake_client):
            with pytest.raises(AIExtractionError, match="INVALID_ARGUMENT"):
                GeminiExtractor().extract(b"%PDF-1.4", "application/pdf")
        assert fake_client.models.generate_content.call_count == 1

    def test_fallback_failure_surfaces_primary_error(self, settings):
        settings.GEMINI_API_KEY = "test-key"
        settings.GEMINI_FALLBACK_MODEL = "gemini-3-flash-preview"
        fake_client = MagicMock()
        fake_client.models.generate_content.side_effect = [
            RuntimeError("503 UNAVAILABLE primary"),
            RuntimeError("503 UNAVAILABLE fallback"),
        ]

        with patch("google.genai.Client", return_value=fake_client):
            with pytest.raises(AIExtractionError, match="primary"):
                GeminiExtractor().extract(b"%PDF-1.4", "application/pdf")
        assert fake_client.models.generate_content.call_count == 2
