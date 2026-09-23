"""Serializadores del módulo de documentos."""
from rest_framework import serializers

from apps.documents.models import Document

class DocumentSerializer(serializers.ModelSerializer):
    """Listar / consultar documentos (otra HU)."""

    class Meta:
        model = Document
        fields = (
            "id",
            "filing_number",
            "original_filename",
            "file_path",
            "file_hash",
            "file_size_bytes",
            "mime_type",
            "processing_status",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "filing_number",
            "processing_status",
            "created_at",
            "updated_at",
        )
        extra_kwargs = {"file_hash": {"required": False, "allow_blank": True}}

    def validate_file_size_bytes(self, value):
        if value < 0:
            raise serializers.ValidationError("El tamaño no puede ser negativo.")
        return value

class DocumentRegistrationSerializer(serializers.ModelSerializer):
    """Registro formal de documento (US-004): valida obligatorios (AC-019)."""

    class Meta:
        model = Document
        fields = [
            "id",
            "filing_number",
            "original_filename",
            "file_path",
            "file_hash",
            "file_size_bytes",
            "mime_type",
            "processing_status",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "filing_number",
            "processing_status",
            "created_at",
        ]
        extra_kwargs = {
            "file_path": {"required": False, "allow_blank": True},
            "file_hash": {"required": False, "allow_blank": True},
        }

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
