"""Serializadores del módulo de documentos (US-004)."""
from rest_framework import serializers

from apps.documents.models import Document


class DocumentRegistrationSerializer(serializers.ModelSerializer):
    """Valida la información del formulario de registro y crea el documento.

    - Los campos `original_filename`, `file_size_bytes` y `mime_type` son
      obligatorios: si faltan, DRF responde `400` con los mensajes de validación
      correspondientes (AC-019).
    - `filing_number` y `processing_status` son de solo lectura: el número de
      radicado lo genera el sistema (AC-017) y el estado inicial es `RECIBIDO`.
    """

    class Meta:
        model = Document
        fields = [
            "id",
            "filing_number",
            "original_filename",
            "file_size_bytes",
            "mime_type",
            "source_channel",
            "document_type",
            "document_date",
            "processing_status",
            "registered_by",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "filing_number",
            "processing_status",
            "registered_by",
            "created_at",
        ]

    def validate_original_filename(self, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise serializers.ValidationError("El nombre del archivo es obligatorio.")
        return cleaned

    def validate_file_size_bytes(self, value: int) -> int:
        if value is None or value <= 0:
            raise serializers.ValidationError(
                "El tamaño del archivo debe ser mayor que cero."
            )
        return value

    def validate_mime_type(self, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise serializers.ValidationError("El tipo MIME es obligatorio.")
        return cleaned
