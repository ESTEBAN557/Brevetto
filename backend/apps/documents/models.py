"""Modelos de radicación de documentos.

- FilingSequence: consecutivo diario atómico para el número de radicado (US-001).
- DocumentType: catálogo mínimo de tipos documentales.
- Document: registro formal de un documento radicado (US-004).
"""
import uuid

from django.conf import settings
from django.db import models, transaction


class FilingSequence(models.Model):
    """Consecutivo diario protegido contra duplicados concurrentes."""

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
        with transaction.atomic():
            sequence, _created = cls.objects.select_for_update().get_or_create(
                date=target_date
            )
            sequence.last_number += 1
            sequence.save(update_fields=["last_number"])
            return cls.format_filing_number(target_date, sequence.last_number)

    @staticmethod
    def format_filing_number(target_date, sequence: int) -> str:
        prefix = getattr(settings, "FILING_NUMBER_PREFIX", "RAD")
        digits = getattr(settings, "FILING_NUMBER_SEQUENCE_DIGITS", 6)
        return f"{prefix}-{target_date:%Y%m%d}-{sequence:0{digits}d}"


class TimeStampedModel(models.Model):
    """Base con identificador UUID y marcas de tiempo automáticas."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class DocumentType(TimeStampedModel):
    """Catálogo de tipos documentales (versión mínima para US-004)."""

    class Category(models.TextChoices):
        LEGAL = "LEGAL", "Documento Legal / Contractual"
        INSURANCE = "POLIZA", "Pólizas y Seguros"
        UTILITIES = "SERVICIOS", "Servicios Públicos"
        FINANCIAL = "FINANCIERO", "Facturación y Pagos"
        COMMUNICATION = "COMUNICACION", "Comunicaciones y Solicitudes"

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=50, unique=True)
    category = models.CharField(
        max_length=30, choices=Category.choices, default=Category.LEGAL
    )
    requires_expiration = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Tipo Documental"
        verbose_name_plural = "Tipos Documentales"
        ordering = ["category", "name"]

    def __str__(self):
        return f"[{self.category}] {self.name}"


class Document(TimeStampedModel):
    """Registro formal de un documento radicado en el sistema (US-004)."""

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
    document_type = models.ForeignKey(
        DocumentType, on_delete=models.SET_NULL, null=True, blank=True
    )

    original_filename = models.CharField(max_length=255)
    file_size_bytes = models.BigIntegerField()
    mime_type = models.CharField(max_length=100, default="application/pdf")

    source_channel = models.CharField(
        max_length=30,
        choices=SourceChannel.choices,
        default=SourceChannel.DIGITAL_INTERNAL,
    )
    processing_status = models.CharField(
        max_length=30,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.RECEIVED,
        db_index=True,
    )

    document_date = models.DateField(null=True, blank=True)

    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registered_documents",
    )

    class Meta:
        verbose_name = "Documento Radicado"
        verbose_name_plural = "Documentos Radicados"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["processing_status", "-created_at"],
                name="doc_status_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.filing_number} - {self.original_filename}"
