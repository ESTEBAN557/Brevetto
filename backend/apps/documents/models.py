"""
Modelos de radicación y documentos de Brevetto (apps.documents).

- FilingSequence: consecutivo diario atómico para el número de radicado (US-001).
- Document: documento radicado con metadatos, checksum y estado de procesamiento.
- AuditLog: bitácora inmutable (append-only) de todas las acciones sobre documentos.
Ver docs/03_DATABASE_MODELS.md.
"""
import uuid

from django.conf import settings
from django.db import models, transaction

from apps.core.models import DigitalRecord, DocumentType, TimeStampedModel


# 5. SECUENCIA ATÓMICA DE RADICACIÓN (US-001)
class FilingSequence(models.Model):
    """Contador diario del radicado. Una fila por fecha, protegida con bloqueo de fila."""

    date = models.DateField(unique=True, db_index=True)
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Secuencia de Radicación"
        verbose_name_plural = "Secuencias de Radicación"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.date:%Y-%m-%d} -> {self.last_number:06d}"

    @classmethod
    def get_next_number(cls, target_date) -> str:
        """Genera el siguiente consecutivo de forma atómica para evitar colisiones.

        Estrategia: `transaction.atomic()` + `SELECT ... FOR UPDATE` sobre la fila
        de la fecha. Dos transacciones concurrentes se serializan en la BD: la
        segunda espera a que la primera confirme y lee el valor ya incrementado,
        por lo que nunca se devuelve el mismo número dos veces.

        Devuelve un radicado con el formato `RAD-YYYYMMDD-XXXXXX`.
        """
        with transaction.atomic():
            seq, _created = cls.objects.select_for_update().get_or_create(date=target_date)
            seq.last_number += 1
            seq.save(update_fields=["last_number"])
            return cls.format_filing_number(target_date, seq.last_number)

    @staticmethod
    def format_filing_number(target_date, sequence: int) -> str:
        prefix = getattr(settings, "FILING_NUMBER_PREFIX", "RAD")
        digits = getattr(settings, "FILING_NUMBER_SEQUENCE_DIGITS", 6)
        return f"{prefix}-{target_date.strftime('%Y%m%d')}-{sequence:0{digits}d}"


# 6. DOCUMENTO RADICADO
class Document(TimeStampedModel):
    class ProcessingStatus(models.TextChoices):
        RECEIVED = "RECIBIDO", "Recibido / En cola"
        PROCESSING = "PROCESANDO", "Procesando en Celery"
        NEEDS_REVIEW = "REQUIERE_REVISION", "Requiere Validación Humana (HITL)"
        PROCESSED = "PROCESADO", "Clasificado y Archivado"
        FAILED = "FALLIDO", "Error de Procesamiento"

    class SourceChannel(models.TextChoices):
        PHYSICAL = "FISICO_ESCANEADO", "Documento Físico Escaneado"
        DIGITAL_INTERNAL = "DIGITAL_INTERNO", "Digital Cargado por Personal"
        WEB_PORTAL = "PORTAL_WEB", "Radicado por Cliente en Portal Web"
        EMAIL = "CORREO", "Ingreso por Correo Electrónico"

    filing_number = models.CharField(
        max_length=50, unique=True, db_index=True, verbose_name="Número de Radicado"
    )
    digital_record = models.ForeignKey(
        DigitalRecord,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
    )
    document_type = models.ForeignKey(
        DocumentType, on_delete=models.SET_NULL, null=True, blank=True
    )

    file_path = models.CharField(max_length=1000, help_text="URI del objeto en S3 / MinIO")
    original_filename = models.CharField(max_length=255)
    file_hash = models.CharField(max_length=64, help_text="Checksum SHA-256", db_index=True)
    file_size_bytes = models.BigIntegerField()
    mime_type = models.CharField(max_length=100, default="application/pdf")

    source_channel = models.CharField(
        max_length=30, choices=SourceChannel.choices, default=SourceChannel.DIGITAL_INTERNAL
    )
    processing_status = models.CharField(
        max_length=30,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.RECEIVED,
        db_index=True,
    )

    # Metadatos extraídos por IA
    ai_extracted_data = models.JSONField(default=dict, blank=True)
    ai_confidence_score = models.FloatField(null=True, blank=True)
    expiration_date = models.DateField(null=True, blank=True, db_index=True)
    document_date = models.DateField(null=True, blank=True)

    # Auditoría de usuario
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registered_documents",
    )
    external_sender_name = models.CharField(
        max_length=255, blank=True, help_text="Nombre del remitente externo si vino del portal"
    )

    class Meta:
        verbose_name = "Documento Radicado"
        verbose_name_plural = "Documentos Radicados"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["processing_status", "-created_at"], name="doc_status_created_idx"),
        ]

    def __str__(self):
        return f"{self.filing_number} - {self.original_filename}"

    @property
    def needs_human_review(self) -> bool:
        return self.processing_status == self.ProcessingStatus.NEEDS_REVIEW


# 7. LOG DE AUDITORÍA INMUTABLE (US-023, US-024, US-025)
class AuditLogImmutableError(Exception):
    """Se lanza al intentar modificar o eliminar registros de auditoría."""


class AuditLogQuerySet(models.QuerySet):
    """QuerySet que bloquea operaciones masivas de escritura sobre la bitácora."""

    def update(self, **kwargs):
        raise AuditLogImmutableError("AuditLog es append-only: UPDATE no permitido.")

    def delete(self):
        raise AuditLogImmutableError("AuditLog es append-only: DELETE no permitido.")

    def bulk_update(self, *args, **kwargs):
        raise AuditLogImmutableError("AuditLog es append-only: bulk_update no permitido.")


class AuditLog(models.Model):
    """Bitácora inmutable. Solo se permite INSERT (reforzado también con triggers en PostgreSQL)."""

    class Action(models.TextChoices):
        UPLOAD = "CARGA", "Carga y Radicación"
        AI_CLASSIFY = "CLASIFICACION_IA", "Clasificación con IA"
        HUMAN_VALIDATE = "VALIDACION_HUMANA", "Aprobación o Ajuste Manual"
        METADATA_UPDATE = "ACTUALIZACION_METADATOS", "Edición de Metadatos"
        VIEW = "CONSULTA_VISUAL", "Visualización en Visor Web"
        DOWNLOAD = "DESCARGA", "Descarga de Archivo"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="audit_logs")
    action = models.CharField(max_length=30, choices=Action.choices, db_index=True)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    details = models.JSONField(default=dict, blank=True)

    objects = AuditLogQuerySet.as_manager()

    class Meta:
        verbose_name = "Registro de Auditoría"
        verbose_name_plural = "Registros de Auditoría"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M:%S}] {self.action} - {self.document_id}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise AuditLogImmutableError(
                "AuditLog es append-only: no se puede modificar un registro."
            )
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise AuditLogImmutableError("AuditLog es append-only: no se puede eliminar un registro.")
