"""Servicios de dominio del núcleo: alta de contratos con expediente digital (US-008)."""
from __future__ import annotations

import logging

from django.db import transaction

from apps.core.models import Contract, DigitalRecord

logger = logging.getLogger(__name__)


def create_contract(**data) -> Contract:
    """Crea el contrato, su DigitalRecord (vía señal) y provisiona la carpeta en S3/MinIO.

    Un fallo del storage no impide registrar el contrato: el prefijo se crea de
    forma perezosa al radicar el primer documento del expediente.
    """
    with transaction.atomic():
        contract = Contract.objects.create(**data)
        record = DigitalRecord.objects.get(contract=contract)

    provision_record_storage(record)
    return contract


def provision_record_storage(record: DigitalRecord) -> str | None:
    from apps.documents.services.storage import ensure_record_prefix

    try:
        return ensure_record_prefix(record)
    except Exception:  # pragma: no cover - depende de la disponibilidad del bucket
        logger.warning(
            "No se pudo provisionar el expediente %s en el storage", record.storage_path,
            exc_info=True,
        )
        return None
