"""Servicio de auditoría: única vía para insertar registros en la bitácora inmutable."""
from __future__ import annotations

from typing import Any

from apps.documents.models import AuditLog, Document


def get_client_ip(request) -> str | None:
    """Obtiene la IP real del cliente respetando proxies inversos (X-Forwarded-For)."""
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    return request.META.get("REMOTE_ADDR") or None


def get_user_agent(request) -> str:
    if request is None:
        return ""
    return (request.META.get("HTTP_USER_AGENT") or "")[:500]


def log_action(
    document: Document,
    action: str,
    *,
    user=None,
    request=None,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    """Registra una acción sobre un documento. Solo INSERT: la tabla es append-only."""
    performed_by = user
    if performed_by is None and request is not None:
        candidate = getattr(request, "user", None)
        if candidate is not None and getattr(candidate, "is_authenticated", False):
            performed_by = candidate

    return AuditLog.objects.create(
        document=document,
        action=action,
        performed_by=performed_by,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        details=details or {},
    )
