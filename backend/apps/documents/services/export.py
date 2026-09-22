"""
Exportación masiva del expediente digital en ZIP (US-020).

El archivo se construye en streaming: cada PDF se copia por bloques desde
S3/MinIO directamente al ZIP y los bytes se entregan al cliente a medida que se
generan, sin escribir en disco ni cargar el expediente completo en memoria.
Incluye `manifest.json` con la relación de documentos y su hash SHA-256.
"""
from __future__ import annotations

import io
import json
import logging
import zipfile
from collections.abc import Iterator
from datetime import datetime

from django.core.files.storage import default_storage
from django.utils import timezone
from django.utils.text import get_valid_filename, slugify

from apps.core.models import Contract
from apps.documents.models import AuditLog, Document
from apps.documents.services.audit import log_action

logger = logging.getLogger(__name__)

CHUNK_SIZE = 1024 * 1024
EXPORT_TYPE = "full_record_zip"
MANIFEST_NAME = "manifest.json"


class _ChunkBuffer(io.RawIOBase):
    """Destino no posicionable para ZipFile: acumula bytes que el generador drena."""

    def __init__(self):
        super().__init__()
        self._chunks: list[bytes] = []

    def writable(self) -> bool:
        return True

    def write(self, data) -> int:  # type: ignore[override]
        self._chunks.append(bytes(data))
        return len(data)

    def drain(self) -> bytes:
        chunks, self._chunks = self._chunks, []
        return b"".join(chunks)


def export_filename(contract: Contract, when: datetime | None = None) -> str:
    when = when or timezone.localtime()
    return f"expediente_{slugify(contract.contract_number).upper()}_{when:%Y%m%d_%H%M}.zip"


def zip_entry_path(document: Document) -> str:
    category = document.document_type.category if document.document_type else "SIN_TIPIFICAR"
    safe_name = get_valid_filename(document.original_filename) or "documento.pdf"
    return f"{category}/{document.filing_number}_{safe_name}"


def export_documents(contract: Contract):
    """Documentos del expediente en orden cronológico (todos los estados)."""
    return (
        contract.digital_record.documents.select_related("document_type", "registered_by")
        .order_by("created_at", "filing_number")
    )


def build_manifest(contract: Contract, documents: list[Document], *, generated_by: str | None, missing: list[str]) -> dict:
    client = contract.client
    return {
        "system": "Brevetto — Coltebienes S.A.",
        "export_type": EXPORT_TYPE,
        "generated_at": timezone.localtime().isoformat(),
        "generated_by": generated_by,
        "contract": {
            "contract_number": contract.contract_number,
            "status": contract.status,
            "property_address": contract.property_address,
            "start_date": contract.start_date.isoformat(),
            "end_date": contract.end_date.isoformat(),
            "storage_path": contract.digital_record.storage_path,
        },
        "client": {
            "name": client.name,
            "document_type": client.document_type,
            "identification_number": client.identification_number,
            "email": client.email,
        },
        "document_count": len(documents),
        "missing_files": missing,
        "documents": [
            {
                "filing_number": doc.filing_number,
                "zip_path": zip_entry_path(doc),
                "original_filename": doc.original_filename,
                "document_type": doc.document_type.code if doc.document_type else None,
                "category": doc.document_type.category if doc.document_type else None,
                "document_date": doc.document_date.isoformat() if doc.document_date else None,
                "expiration_date": doc.expiration_date.isoformat() if doc.expiration_date else None,
                "processing_status": doc.processing_status,
                "source_channel": doc.source_channel,
                "sha256": doc.file_hash,
                "size_bytes": doc.file_size_bytes,
                "mime_type": doc.mime_type,
                "filed_at": timezone.localtime(doc.created_at).isoformat(),
                "registered_by": doc.registered_by.username if doc.registered_by else doc.external_sender_name or None,
            }
            for doc in documents
        ],
    }


def iter_record_zip(contract: Contract, documents: list[Document], *, generated_by: str | None) -> Iterator[bytes]:
    """Generador de bytes del ZIP. Los archivos ausentes en el bucket se listan en el manifest."""
    buffer = _ChunkBuffer()
    missing: list[str] = []
    included: list[Document] = []

    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for document in documents:
            if not default_storage.exists(document.file_path):
                logger.warning("Exportación %s: objeto ausente %s", contract.contract_number, document.file_path)
                missing.append(document.filing_number)
                continue
            info = zipfile.ZipInfo(zip_entry_path(document), date_time=timezone.localtime(document.created_at).timetuple()[:6])
            info.compress_type = zipfile.ZIP_DEFLATED
            with default_storage.open(document.file_path, "rb") as source, archive.open(info, mode="w") as target:
                for chunk in iter(lambda: source.read(CHUNK_SIZE), b""):
                    target.write(chunk)
                    yield buffer.drain()
            included.append(document)

        manifest = build_manifest(contract, included, generated_by=generated_by, missing=missing)
        archive.writestr(MANIFEST_NAME, json.dumps(manifest, ensure_ascii=False, indent=2))
        yield buffer.drain()

    yield buffer.drain()


def log_record_export(contract: Contract, documents: list[Document], *, request=None) -> int:
    """Deja rastro DESCARGA en cada documento exportado (la bitácora es por documento)."""
    for document in documents:
        log_action(
            document,
            AuditLog.Action.DOWNLOAD,
            request=request,
            details={
                "export_type": EXPORT_TYPE,
                "document_count": len(documents),
                "contract_number": contract.contract_number,
            },
        )
    return len(documents)
