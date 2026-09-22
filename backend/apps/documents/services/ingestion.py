"""
Servicio de ingesta y radicación de documentos (US-002, US-004, US-005, US-006).

Flujo: validar archivo -> generar radicado atómico -> checksum SHA-256 -> subir a
S3/MinIO -> crear Document (RECIBIDO) -> AuditLog CARGA -> encolar procesamiento IA.
"""
from __future__ import annotations

import hashlib
import logging
from pathlib import PurePosixPath

from django.conf import settings
from django.db import transaction

from apps.core.models import DigitalRecord
from apps.documents.models import AuditLog, Document
from apps.documents.services.audit import log_action
from apps.documents.services.filing import generate_filing_number
from apps.documents.services.storage import build_object_key, store_document_file

logger = logging.getLogger(__name__)

MIME_BY_EXTENSION = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


class DocumentValidationError(ValueError):
    """Archivo rechazado por extensión, tamaño o tipo MIME."""


def get_extension(filename: str) -> str:
    return PurePosixPath(filename or "").suffix.lower()


def validate_upload(file) -> str:
    """Valida extensión, tamaño y MIME declarado. Devuelve el MIME canónico por extensión."""
    allowed_extensions = tuple(ext.lower() for ext in settings.UPLOAD_ALLOWED_EXTENSIONS)
    max_size = settings.UPLOAD_MAX_SIZE_BYTES

    extension = get_extension(getattr(file, "name", ""))
    if extension not in allowed_extensions:
        raise DocumentValidationError(
            f"Extensión '{extension or '(ninguna)'}' no permitida. "
            f"Use: {', '.join(allowed_extensions)}."
        )

    size = getattr(file, "size", None) or 0
    if size <= 0:
        raise DocumentValidationError("El archivo está vacío.")
    if size > max_size:
        raise DocumentValidationError(
            f"El archivo pesa {size} bytes y supera el máximo de {max_size} bytes (25 MB)."
        )

    declared_mime = (getattr(file, "content_type", "") or "").split(";")[0].strip().lower()
    if declared_mime and declared_mime != "application/octet-stream":
        if declared_mime not in settings.UPLOAD_ALLOWED_MIME_TYPES:
            raise DocumentValidationError(f"Tipo MIME '{declared_mime}' no permitido.")

    return MIME_BY_EXTENSION[extension]


def compute_sha256(file) -> str:
    """Checksum SHA-256 leyendo por bloques; deja el puntero al inicio del archivo."""
    digest = hashlib.sha256()
    file.seek(0)
    for chunk in iter(lambda: file.read(1024 * 1024), b""):
        digest.update(chunk)
    file.seek(0)
    return digest.hexdigest()


def enqueue_processing(document_id) -> None:
    """Dispara el pipeline asíncrono de IA (US-009). Import diferido para evitar ciclos."""
    from apps.documents.tasks import process_document_content_task

    process_document_content_task.delay(str(document_id))


def register_document(
    *,
    file,
    source_channel: str,
    user=None,
    digital_record: DigitalRecord | None = None,
    request=None,
    external_sender_name: str = "",
    document_date=None,
) -> Document:
    """Radica un documento individual y programa su procesamiento al confirmar la transacción."""
    mime_type = validate_upload(file)

    # El radicado se genera en su propia transacción corta para no retener el bloqueo
    # de la secuencia mientras se sube el archivo al bucket.
    filing_number = generate_filing_number()
    file_hash = compute_sha256(file)
    object_key = build_object_key(filing_number, file.name, digital_record)
    stored_key = store_document_file(object_key, file)

    with transaction.atomic():
        document = Document.objects.create(
            filing_number=filing_number,
            digital_record=digital_record,
            file_path=stored_key,
            original_filename=file.name[:255],
            file_hash=file_hash,
            file_size_bytes=file.size,
            mime_type=mime_type,
            source_channel=source_channel,
            processing_status=Document.ProcessingStatus.RECEIVED,
            registered_by=user if getattr(user, "is_authenticated", False) else None,
            external_sender_name=external_sender_name or "",
            document_date=document_date,
        )
        log_action(
            document,
            AuditLog.Action.UPLOAD,
            user=document.registered_by,
            request=request,
            details={
                "filing_number": filing_number,
                "original_filename": document.original_filename,
                "file_hash": file_hash,
                "file_size_bytes": document.file_size_bytes,
                "mime_type": mime_type,
                "source_channel": source_channel,
                "storage_key": stored_key,
                "contract_number": (
                    digital_record.contract.contract_number if digital_record else None
                ),
            },
        )
        transaction.on_commit(lambda: enqueue_processing(document.pk))

    logger.info("Documento radicado %s (%s bytes) -> %s", filing_number, file.size, stored_key)
    return document


def register_documents_batch(
    *,
    files,
    source_channel: str,
    user=None,
    digital_record: DigitalRecord | None = None,
    request=None,
) -> list[Document]:
    """Radica varios documentos (US-011). Valida todos antes de radicar el primero."""
    errors = []
    for index, file in enumerate(files):
        try:
            validate_upload(file)
        except DocumentValidationError as exc:
            errors.append(f"[{index}] {getattr(file, 'name', '?')}: {exc}")
    if errors:
        raise DocumentValidationError(" | ".join(errors))

    return [
        register_document(
            file=file,
            source_channel=source_channel,
            user=user,
            digital_record=digital_record,
            request=request,
        )
        for file in files
    ]
