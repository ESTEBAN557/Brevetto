"""
Clasificación asistida por IA con regla Human-in-the-Loop (HITL).

Un documento solo se archiva automáticamente cuando la confianza del modelo es
>= settings.AI_CONFIDENCE_THRESHOLD (0.85) Y el contrato se resolvió sin
ambigüedad. En cualquier otro caso pasa a la bandeja REQUIERE_REVISION.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any

from django.conf import settings
from django.db.models import F, Value
from django.db.models.functions import Replace

from apps.core.models import Client, Contract, DocumentType
from apps.documents.models import AuditLog, Document
from apps.documents.services.audit import log_action

# Tipo devuelto por Gemini -> código del catálogo DocumentType
AI_TYPE_TO_DOCUMENT_TYPE_CODE = {
    "POLIZA": "POLIZA_CUMPLIMIENTO",
    "FACTURA": "FACTURA",
    "SERVICIO_PUBLICO": "SERVICIO_PUBLICO",
    "CARTA_SOLICITUD": "CARTA_SOLICITUD",
    "ACTA_ENTREGA": "ACTA_ENTREGA",
    "OTRO": "OTRO",
}

MIN_IDENTIFICATION_DIGITS = 6


class ContractResolution:
    """Resultado de intentar asociar el documento a un contrato."""

    def __init__(self, contract: Contract | None, method: str, candidates: int = 0):
        self.contract = contract
        self.method = method          # contract_number | client_identification | none | ambiguous
        self.candidates = candidates

    @property
    def is_ambiguous(self) -> bool:
        return self.method == "ambiguous"


def parse_iso_date(value) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def resolve_document_type(ai_document_type: str | None) -> DocumentType | None:
    if not ai_document_type:
        return None
    code = str(ai_document_type).strip().upper()
    direct = DocumentType.objects.filter(code=code).first()
    if direct:
        return direct
    mapped = AI_TYPE_TO_DOCUMENT_TYPE_CODE.get(code)
    return DocumentType.objects.filter(code=mapped).first() if mapped else None


def resolve_contract(ai_data: dict[str, Any]) -> ContractResolution:
    """1) número de contrato exacto; 2) identificación del cliente con un único contrato activo."""
    contract_number = (ai_data.get("contract_number") or "").strip()
    if contract_number:
        contract = (
            Contract.objects.select_related("digital_record", "client")
            .filter(contract_number__iexact=contract_number)
            .first()
        )
        if contract:
            return ContractResolution(contract, "contract_number", 1)

    identification = ai_data.get("client_identification") or ""
    digits = re.sub(r"\D", "", str(identification))
    if len(digits) >= MIN_IDENTIFICATION_DIGITS:
        clients = Client.objects.annotate(
            normalized_id=Replace(
                Replace(F("identification_number"), Value("."), Value("")),
                Value("-"),
                Value(""),
            )
        ).filter(normalized_id__startswith=digits)
        active = list(
            Contract.objects.select_related("digital_record", "client")
            .filter(client__in=clients, status=Contract.ContractStatus.ACTIVE)
            .order_by("-start_date")[:5]
        )
        if len(active) == 1:
            return ContractResolution(active[0], "client_identification", 1)
        if len(active) > 1:
            return ContractResolution(None, "ambiguous", len(active))

    return ContractResolution(None, "none", 0)


def apply_classification(document: Document, ai_data: dict[str, Any]) -> str:
    """Persiste la extracción, aplica la regla HITL y deja rastro en AuditLog.

    Devuelve el nuevo `processing_status` del documento.
    """
    threshold = float(getattr(settings, "AI_CONFIDENCE_THRESHOLD", 0.85))
    confidence = float(ai_data.get("confidence_score") or 0.0)
    resolution = resolve_contract(ai_data)
    document_type = resolve_document_type(ai_data.get("document_type"))

    document.ai_extracted_data = ai_data
    document.ai_confidence_score = confidence

    details: dict[str, Any] = {
        "confidence": confidence,
        "threshold": threshold,
        "contract_resolution": resolution.method,
        "suggested_contract_number": (
            resolution.contract.contract_number if resolution.contract else ai_data.get("contract_number")
        ),
        "suggested_document_type": document_type.code if document_type else None,
    }

    auto_classify = confidence >= threshold and resolution.contract is not None

    if auto_classify:
        document.digital_record = resolution.contract.digital_record
        if document_type is not None:
            document.document_type = document_type
        document.document_date = parse_iso_date(ai_data.get("document_date")) or document.document_date
        document.expiration_date = parse_iso_date(ai_data.get("expiration_date")) or document.expiration_date
        document.processing_status = Document.ProcessingStatus.PROCESSED
        details["auto_associated"] = True
    else:
        document.processing_status = Document.ProcessingStatus.NEEDS_REVIEW
        details["needs_human_validation"] = True
        details["reason"] = (
            "low_confidence" if confidence < threshold
            else "ambiguous_contract" if resolution.is_ambiguous
            else "contract_not_found"
        )
        if resolution.is_ambiguous:
            details["candidate_contracts"] = resolution.candidates

    document.save(
        update_fields=[
            "ai_extracted_data",
            "ai_confidence_score",
            "digital_record",
            "document_type",
            "document_date",
            "expiration_date",
            "processing_status",
            "updated_at",
        ]
    )
    log_action(document, AuditLog.Action.AI_CLASSIFY, details=details)
    return document.processing_status
