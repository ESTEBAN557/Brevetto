"""Endpoints REST del núcleo: /api/v1/clients/, /api/v1/contracts/, /api/v1/document-types/."""
from __future__ import annotations

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.models import Client, Contract, DocumentType
from apps.core.serializers import ClientSerializer, ContractSerializer, DocumentTypeSerializer
from apps.core.services import create_contract
from apps.documents.models import AuditLog
from apps.documents.serializers import AuditLogSerializer, DocumentSerializer


class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_fields = ("client_type", "document_type")
    search_fields = ("name", "identification_number", "email")
    ordering_fields = ("name", "created_at")
    http_method_names = ("get", "post", "patch", "put", "head", "options")  # sin DELETE: PROTECT


class ContractViewSet(viewsets.ModelViewSet):
    """US-008: al crear un contrato se genera su expediente digital y su carpeta en S3."""

    queryset = Contract.objects.select_related("client", "digital_record").all()
    serializer_class = ContractSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_fields = ("status", "client")
    search_fields = ("contract_number", "client__name", "client__identification_number", "property_address")
    ordering_fields = ("start_date", "end_date", "contract_number", "created_at")
    http_method_names = ("get", "post", "patch", "put", "head", "options")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        contract = create_contract(**serializer.validated_data)
        contract = self.get_queryset().get(pk=contract.pk)
        output = self.get_serializer(contract)
        headers = self.get_success_headers(output.data)
        return Response(output.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=["get"], url_path="documents")
    def documents(self, request, pk=None):
        """Expediente digital: documentos del contrato, cronológicos y filtrables por tipo."""
        contract = self.get_object()
        queryset = (
            contract.digital_record.documents.select_related(
                "document_type", "registered_by", "digital_record__contract__client"
            )
            .order_by("-created_at")
        )
        document_type = request.query_params.get("document_type")
        if document_type:
            queryset = queryset.filter(document_type__code=document_type)
        category = request.query_params.get("category")
        if category:
            queryset = queryset.filter(document_type__category=category)

        page = self.paginate_queryset(queryset)
        serializer = DocumentSerializer(page if page is not None else queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="audit-trail")
    def audit_trail(self, request, pk=None):
        """Historial de todas las acciones sobre los documentos del expediente."""
        contract = self.get_object()
        logs = (
            AuditLog.objects.filter(document__digital_record__contract=contract)
            .select_related("performed_by", "document")
            .order_by("-timestamp")
        )
        page = self.paginate_queryset(logs)
        serializer = AuditLogSerializer(page if page is not None else logs, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)


class DocumentTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DocumentType.objects.all()
    serializer_class = DocumentTypeSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    filterset_fields = ("category", "requires_expiration")
    search_fields = ("code", "name")
    pagination_class = None
