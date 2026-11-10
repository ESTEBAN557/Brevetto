"""Serializadores de Mi Portal (solo exponen lo que el cliente puede ver)."""

from __future__ import annotations

import os

from rest_framework import serializers

from apps.core.models import Client, Contract
from apps.customer import services
from apps.customer.models import (
    LoginCode,
    ServiceRequest,
    ServiceRequestAttachment,
    ServiceRequestEvent,
    ServiceRequestMessage,
)
from apps.documents.models import Document
from apps.portal.services import mask_identification

MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
ATTACHMENT_EXTENSIONS = {
    ".pdf", ".jpg", ".jpeg", ".png", ".webp", ".doc", ".docx", ".xls", ".xlsx",
    ".mp4", ".mov", ".avi", ".webm", ".mp3", ".wav", ".ogg", ".m4a",
}  # fmt: skip


def validate_attachment(file) -> None:
    extension = os.path.splitext(file.name)[1].lower()
    if extension not in ATTACHMENT_EXTENSIONS:
        raise serializers.ValidationError(f"Formato no permitido: {extension or 'sin extensión'}.")
    if file.size > MAX_ATTACHMENT_BYTES:
        raise serializers.ValidationError(f"«{file.name}» supera los 10 MB permitidos.")
    if file.size == 0:
        raise serializers.ValidationError(f"«{file.name}» está vacío.")


class RequestCodeSerializer(serializers.Serializer):
    document_type = serializers.ChoiceField(choices=Client.IdentificationType.choices)
    identification_number = serializers.CharField(max_length=50)
    channel = serializers.ChoiceField(choices=LoginCode.Channel.choices, default=LoginCode.Channel.SMS)


class VerifyCodeSerializer(serializers.Serializer):
    document_type = serializers.ChoiceField(choices=Client.IdentificationType.choices)
    identification_number = serializers.CharField(max_length=50)
    code = serializers.CharField(min_length=6, max_length=6)


class PasswordLoginSerializer(serializers.Serializer):
    email = serializers.CharField(max_length=254)
    password = serializers.CharField(max_length=128, trim_whitespace=False)


class SetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(min_length=8, max_length=128, trim_whitespace=False)


class ContractSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Contract
        fields = ("id", "contract_number", "property_address", "status", "start_date", "end_date")


class ClientDocumentSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    document_type_name = serializers.CharField(source="document_type.name", default=None)
    document_type_code = serializers.CharField(source="document_type.code", default=None)
    contract_number = serializers.CharField(source="digital_record.contract.contract_number", default=None)
    property_address = serializers.CharField(source="digital_record.contract.property_address", default=None)
    detail = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = (
            "id", "filing_number", "title", "document_type_name", "document_type_code", "contract_number",
            "property_address", "document_date", "expiration_date", "created_at", "original_filename",
            "file_size_bytes", "detail",
        )  # fmt: skip

    def get_title(self, obj: Document) -> str:
        return os.path.splitext(obj.original_filename)[0]

    def get_detail(self, obj: Document) -> dict:
        # Solo se listan documentos archivados en un expediente (ver services.client_documents).
        assert obj.digital_record is not None
        client = obj.digital_record.contract.client
        return {
            "beneficiary": {
                "name": client.name,
                "identification_type": client.document_type,
                "identification_number": mask_identification(client.identification_number),
                "email": client.email,
            },
            "transaction": {
                "filing_number": obj.filing_number,
                "document_date": obj.document_date,
                "registered_at": obj.created_at,
                "channel": obj.get_source_channel_display(),
            },
        }


class ClientDocumentUploadSerializer(serializers.Serializer):
    contract = serializers.PrimaryKeyRelatedField(queryset=Contract.objects.all())
    document_type: serializers.SlugRelatedField = serializers.SlugRelatedField(
        slug_field="code", queryset=services.publishable_document_types()
    )
    file = serializers.FileField()
    document_date = serializers.DateField(required=False, allow_null=True)
    expiration_date = serializers.DateField(required=False, allow_null=True)


class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceRequestAttachment
        fields = ("id", "from_client", "original_filename", "file_size_bytes", "mime_type", "created_at")


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceRequestMessage
        fields = ("id", "author_type", "author_name", "body", "created_at")


class EventSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = ServiceRequestEvent
        fields = ("id", "status", "status_display", "actor", "note", "created_at")


class ServiceRequestListSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    contract_number = serializers.CharField(source="contract.contract_number", read_only=True)

    class Meta:
        model = ServiceRequest
        fields: tuple[str, ...] = (
            "id", "subject", "created_at", "service", "subcategory", "assigned_to", "status", "status_display",
            "contract_number",
        )  # fmt: skip


class ServiceRequestDetailSerializer(ServiceRequestListSerializer):
    events = EventSerializer(many=True, read_only=True)
    messages = MessageSerializer(many=True, read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)
    property_address = serializers.CharField(source="contract.property_address", read_only=True)
    reported_by = serializers.CharField(source="client.name", read_only=True)

    class Meta(ServiceRequestListSerializer.Meta):
        fields = ServiceRequestListSerializer.Meta.fields + (
            "case_type", "description", "solution", "updated_at", "property_address", "reported_by", "events",
            "messages", "attachments",
        )  # fmt: skip


class ServiceRequestCreateSerializer(serializers.Serializer):
    contract = serializers.PrimaryKeyRelatedField(queryset=Contract.objects.all())
    catalog_id = serializers.IntegerField(min_value=0, max_value=len(services.REQUEST_CATALOG) - 1)
    subject = serializers.CharField(max_length=200)
    description = serializers.CharField(max_length=5000)
    files = serializers.ListField(child=serializers.FileField(), required=False, max_length=10)

    def validate_files(self, files):
        for file in files:
            validate_attachment(file)
        return files


class MessageCreateSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=3000)
