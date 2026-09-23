"""Servicio de creación de registros de documento (US-004)."""
from __future__ import annotations

from typing import Any

from apps.documents.models import Document

def create_document_record(**fields: Any) -> Document:
    """Crea y almacena un registro de documento.

    El número de radicado se genera automáticamente en Document.save()
    (reutiliza US-001), garantizando que todo registro almacenado tenga
    radicado asociado (AC-016, AC-017, AC-018).
    """
    return Document.objects.create(**fields)
