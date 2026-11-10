"""
Endpoints de Mi Portal: /api/v1/client-portal/ (sesión de cliente, ver `auth.py`).

- auth/*: ingreso rápido con código (SMS o correo), ingreso con contraseña y creación de contraseña.
- me/, home/: perfil, contratos y resumen.
- documents/: estados de cuenta, facturas, certificados y contratos publicados en el expediente.
- requests/: requerimientos con seguimiento, chat y adjuntos.
"""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.generics import ListAPIView
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.core.serializers import DocumentTypeSerializer
from apps.customer import services
from apps.customer.auth import ClientTokenAuthentication, IsClient, issue_client_token, session_ttl_seconds
from apps.customer.models import ServiceRequest, ServiceRequestMessage
from apps.customer.serializers import (
    AttachmentSerializer,
    ClientDocumentSerializer,
    ClientDocumentUploadSerializer,
    ContractSummarySerializer,
    MessageCreateSerializer,
    MessageSerializer,
    PasswordLoginSerializer,
    RequestCodeSerializer,
    ServiceRequestCreateSerializer,
    ServiceRequestDetailSerializer,
    ServiceRequestListSerializer,
    SetPasswordSerializer,
    VerifyCodeSerializer,
    validate_attachment,
)
from apps.documents.models import AuditLog, Document
from apps.documents.services.audit import log_action
from apps.documents.services.ingestion import DocumentValidationError, register_document
from apps.documents.services.storage import (
    FILE_UNAVAILABLE_MESSAGE,
    file_exists,
    get_presigned_url,
    presigned_url_ttl_seconds,
)
from apps.portal.services import mask_identification

GENERIC_CODE_MESSAGE = (
    "Si los datos corresponden a un cliente registrado, enviamos un código de verificación. "
    "Vence en 10 minutos."
)
INVALID_CODE_MESSAGE = "El código es incorrecto o ya venció. Solicita uno nuevo."
INVALID_LOGIN_MESSAGE = "Correo o contraseña incorrectos."


class ClientAuthThrottle(AnonRateThrottle):
    scope = "client_auth"


class ClientAPIView(APIView):
    authentication_classes = (ClientTokenAuthentication,)
    permission_classes = (IsClient,)

    @property
    def client(self):
        return self.request.user.client


def _session_payload(account) -> dict:
    return {
        "token": issue_client_token(account),
        "expires_in_seconds": session_ttl_seconds(),
        "account": {
            "email": account.email,
            "client_name": account.client.name,
            "has_password": account.has_password,
        },
    }


# ----------------------------------------------------------------- acceso --
class RequestCodeView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)
    throttle_classes = (ClientAuthThrottle,)

    def post(self, request):
        serializer = RequestCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        client = services.find_client(data["document_type"], data["identification_number"])
        body: dict[str, str] = {"detail": GENERIC_CODE_MESSAGE}
        if client is not None:
            try:
                code, channel = services.request_login_code(client, data["channel"])
            except services.CodeRequestRejected:
                return Response(
                    {"detail": "Espera unos segundos antes de solicitar un nuevo código."},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )
            body["destination"] = services.mask_destination(channel, client)
            body["channel"] = channel
            if getattr(settings, "CLIENT_OTP_DEV_ECHO", False):
                body["dev_code"] = code  # solo desarrollo: sin proveedor SMS no hay otra vía de verlo
        return Response(body)


class VerifyCodeView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)
    throttle_classes = (ClientAuthThrottle,)

    def post(self, request):
        serializer = VerifyCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        client = services.find_client(data["document_type"], data["identification_number"])
        account = services.verify_login_code(client, data["code"]) if client else None
        if account is None:
            return Response({"detail": INVALID_CODE_MESSAGE}, status=status.HTTP_400_BAD_REQUEST)
        return Response(_session_payload(account))


class PasswordLoginView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)
    throttle_classes = (ClientAuthThrottle,)

    def post(self, request):
        serializer = PasswordLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account = services.login_with_password(**serializer.validated_data)
        if account is None:
            return Response({"detail": INVALID_LOGIN_MESSAGE}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(_session_payload(account))


class SetPasswordView(ClientAPIView):
    def post(self, request):
        serializer = SetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account = request.user.account
        account.set_password(serializer.validated_data["password"])
        account.save(update_fields=["password_hash", "updated_at"])
        return Response({"detail": "Contraseña creada. Ya puedes ingresar con tu correo y contraseña."})


# ------------------------------------------------------------ perfil / inicio --
def _executive() -> dict:
    return {
        "name": getattr(settings, "CLIENT_PORTAL_EXECUTIVE_NAME", "Tu ejecutivo de servicio"),
        "email": getattr(settings, "CLIENT_PORTAL_EXECUTIVE_EMAIL", ""),
        "whatsapp": getattr(settings, "CLIENT_PORTAL_EXECUTIVE_WHATSAPP", ""),
    }


def _notifications(client) -> list[dict]:
    limit = timezone.localdate() + timedelta(days=30)
    documents = (
        services.client_documents(client)
        .filter(expiration_date__isnull=False, expiration_date__lte=limit)
        .order_by("expiration_date")[:10]
    )
    today = timezone.localdate()
    return [
        {
            "document_type": doc.document_type.name if doc.document_type else "Documento",
            "contract_number": doc.digital_record.contract.contract_number,
            "expiration_date": doc.expiration_date,
            "expired": doc.expiration_date < today,
        }
        for doc in documents
    ]


class MeView(ClientAPIView):
    def get(self, request):
        client = self.client
        return Response(
            {
                "client": {
                    "name": client.name,
                    "document_type": client.document_type,
                    "identification_number": mask_identification(client.identification_number),
                    "email": client.email,
                },
                "has_password": request.user.account.has_password,
                "contracts": ContractSummarySerializer(services.client_contracts(client), many=True).data,
                "executive": _executive(),
                "notifications": _notifications(client),
            }
        )


class HomeView(ClientAPIView):
    def get(self, request):
        contract = get_object_or_404(
            services.client_contracts(self.client), pk=request.query_params.get("contract")
        )
        documents = services.client_documents(self.client, contract_id=contract.pk)
        counts = {
            category: documents.filter(document_type__code__in=codes).count()
            for category, codes in services.DOCUMENT_CATEGORIES.items()
        }
        days_left = (contract.end_date - timezone.localdate()).days
        return Response(
            {
                "contract": ContractSummarySerializer(contract).data,
                "days_remaining": days_left,
                "document_counts": counts,
                "total_documents": documents.count(),
                "open_requests": ServiceRequest.objects.filter(client=self.client, contract=contract)
                .exclude(status=ServiceRequest.Status.CLOSED)
                .count(),
            }
        )


# -------------------------------------------------------------- documentos --
class DocumentListView(ClientAPIView, ListAPIView):
    serializer_class = ClientDocumentSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get_queryset(self):
        params = self.request.query_params
        category = params.get("category")
        queryset = services.client_documents(
            self.client, category=category, contract_id=params.get("contract")
        )
        if params.get("year", "").isdigit():
            queryset = queryset.filter(document_date__year=int(params["year"]))
        if params.get("month", "").isdigit():
            queryset = queryset.filter(document_date__month=int(params["month"]))
        search = params.get("q", "").strip()
        if search:
            queryset = queryset.filter(
                Q(filing_number__icontains=search) | Q(original_filename__icontains=search)
            )
        return queryset

    def post(self, request):
        """Radicación directa del cliente autenticado en el expediente de uno de sus contratos."""
        serializer = ClientDocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        contract = get_object_or_404(services.client_contracts(self.client), pk=data["contract"].pk)
        try:
            with transaction.atomic():
                document = register_document(
                    file=data["file"],
                    source_channel=Document.SourceChannel.WEB_PORTAL,
                    user=None,
                    digital_record=contract.digital_record,
                    request=None,
                    external_sender_name=self.client.name,
                    document_date=data.get("document_date"),
                )
                document.document_type = data["document_type"]
                if data.get("expiration_date"):
                    document.expiration_date = data["expiration_date"]
                document.save(update_fields=["document_type", "expiration_date", "updated_at"])
                log_action(
                    document,
                    AuditLog.Action.METADATA_UPDATE,
                    details={
                        "source": "mi_portal",
                        "client_account": request.user.account.email,
                        "declared_document_type": data["document_type"].code,
                    },
                )
        except DocumentValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        received_at = timezone.localtime(document.created_at)
        return Response(
            {
                "filing_number": document.filing_number,
                "received_at_display": received_at.strftime("%d/%m/%Y %H:%M:%S (%Z)"),
                "contract_number": contract.contract_number,
                "document_type": data["document_type"].name,
                "original_filename": document.original_filename,
            },
            status=status.HTTP_201_CREATED,
        )


class DocumentOptionsView(ClientAPIView):
    def get(self, request):
        return Response(
            {"document_types": DocumentTypeSerializer(services.publishable_document_types(), many=True).data}
        )


class DocumentDownloadView(ClientAPIView):
    def get(self, request, pk):
        document = get_object_or_404(services.client_documents(self.client), pk=pk)
        if not file_exists(document.file_path):
            return Response({"detail": FILE_UNAVAILABLE_MESSAGE}, status=status.HTTP_404_NOT_FOUND)
        url = get_presigned_url(document.file_path)
        log_action(
            document,
            AuditLog.Action.DOWNLOAD,
            details={
                "source": "mi_portal",
                "client_account": request.user.account.email,
                "storage_key": document.file_path,
            },
        )
        return Response(
            {
                "download_url": url,
                "original_filename": document.original_filename,
                "expires_in_seconds": presigned_url_ttl_seconds(),
            }
        )


# ---------------------------------------------------------- requerimientos --
class CatalogView(ClientAPIView):
    def get(self, request):
        return Response(services.catalog_entries())


class ServiceRequestListCreateView(ClientAPIView):
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get(self, request):
        queryset = ServiceRequest.objects.filter(client=self.client).select_related("contract")
        search = request.query_params.get("q", "").strip()
        if search:
            filters = (
                Q(subject__icontains=search) | Q(service__icontains=search) | Q(subcategory__icontains=search)
            )
            if search.lstrip("#").isdigit():
                filters |= Q(pk=int(search.lstrip("#")))
            queryset = queryset.filter(filters)
        return Response(ServiceRequestListSerializer(queryset, many=True).data)

    def post(self, request):
        data = {key: request.data.get(key) for key in ("contract", "catalog_id", "subject", "description")}
        data["files"] = request.FILES.getlist("files")
        serializer = ServiceRequestCreateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        valid = serializer.validated_data
        contract = get_object_or_404(services.client_contracts(self.client), pk=valid["contract"].pk)
        service_request = services.create_service_request(
            client=self.client,
            contract=contract,
            catalog_id=valid["catalog_id"],
            subject=valid["subject"],
            description=valid["description"],
            files=valid.get("files", []),
        )
        return Response(ServiceRequestDetailSerializer(service_request).data, status=status.HTTP_201_CREATED)


class ServiceRequestMixin:
    client: object

    def get_request_object(self, pk) -> ServiceRequest:
        return get_object_or_404(
            ServiceRequest.objects.select_related("contract", "client"), pk=pk, client=self.client
        )


class ServiceRequestDetailView(ServiceRequestMixin, ClientAPIView):
    def get(self, request, pk):
        return Response(ServiceRequestDetailSerializer(self.get_request_object(pk)).data)


class ServiceRequestMessageView(ServiceRequestMixin, ClientAPIView):
    def post(self, request, pk):
        service_request = self.get_request_object(pk)
        if service_request.is_closed:
            return Response(
                {"detail": "El requerimiento está cerrado y no permite nuevos comentarios."},
                status=status.HTTP_409_CONFLICT,
            )
        serializer = MessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = ServiceRequestMessage.objects.create(
            request=service_request,
            author_type=ServiceRequestMessage.Author.CLIENT,
            author_name=self.client.name,
            body=serializer.validated_data["body"].strip(),
        )
        return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)


class ServiceRequestAttachmentView(ServiceRequestMixin, ClientAPIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, pk):
        service_request = self.get_request_object(pk)
        if service_request.is_closed:
            return Response(
                {"detail": "El requerimiento está cerrado y no permite nuevos adjuntos."},
                status=status.HTTP_409_CONFLICT,
            )
        files = request.FILES.getlist("files")
        if not files:
            return Response({"detail": "Adjunta al menos un archivo."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            for file in files:
                validate_attachment(file)
        except DRFValidationError as exc:
            return Response(
                {"detail": " ".join(str(e) for e in exc.detail)}, status=status.HTTP_400_BAD_REQUEST
            )
        created = [services.add_attachment(service_request, file, from_client=True) for file in files]
        return Response(AttachmentSerializer(created, many=True).data, status=status.HTTP_201_CREATED)


class ServiceRequestAttachmentDownloadView(ServiceRequestMixin, ClientAPIView):
    def get(self, request, pk, attachment_id):
        service_request = self.get_request_object(pk)
        attachment = get_object_or_404(service_request.attachments, pk=attachment_id)
        if not file_exists(attachment.file_path):
            return Response({"detail": FILE_UNAVAILABLE_MESSAGE}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            {
                "download_url": get_presigned_url(attachment.file_path),
                "original_filename": attachment.original_filename,
                "expires_in_seconds": presigned_url_ttl_seconds(),
            }
        )
