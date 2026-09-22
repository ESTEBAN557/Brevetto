"""
Tareas Celery del módulo de documentos (US-009 / US-010).

`process_document_content_task` descarga el archivo del bucket, lo envía a Gemini,
aplica la regla Human-in-the-Loop y actualiza el estado del documento. Reintenta
ante fallos transitorios (red, cuota, JSON inválido) hasta `max_retries` veces.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from apps.documents.models import AuditLog, Document
from apps.documents.services.ai_extraction import AIConfigurationError, extract_document_metadata
from apps.documents.services.audit import log_action
from apps.documents.services.classification import apply_classification
from apps.documents.services.storage import get_file_bytes

logger = logging.getLogger(__name__)

RETRY_BASE_SECONDS = 30


@shared_task(
    bind=True,
    name="documents.process_document_content",
    max_retries=3,
    acks_late=True,
)
def process_document_content_task(self, document_id: str) -> dict:
    try:
        document = Document.objects.select_related("digital_record").get(pk=document_id)
    except Document.DoesNotExist:
        logger.warning("process_document_content: documento %s no existe; se descarta.", document_id)
        return {"document_id": str(document_id), "status": "NOT_FOUND"}

    document.processing_status = Document.ProcessingStatus.PROCESSING
    document.save(update_fields=["processing_status", "updated_at"])

    try:
        file_bytes = get_file_bytes(document.file_path)
        ai_data = extract_document_metadata(file_bytes, document.mime_type)
        status = apply_classification(document, ai_data)

    except AIConfigurationError as exc:
        # Sin IA disponible la filosofía HITL manda: el humano clasifica.
        logger.error("IA no configurada; %s enviado a revisión manual: %s", document.filing_number, exc)
        document.ai_extracted_data = {"error": str(exc)}
        document.ai_confidence_score = None
        document.processing_status = Document.ProcessingStatus.NEEDS_REVIEW
        document.save(update_fields=["ai_extracted_data", "ai_confidence_score", "processing_status", "updated_at"])
        log_action(
            document,
            AuditLog.Action.AI_CLASSIFY,
            details={"needs_human_validation": True, "reason": "ai_unavailable", "error": str(exc)},
        )
        status = document.processing_status

    except Exception as exc:
        retries = self.request.retries
        if retries >= self.max_retries:
            logger.exception("Fallo definitivo procesando %s tras %s reintentos", document.filing_number, retries)
            document.processing_status = Document.ProcessingStatus.FAILED
            document.save(update_fields=["processing_status", "updated_at"])
            log_action(
                document,
                AuditLog.Action.AI_CLASSIFY,
                details={
                    "failed": True,
                    "error": str(exc)[:1000],
                    "retries": retries,
                    "failed_at": timezone.now().isoformat(),
                },
            )
            raise
        countdown = RETRY_BASE_SECONDS * (retries + 1)
        logger.warning(
            "Error transitorio procesando %s (intento %s/%s), reintento en %ss: %s",
            document.filing_number, retries + 1, self.max_retries, countdown, exc,
        )
        raise self.retry(exc=exc, countdown=countdown)

    logger.info("Documento %s procesado -> %s", document.filing_number, status)
    return {
        "document_id": str(document.pk),
        "filing_number": document.filing_number,
        "status": status,
        "confidence": document.ai_confidence_score,
    }


@shared_task(name="documents.check_expiring_documents")
def check_expiring_documents_task(days: int | None = None) -> dict:
    """Alertas de vencimiento (Coltebienes #6): registra en AuditLog los documentos
    vencidos o por vencer en los próximos `days` días (30 por defecto), una vez por etapa."""
    from apps.documents.services.expirations import check_expiring_documents

    summary = check_expiring_documents(days)
    logger.info(
        "Vencimientos: %s revisados, %s alertas nuevas (vencidos=%s, críticos=%s, aviso=%s)",
        summary["checked"], summary["alerts_created"], summary["expired"], summary["critical"], summary["warning"],
    )
    return summary


@shared_task(name="documents.requeue_stale_documents")
def requeue_stale_documents_task(stale_after_minutes: int | None = None) -> dict:
    """Red de seguridad periódica (Celery beat).

    Si un worker muere a mitad de un análisis o se pierde un reintento con ETA,
    el documento quedaría en RECIBIDO/PROCESANDO indefinidamente. Esta tarea
    re-encola los que llevan más de `stale_after_minutes` sin cambios.
    """
    minutes = stale_after_minutes or int(getattr(settings, "PROCESSING_STALE_AFTER_MINUTES", 15))
    threshold = timezone.now() - timedelta(minutes=minutes)
    stale = list(
        Document.objects.filter(
            processing_status__in=[
                Document.ProcessingStatus.RECEIVED,
                Document.ProcessingStatus.PROCESSING,
            ],
            updated_at__lt=threshold,
        ).values_list("pk", "filing_number")
    )
    for pk, filing_number in stale:
        logger.warning("Documento %s estancado > %s min; re-encolando procesamiento.", filing_number, minutes)
        Document.objects.filter(pk=pk).update(updated_at=timezone.now())  # evita re-encolar en el siguiente ciclo
        process_document_content_task.delay(str(pk))
    return {"requeued": len(stale), "stale_after_minutes": minutes}
