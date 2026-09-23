"""Modelos de registro documental para US-001 y US-004."""
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


class Document(models.Model):
    """Registro persistente de un documento antes de su procesamiento."""

    class ProcessingStatus(models.TextChoices):
        RECEIVED = "RECIBIDO", "Recibido / En cola"
        PROCESSING = "PROCESANDO", "Procesando"
        PROCESSED = "PROCESADO", "Procesado"
        FAILED = "FALLIDO", "Fallido"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    filing_number = models.CharField(
        max_length=50, unique=True, db_index=True, editable=False
    )
    original_filename = models.CharField(max_length=255)
    file_path = models.CharField(max_length=1000)
    file_hash = models.CharField(max_length=64, blank=True)
    file_size_bytes = models.PositiveBigIntegerField()
    mime_type = models.CharField(max_length=100)
    processing_status = models.CharField(
        max_length=30,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.RECEIVED,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Documento"
        verbose_name_plural = "Documentos"

    def save(self, *args, **kwargs):
        if not self.filing_number:
            from apps.documents.services.filing import generate_filing_number

            with transaction.atomic():
                self.filing_number = generate_filing_number()
                return super().save(*args, **kwargs)
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.filing_number} - {self.original_filename}"

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


    def __str__(self):
        return f"{self.filing_number} - {self.original_filename}"
