"""
Métricas ejecutivas de gestión documental (KPIs de Coltebienes).

Todo se calcula con agregaciones sobre PostgreSQL; el único recorrido en Python
es el cálculo del tiempo promedio de clasificación sobre una muestra reciente.
"""
from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.db.models import Avg, Count, Min, Q
from django.utils import timezone

from apps.core.models import Contract
from apps.documents.models import AuditLog, Document
from apps.documents.services.expirations import alert_window_days, expiring_documents_queryset

# Equivalencia de estados internos con la nomenclatura del backlog.
STATUS_ALIASES = {
    "RECIBIDO": "RECEIVED",
    "PROCESANDO": "PROCESSING",
    "REQUIERE_REVISION": "NEEDS_REVIEW",
    "PROCESADO": "CLASSIFIED",
    "FALLIDO": "FAILED",
}

PROCESSING_SAMPLE_SIZE = 500


def manual_minutes_per_document() -> int:
    """Supuesto de negocio: minutos que tomaba radicar y clasificar un anexo a mano."""
    return int(getattr(settings, "MANUAL_MINUTES_PER_DOCUMENT", 8))


def _status_breakdown() -> list[dict]:
    counts = dict(Document.objects.values_list("processing_status").annotate(total=Count("id")).values_list("processing_status", "total"))
    return [
        {
            "code": status.value,
            "alias": STATUS_ALIASES.get(status.value, status.value),
            "label": status.label,
            "count": counts.get(status.value, 0),
        }
        for status in Document.ProcessingStatus
    ]


def _channel_breakdown() -> list[dict]:
    counts = dict(Document.objects.values_list("source_channel").annotate(total=Count("id")).values_list("source_channel", "total"))
    return [
        {"code": channel.value, "label": channel.label, "count": counts.get(channel.value, 0)}
        for channel in Document.SourceChannel
    ]


def _category_breakdown() -> list[dict]:
    rows = (
        Document.objects.filter(document_type__isnull=False)
        .values("document_type__category")
        .annotate(total=Count("id"))
        .order_by("-total")
    )
    return [{"category": row["document_type__category"], "count": row["total"]} for row in rows]


def _ai_metrics() -> dict:
    auto_ids = set(
        AuditLog.objects.filter(action=AuditLog.Action.AI_CLASSIFY, details__auto_associated=True)
        .values_list("document_id", flat=True)
        .distinct()
    )
    review_ids = set(
        AuditLog.objects.filter(action=AuditLog.Action.AI_CLASSIFY, details__needs_human_validation=True)
        .values_list("document_id", flat=True)
        .distinct()
    )
    human_validated_ids = set(
        AuditLog.objects.filter(action=AuditLog.Action.HUMAN_VALIDATE).values_list("document_id", flat=True).distinct()
    )
    # Auto-clasificados a los que un analista luego cambió el tipo documental: corrección de la IA.
    corrected_ids = set(
        AuditLog.objects.filter(
            action=AuditLog.Action.METADATA_UPDATE,
            document_id__in=auto_ids,
            details__changes__has_key="document_type",
        ).values_list("document_id", flat=True)
    ) if auto_ids else set()

    analyzed = len(auto_ids | review_ids)
    auto = len(auto_ids)
    corrected = len(corrected_ids)
    confidence = Document.objects.filter(ai_confidence_score__isnull=False).aggregate(avg=Avg("ai_confidence_score"))["avg"]

    return {
        "documents_analyzed": analyzed,
        "auto_classified": auto,
        "sent_to_review": len(review_ids),
        "human_validated": len(human_validated_ids),
        "auto_corrected_by_staff": corrected,
        "automation_rate": round(auto / analyzed, 4) if analyzed else None,
        "accuracy_rate": round((auto - corrected) / auto, 4) if auto else None,
        "average_confidence": round(float(confidence), 4) if confidence is not None else None,
        "confidence_threshold": float(getattr(settings, "AI_CONFIDENCE_THRESHOLD", 0.85)),
    }


def _average_processing_seconds() -> float | None:
    """Promedio entre la radicación y la primera clasificación IA (muestra reciente)."""
    rows = (
        AuditLog.objects.filter(action=AuditLog.Action.AI_CLASSIFY)
        .values("document_id", "document__created_at")
        .annotate(first_classification=Min("timestamp"))
        .order_by("-first_classification")[:PROCESSING_SAMPLE_SIZE]
    )
    durations = [
        (row["first_classification"] - row["document__created_at"]).total_seconds()
        for row in rows
        if row["first_classification"] and row["document__created_at"]
    ]
    durations = [d for d in durations if d >= 0]
    return round(sum(durations) / len(durations), 1) if durations else None


def _expiration_metrics() -> dict:
    today = timezone.localdate()
    window = alert_window_days()
    queryset = expiring_documents_queryset(window, include_expired=True, today=today)
    expired = queryset.filter(expiration_date__lt=today).count()
    critical = queryset.filter(expiration_date__gte=today, expiration_date__lte=today + timedelta(days=7)).count()
    total = queryset.count()
    return {
        "window_days": window,
        "total": total,
        "expired": expired,
        "critical_7_days": critical,
        "warning": total - expired - critical,
        "alerts_emitted": AuditLog.objects.filter(action=AuditLog.Action.EXPIRATION_ALERT).count(),
    }


def summary(period_days: int = 30) -> dict:
    now = timezone.now()
    since = now - timedelta(days=period_days)
    total = Document.objects.count()
    processed = Document.objects.filter(processing_status=Document.ProcessingStatus.PROCESSED).count()
    pending_review = Document.objects.filter(processing_status=Document.ProcessingStatus.NEEDS_REVIEW).count()
    ai = _ai_metrics()
    minutes_saved = ai["auto_classified"] * manual_minutes_per_document()

    return {
        "generated_at": now.isoformat(),
        "period_days": period_days,
        "documents": {
            "total": total,
            "processed": processed,
            "pending_review": pending_review,
            "filed_in_period": Document.objects.filter(created_at__gte=since).count(),
            "filed_last_24h": Document.objects.filter(created_at__gte=now - timedelta(hours=24)).count(),
            "portal_submissions": Document.objects.filter(source_channel=Document.SourceChannel.WEB_PORTAL).count(),
            "by_status": _status_breakdown(),
            "by_channel": _channel_breakdown(),
            "by_category": _category_breakdown(),
        },
        "ai": ai,
        "processing": {
            "average_seconds_to_classification": _average_processing_seconds(),
            "manual_minutes_per_document_assumption": manual_minutes_per_document(),
            "estimated_minutes_saved": minutes_saved,
            "estimated_hours_saved": round(minutes_saved / 60, 1),
        },
        "expirations": _expiration_metrics(),
        "contracts": {
            "total": Contract.objects.count(),
            "active": Contract.objects.filter(status=Contract.ContractStatus.ACTIVE).count(),
            "with_documents": Contract.objects.filter(digital_record__documents__isnull=False).distinct().count(),
        },
        "audit": {
            "total_events": AuditLog.objects.count(),
            "events_in_period": AuditLog.objects.filter(timestamp__gte=since).count(),
            "views_and_downloads": AuditLog.objects.filter(
                Q(action=AuditLog.Action.VIEW) | Q(action=AuditLog.Action.DOWNLOAD)
            ).count(),
        },
    }
