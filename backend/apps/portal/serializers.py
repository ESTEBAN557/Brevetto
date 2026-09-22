"""Serializers del portal público (docs/04 §2)."""
from __future__ import annotations

from rest_framework import serializers

from apps.core.models import DocumentType
from apps.documents.serializers import _validate_file


class VerifyContractSerializer(serializers.Serializer):
    contract_number = serializers.CharField(max_length=100)
    identification_number = serializers.CharField(max_length=50)


class PortalSubmitSerializer(serializers.Serializer):
    file = serializers.FileField()
    document_type_code = serializers.CharField(max_length=50)
    sender_name = serializers.CharField(max_length=255)
    expiration_date = serializers.DateField(required=False, allow_null=True)
    document_date = serializers.DateField(required=False, allow_null=True)

    def validate_file(self, file):
        return _validate_file(file)

    def validate(self, attrs):
        code = attrs["document_type_code"].strip().upper()
        document_type = DocumentType.objects.filter(code=code).first()
        if document_type is None:
            raise serializers.ValidationError({"document_type_code": "Tipo documental no válido."})
        if document_type.requires_expiration and not attrs.get("expiration_date"):
            raise serializers.ValidationError(
                {"expiration_date": f"El documento '{document_type.name}' requiere fecha de vencimiento."}
            )
        attrs["document_type"] = document_type
        return attrs
