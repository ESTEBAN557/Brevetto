"""
Alertas de vencimiento documental (Requerimiento Coltebienes #6).

Identifica pólizas, certificados y demás documentos con vigencia que ya vencieron
o vencen en los próximos N días, y deja constancia en AuditLog (acción
ALERTA_VENCIMIENTO) una sola vez por etapa: warning (<= 30 d), critical (<= 7 d)
y expired. La bitácora es el registro inmutable de que la alerta fue emitida.
"""
from __future__ import annotations

from datetime import date, timedelta

from django.conf import settings
from django.utils import timezone

from apps.documents.models import AuditLog, Document
from apps.documents.services.audit import log_action

STAGE_EXPIRED = "expired"
STAGE_CRITICAL = "critical"
STAGE_WARNING = "warning"
CRITICAL_DAYS = 7

ACTIVE_STATUSES = (
    Document.ProcessingStatus.PROCESSED,
    Document.ProcessingStatus.NEEDS_REVIEW,
    Document.ProcessingStatus.RECEIVED,
    Document.ProcessingStatus.PROCESSING,
)


def alert_window_days() -> int:
    return int(getattr(settings, "EXPIRATION_ALERT_DAYS", 30))


def days_to_expiration(expiration_date: date | None, today: date | None = None) -> int | None:
    if expiration_date is None:
        return None
    return (expiration_date - (today or timezone.localdate())).days


def alert_stage(expiration_date: date | None, today: date | None = None, window_days: int | None = None) -> str | None:
    days = days_to_expiration(expiration_date, today)
    if days is None:
        return None
    if days < 0:
        return STAGE_EXPIRED
    if days <= CRITICAL_DAYS:
        return STAGE_CRITICAL
    if days <= (window_days or alert_window_days()):
        return STAGE_WARNING
    return None


def expiring_documents_queryset(days: int | None = None, include_expired: bool = True, today: date | None = None):
    """Documentos con vigencia que vence dentro de `days` días (y los ya vencidos si se pide)."""
    today = today or timezone.localdate()
    limit = today + timedelta(days=days if days is not None else alert_window_days())
    queryset = (
        Document.objects.select_related(
            "document_type", "registered_by", "digital_record__contract__client"
        )
        .filter(
            processing_status__in=ACTIVE_STATUSES,
            expiration_date__isnull=False,
            expiration_date__lte=limit,
        )
        .order_by("expiration_date", "filing_number")
    )
    if not include_expired:
        queryset = queryset.filter(expiration_date__gte=today)
    return queryset


def build_alert_details(document: Document, stage: str, today: date) -> dict:
    contract = document.digital_record.contract if document.digital_record else None
    client = contract.client if contract else None
    return {
        "stage": stage,
        "expiration_date": document.expiration_date.isoformat(),
        "days_left": days_to_expiration(document.expiration_date, today),
        "document_type": document.document_type.code if document.document_type else None,
        "contract_number": contract.contract_number if contract else None,
        "client_name": client.name if client else None,
        "client_email": client.email if client else None,
        "client_phone": client.phone if client else None,
        "as_of": today.isoformat(),
    }


def check_expiring_documents(days: int | None = None, today: date | None = None) -> dict:
    """Recorre los documentos por vencer y registra la alerta de cada etapa una sola vez."""
    today = today or timezone.localdate()
    window = days if days is not None else alert_window_days()
    summary = {"checked": 0, "alerts_created": 0, STAGE_EXPIRED: 0, STAGE_CRITICAL: 0, STAGE_WARNING: 0, "as_of": today.isoformat()}

    for document in expiring_documents_queryset(window, include_expired=True, today=today):
        summary["checked"] += 1
        stage = alert_stage(document.expiration_date, today, window)
        if stage is None:
            continue
        summary[stage] += 1
        already_alerted = AuditLog.objects.filter(
            document=document,
            action=AuditLog.Action.EXPIRATION_ALERT,
            details__stage=stage,
            details__expiration_date=document.expiration_date.isoformat(),
        ).exists()
        if already_alerted:
            continue
        log_action(document, AuditLog.Action.EXPIRATION_ALERT, details=build_alert_details(document, stage, today))
        summary["alerts_created"] += 1

    return summary
