"""
Servicios del portal público de inquilinos.

La sesión del portal es un token firmado (HMAC con SECRET_KEY) y con vencimiento,
sin estado en base de datos. Identifica al contrato validado y evita enumerar
contratos: cualquier fallo de verificación responde con el mismo mensaje.
"""
from __future__ import annotations

import re
from datetime import timedelta

from django.conf import settings
from django.core import signing
from django.utils import timezone

from apps.core.models import Contract, DocumentType

PORTAL_TOKEN_SALT = "brevetto.portal.session"
RECEIPT_SALT = "brevetto.portal.receipt"

PORTAL_ALLOWED_STATUSES = (Contract.ContractStatus.ACTIVE, Contract.ContractStatus.IN_RENEWAL)


class PortalVerificationError(Exception):
    """Credenciales de portal inválidas (mensaje genérico hacia el cliente)."""


class PortalTokenError(Exception):
    """Token de sesión ausente, alterado o vencido."""


def normalize_identification(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z]", "", value or "").upper()


def session_ttl_seconds() -> int:
    return int(getattr(settings, "PORTAL_SESSION_TTL_SECONDS", 1800))


def verify_contract(contract_number: str, identification_number: str) -> Contract:
    """Devuelve el contrato si número + identificación coinciden y el contrato está vigente."""
    contract = (
        Contract.objects.select_related("client", "digital_record")
        .filter(contract_number__iexact=(contract_number or "").strip())
        .first()
    )
    if contract is None or contract.status not in PORTAL_ALLOWED_STATUSES:
        raise PortalVerificationError()
    if normalize_identification(contract.client.identification_number) != normalize_identification(
        identification_number
    ):
        raise PortalVerificationError()
    return contract


def issue_portal_token(contract: Contract) -> str:
    signer = signing.TimestampSigner(salt=PORTAL_TOKEN_SALT)
    return signer.sign_object({"contract_id": str(contract.pk), "contract_number": contract.contract_number})


def resolve_portal_token(token: str) -> Contract:
    if not token:
        raise PortalTokenError("Token de portal requerido.")
    signer = signing.TimestampSigner(salt=PORTAL_TOKEN_SALT)
    try:
        payload = signer.unsign_object(token, max_age=timedelta(seconds=session_ttl_seconds()))
    except signing.SignatureExpired as exc:
        raise PortalTokenError("La sesión del portal expiró. Valide nuevamente su contrato.") from exc
    except signing.BadSignature as exc:
        raise PortalTokenError("Token de portal inválido.") from exc

    contract = (
        Contract.objects.select_related("client", "digital_record")
        .filter(pk=payload.get("contract_id"), status__in=PORTAL_ALLOWED_STATUSES)
        .first()
    )
    if contract is None:
        raise PortalTokenError("El contrato asociado a la sesión ya no está vigente.")
    return contract


def receipt_signature(filing_number: str, file_hash: str) -> str:
    """Firma digital del comprobante: permite verificar su autenticidad posteriormente."""
    return signing.Signer(salt=RECEIPT_SALT).signature(f"{filing_number}:{file_hash}")


def mask_identification(value: str) -> str:
    digits = normalize_identification(value)
    if len(digits) <= 4:
        return "*" * len(digits)
    return "*" * (len(digits) - 4) + digits[-4:]


def portal_document_types():
    """Tipos que un inquilino puede radicar desde el portal (excluye los internos)."""
    return DocumentType.objects.exclude(code__in=("CONTRATO", "ACTA_ENTREGA", "NOTIFICACION")).order_by(
        "category", "name"
    )


def expiring_documents(contract: Contract, within_days: int = 30):
    """Documentos con vigencia vencida o por vencer para mostrar al inquilino."""
    limit = timezone.localdate() + timedelta(days=within_days)
    return (
        contract.digital_record.documents.select_related("document_type")
        .filter(expiration_date__isnull=False, expiration_date__lte=limit)
        .order_by("expiration_date")
    )
