"""Serializers DRF del módulo de radicación y documentos (docs/04_API_SPECIFICATION.md)."""
from __future__ import annotations

from django.conf import settings
from rest_framework import serializers

from apps.core.models import Contract, DocumentType
from apps.documents.models import AuditLog, Document
from apps.documents.services.ingestion import DocumentValidationError, validate_upload

INTERNAL_SOURCE_CHANNELS = (
    Document.SourceChannel.PHYSICAL,
    Document.SourceChannel.DIGITAL_INTERNAL,
    Document.SourceChannel.EMAIL,
)


def _validate_file(file):
    try:
        validate_upload(file)
    except DocumentValidationError as exc:
        raise serializers.ValidationError(str(exc)) from exc
    return file


def _resolve_contract(contract_id):
    contract = (
        Contract.objects.select_related("digital_record", "client")
        .filter(pk=contract_id)
        .first()
    )
    if contract is None:
        raise serializers.ValidationError({"contract_id": "El contrato indicado no existe."})
    return contract


class DocumentUploadSerializer(serializers.Serializer):
    """Payload multipart de POST /documents/upload/."""

    file = serializers.FileField()
    source_channel = serializers.ChoiceField(
        choices=[(c.value, c.label) for c in INTERNAL_SOURCE_CHANNELS],
        default=Document.SourceChannel.DIGITAL_INTERNAL,
    )
    contract_id = serializers.UUIDField(required=False, allow_null=True)
    document_date = serializers.DateField(required=False, allow_null=True)
    external_sender_name = serializers.CharField(required=False, allow_blank=True, max_length=255)

    def validate_file(self, file):
        return _validate_file(file)

    def validate(self, attrs):
        contract_id = attrs.pop("contract_id", None)
        attrs["digital_record"] = _resolve_contract(contract_id).digital_record if contract_id else None
        return attrs


class DocumentBatchUploadSerializer(serializers.Serializer):
    """Payload multipart de POST /documents/batch-upload/ (US-011)."""

    files = serializers.ListField(
        child=serializers.FileField(), allow_empty=False, min_length=1, max_length=50
    )
    source_channel = serializers.ChoiceField(
        choices=[(c.value, c.label) for c in INTERNAL_SOURCE_CHANNELS],
        default=Document.SourceChannel.PHYSICAL,
    )
    contract_id = serializers.UUIDField(required=False, allow_null=True)

    def validate_files(self, files):
        errors = []
        for index, file in enumerate(files):
            try:
                validate_upload(file)
            except DocumentValidationError as exc:
                errors.append(f"[{index}] {file.name}: {exc}")
        if errors:
            raise serializers.ValidationError(errors)
        return files

    def validate(self, attrs):
        contract_id = attrs.pop("contract_id", None)
        attrs["digital_record"] = _resolve_contract(contract_id).digital_record if contract_id else None
        return attrs


class DocumentReceiptSerializer(serializers.ModelSerializer):
    """Respuesta 201 de la radicación individual (campos exactos de la especificación)."""

    class Meta:
        model = Document
        fields = (
            "id",
            "filing_number",
            "original_filename",
            "file_size_bytes",
            "source_channel",
            "processing_status",
            "created_at",
        )
        read_only_fields = fields


class DocumentTypeCompactSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentType
        fields = ("id", "code", "name", "category", "requires_expiration")


class DocumentSerializer(serializers.ModelSerializer):
    """Representación completa usada en listados, detalle y bandeja HITL."""

    document_type = DocumentTypeCompactSerializer(read_only=True)
    contract_id = serializers.UUIDField(source="digital_record.contract_id", read_only=True, default=None)
    contract_number = serializers.CharField(
        source="digital_record.contract.contract_number", read_only=True, default=None
    )
    client_name = serializers.CharField(
        source="digital_record.contract.client.name", read_only=True, default=None
    )
    registered_by = serializers.CharField(source="registered_by.username", read_only=True, default=None)
    needs_human_review = serializers.BooleanField(read_only=True)

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
            "source_channel",
            "processing_status",
            "needs_human_review",
            "contract_id",
            "contract_number",
            "client_name",
            "document_type",
            "ai_extracted_data",
            "ai_confidence_score",
            "document_date",
            "expiration_date",
            "registered_by",
            "external_sender_name",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class DocumentValidateSerializer(serializers.Serializer):
    """Payload de POST /documents/{id}/validate/ (confirmación humana)."""

    contract_id = serializers.UUIDField()
    document_type_id = serializers.UUIDField()
    expiration_date = serializers.DateField(required=False, allow_null=True)
    document_date = serializers.DateField(required=False, allow_null=True)

    def validate(self, attrs):
        attrs["contract"] = _resolve_contract(attrs.pop("contract_id"))
        document_type = DocumentType.objects.filter(pk=attrs.pop("document_type_id")).first()
        if document_type is None:
            raise serializers.ValidationError({"document_type_id": "El tipo documental no existe."})
        attrs["document_type"] = document_type
        if document_type.requires_expiration and not attrs.get("expiration_date"):
            raise serializers.ValidationError(
                {"expiration_date": f"El tipo '{document_type.code}' exige fecha de vencimiento."}
            )
        return attrs


class DocumentMetadataUpdateSerializer(serializers.ModelSerializer):
    """Payload de PATCH /documents/{id}/metadata/ (US-007)."""

    document_type = serializers.PrimaryKeyRelatedField(
        queryset=DocumentType.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Document
        fields = ("document_type", "expiration_date", "document_date", "external_sender_name")
        extra_kwargs = {
            "expiration_date": {"required": False, "allow_null": True},
            "document_date": {"required": False, "allow_null": True},
            "external_sender_name": {"required": False, "allow_blank": True},
        }

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Debe enviar al menos un campo de metadatos para actualizar.")
        return attrs


class PresignedUrlSerializer(serializers.Serializer):
    filing_number = serializers.CharField()
    view_url = serializers.CharField()
    expires_in_seconds = serializers.IntegerField(
        default=int(getattr(settings, "AWS_QUERYSTRING_EXPIRE", 900))
    )


class AuditLogSerializer(serializers.ModelSerializer):
    performed_by = serializers.CharField(source="performed_by.username", read_only=True, default=None)
    filing_number = serializers.CharField(source="document.filing_number", read_only=True)
    action_label = serializers.CharField(source="get_action_display", read_only=True)

    class Meta:
        model = AuditLog
        fields = (
            "id",
            "document",
            "filing_number",
            "action",
            "action_label",
            "performed_by",
            "ip_address",
            "user_agent",
            "timestamp",
            "details",
        )
        read_only_fields = fields
