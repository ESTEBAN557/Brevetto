"""
Servicio de almacenamiento de objetos (S3 / MinIO) vía django-storages.

Toda interacción con el bucket pasa por `default_storage`, configurado en
settings.STORAGES. En pruebas se sustituye por InMemoryStorage.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import PurePosixPath

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone
from django.utils.text import get_valid_filename

from apps.core.models import DigitalRecord

logger = logging.getLogger(__name__)

UNCLASSIFIED_PREFIX = "radicados/sin_clasificar"
RECORD_MARKER_FILENAME = ".expediente.json"
FALLBACK_FILENAME = "documento"


def safe_object_filename(original_filename: str) -> str:
    """Nombre seguro para la clave S3. Si no queda ningún carácter válido, usa un
    nombre genérico conservando la extensión (Django lanza SuspiciousFileOperation)."""
    try:
        safe = get_valid_filename(original_filename or "")
    except SuspiciousFileOperation:
        safe = ""
    if safe and not safe.startswith("."):
        return safe
    if safe.startswith("."):
        # Solo sobrevivió la extensión (ej. "¿¿??.pdf" -> ".pdf"): anteponer nombre genérico.
        return f"{FALLBACK_FILENAME}{safe.lower()}"
    extension = PurePosixPath(original_filename or "").suffix.lower()
    if re.fullmatch(r"\.[a-z0-9]{1,10}", extension):
        return f"{FALLBACK_FILENAME}{extension}"
    return FALLBACK_FILENAME


def build_object_key(
    filing_number: str,
    original_filename: str,
    digital_record: DigitalRecord | None = None,
) -> str:
    """Clave determinística del objeto en el bucket.

    - Con contrato conocido: `expedientes/<contrato>/<radicado>_<archivo>`
    - Sin contrato (pendiente de clasificación): `radicados/sin_clasificar/<YYYY>/<MM>/<radicado>_<archivo>`
    """
    safe_name = safe_object_filename(original_filename)
    if digital_record is not None:
        prefix = digital_record.storage_path.rstrip("/")
    else:
        # RAD-YYYYMMDD-XXXXXX -> año en [4:8], mes en [8:10]
        year, month = filing_number[4:8], filing_number[8:10]
        prefix = f"{UNCLASSIFIED_PREFIX}/{year}/{month}"
    return f"{prefix}/{filing_number}_{safe_name}"


def store_document_file(key: str, file) -> str:
    """Sube el archivo y devuelve la clave final (el storage puede renombrar si ya existe)."""
    if hasattr(file, "seek"):
        file.seek(0)
    return default_storage.save(key, file)


def get_file_bytes(key: str) -> bytes:
    with default_storage.open(key, "rb") as handle:
        return handle.read()


def file_exists(key: str) -> bool:
    return default_storage.exists(key)


def presigned_url_ttl_seconds() -> int:
    return int(getattr(settings, "AWS_QUERYSTRING_EXPIRE", 900))


def _is_s3_backend() -> bool:
    backend = settings.STORAGES.get("default", {}).get("BACKEND", "")
    return "storages.backends.s3" in backend


def get_presigned_url(key: str) -> str:
    """URL temporal de lectura (15 min por defecto).

    Dentro de Docker el backend habla con MinIO por `http://minio:9000`, pero el
    navegador del usuario necesita un host alcanzable. Si se define
    AWS_S3_PUBLIC_ENDPOINT_URL la firma se genera contra ese host; la firma v4
    incluye el Host, por lo que la URL solo es válida para ese endpoint público.
    """
    public_endpoint = getattr(settings, "AWS_S3_PUBLIC_ENDPOINT_URL", "") or ""
    if public_endpoint and _is_s3_backend():
        import boto3
        from botocore.config import Config

        client = boto3.client(
            "s3",
            endpoint_url=public_endpoint,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.AWS_STORAGE_BUCKET_NAME, "Key": key},
            ExpiresIn=presigned_url_ttl_seconds(),
        )
    return default_storage.url(key)


def ensure_record_prefix(record: DigitalRecord) -> str:
    """Crea la "carpeta" del expediente en el bucket (US-008).

    S3 no tiene carpetas reales: se materializa el prefijo con un objeto marcador
    que además documenta el contrato al que pertenece.
    """
    marker_key = f"{record.storage_path.rstrip('/')}/{RECORD_MARKER_FILENAME}"
    if default_storage.exists(marker_key):
        return marker_key

    payload = {
        "contract_number": record.contract.contract_number,
        "client": record.contract.client.name,
        "client_identification": record.contract.client.identification_number,
        "created_at": timezone.now().isoformat(),
    }
    content = ContentFile(json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"))
    saved = default_storage.save(marker_key, content)
    logger.info("Expediente provisionado en storage: %s", saved)
    return saved
