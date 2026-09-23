"""Servicio de creación de registros de documento (US-004).

Encapsula la regla de negocio de "crear registro de documento":
1. Genera y asocia un número de radicado único (reutiliza US-001).
2. Persiste el registro con estado inicial `RECIBIDO`.

La validación de campos obligatorios se realiza en la capa de serializador
(`DocumentRegistrationSerializer`), de modo que este servicio asume que los datos
que recibe ya son válidos.
"""
from __future__ import annotations

from typing import Any

from django.db import transaction

from apps.documents.models import Document
from apps.documents.services.filing import generate_filing_number


@transaction.atomic
def create_document_record(*, registered_by=None, **fields: Any) -> Document:
    """Crea y almacena un registro de documento con su número de radicado.

    La generación del radicado y la creación del registro ocurren dentro de la
    misma transacción para garantizar que un registro almacenado siempre tenga un
    número de radicado asociado (AC-016, AC-017, AC-018).
    """
    filing_number = generate_filing_number()
    return Document.objects.create(
        filing_number=filing_number,
        registered_by=registered_by,
        **fields,
    )
