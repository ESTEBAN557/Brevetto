"""
Endpoints del portal externo de inquilinos: /api/v1/portal/ (sin autenticación JWT).

- verify-contract: valida NIT/Cédula + número de contrato y emite un token temporal.
- submit-document: radica un documento asociado al contrato del token y devuelve el comprobante.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.core.serializers import DocumentTypeSerializer
from apps.documents.models import AuditLog, Document
from apps.documents.services.audit import log_action
from apps.documents.services.ingestion import register_document
from apps.portal.serializers import PortalSubmitSerializer, VerifyContractSerializer
from apps.portal.services import (
    PortalTokenError,
    PortalVerificationError,
    expiring_documents,
    issue_portal_token,
    mask_identification,
    portal_document_types,
    receipt_signature,
    resolve_portal_token,
    session_ttl_seconds,
    verify_contract,
)

GENERIC_VERIFY_ERROR = "No encontramos un contrato vigente con los datos suministrados."


class PortalVerifyThrottle(AnonRateThrottle):
    scope = "portal_verify"


class PortalSubmitThrottle(AnonRateThrottle):
    scope = "portal_submit"


def _extract_token(request) -> str:
    return (
        request.headers.get("X-Portal-Token")
        or request.data.get("portal_token")
        or request.query_params.get("portal_token")
        or ""
    )


class VerifyContractView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()
    throttle_classes = (PortalVerifyThrottle,)

    def post(self, request):
        serializer = VerifyContractSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            contract = verify_contract(**serializer.validated_data)
        except PortalVerificationError:
            return Response({"detail": GENERIC_VERIFY_ERROR}, status=status.HTTP_404_NOT_FOUND)

        expiring = [
            {
                "filing_number": doc.filing_number,
                "document_type": doc.document_type.name if doc.document_type else None,
                "expiration_date": doc.expiration_date,
                "expired": doc.expiration_date < timezone.localdate(),
            }
            for doc in expiring_documents(contract)
        ]
        return Response(
            {
                "portal_token": issue_portal_token(contract),
                "expires_in_seconds": session_ttl_seconds(),
                "contract": {
                    "contract_number": contract.contract_number,
                    "property_address": contract.property_address,
                    "status": contract.status,
                    "start_date": contract.start_date,
                    "end_date": contract.end_date,
                },
                "client": {
                    "name": contract.client.name,
                    "identification_number": mask_identification(contract.client.identification_number),
                },
                "document_types": DocumentTypeSerializer(portal_document_types(), many=True).data,
                "expiring_documents": expiring,
            }
        )


class SubmitDocumentView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()
    throttle_classes = (PortalSubmitThrottle,)
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        try:
            contract = resolve_portal_token(_extract_token(request))
        except PortalTokenError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = PortalSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            document = register_document(
                file=data["file"],
                source_channel=Document.SourceChannel.WEB_PORTAL,
                user=None,
                digital_record=contract.digital_record,
                request=request,
                external_sender_name=data["sender_name"],
                document_date=data.get("document_date"),
            )
            # El inquilino declara el tipo; la IA lo verificará y el personal lo confirmará.
            document.document_type = data["document_type"]
            if data.get("expiration_date"):
                document.expiration_date = data["expiration_date"]
            document.save(update_fields=["document_type", "expiration_date", "updated_at"])
            log_action(
                document,
                AuditLog.Action.METADATA_UPDATE,
                request=request,
                details={
                    "source": "portal_web",
                    "declared_document_type": data["document_type"].code,
                    "declared_expiration_date": (
                        data["expiration_date"].isoformat() if data.get("expiration_date") else None
                    ),
                    "sender_name": data["sender_name"],
                },
            )

        received_at = timezone.localtime(document.created_at)
        return Response(
            {
                "filing_number": document.filing_number,
                "received_at": received_at.isoformat(),
                "received_at_display": received_at.strftime("%d/%m/%Y %H:%M:%S (%Z)"),
                "contract_number": contract.contract_number,
                "client_name": contract.client.name,
                "document_type": data["document_type"].name,
                "original_filename": document.original_filename,
                "file_size_bytes": document.file_size_bytes,
                "file_hash": document.file_hash,
                "sender_name": data["sender_name"],
                "processing_status": document.processing_status,
                "receipt_signature": receipt_signature(document.filing_number, document.file_hash),
            },
            status=status.HTTP_201_CREATED,
        )
