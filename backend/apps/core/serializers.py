"""Serializers DRF del núcleo: clientes, contratos, expedientes y tipos documentales."""
from __future__ import annotations

from rest_framework import serializers

from apps.core.models import Client, Contract, DigitalRecord, DocumentType


class ClientSerializer(serializers.ModelSerializer):
    contracts_count = serializers.IntegerField(source="contracts.count", read_only=True)

    class Meta:
        model = Client
        fields = (
            "id",
            "name",
            "document_type",
            "identification_number",
            "email",
            "phone",
            "client_type",
            "contracts_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "contracts_count", "created_at", "updated_at")


class DocumentTypeSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = DocumentType
        fields = (
            "id",
            "code",
            "name",
            "category",
            "category_label",
            "requires_expiration",
            "description",
        )
        read_only_fields = ("id",)


class DigitalRecordSerializer(serializers.ModelSerializer):
    documents_count = serializers.IntegerField(source="documents.count", read_only=True)

    class Meta:
        model = DigitalRecord
        fields = ("id", "storage_path", "documents_count", "created_at")
        read_only_fields = fields


class ContractSerializer(serializers.ModelSerializer):
    """Escritura por `client` (UUID); lectura con cliente anidado y expediente digital."""

    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all())
    client_detail = ClientSerializer(source="client", read_only=True)
    digital_record = DigitalRecordSerializer(read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Contract
        fields = (
            "id",
            "contract_number",
            "client",
            "client_detail",
            "property_address",
            "start_date",
            "end_date",
            "status",
            "status_label",
            "digital_record",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "client_detail", "digital_record", "status_label", "created_at", "updated_at")

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and end < start:
            raise serializers.ValidationError(
                {"end_date": "La fecha de fin no puede ser anterior a la fecha de inicio."}
            )
        return attrs
