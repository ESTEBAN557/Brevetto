"""
Endpoints REST de radicación y documentos: /api/v1/documents/ (docs/04_API_SPECIFICATION.md).

Las respuestas HTTP se mantienen bajo 2 s: la única operación pesada dentro del
request es la subida al bucket; el análisis con IA corre en Celery.
"""
from __future__ import annotations

from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from rest_framework.views import APIView

from apps.documents.filters import AuditLogFilter, DocumentFilter
from apps.documents.models import AuditLog, Document
from apps.documents.services import metrics as metrics_service
from apps.documents.services.expirations import alert_window_days, expiring_documents_queryset
from apps.documents.serializers import (
    AuditLogSerializer,
    DocumentBatchUploadSerializer,
    DocumentMetadataUpdateSerializer,
    DocumentReceiptSerializer,
    DocumentSerializer,
    DocumentUploadSerializer,
    DocumentValidateSerializer,
    PresignedUrlSerializer,
)
from apps.documents.services.audit import log_action
from apps.documents.services.ingestion import register_document, register_documents_batch
from apps.documents.services.storage import get_presigned_url, presigned_url_ttl_seconds


class DocumentViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """Consulta de documentos radicados y acciones de radicación / validación."""

    queryset = (
        Document.objects.select_related(
            "document_type",
            "registered_by",
            "digital_record__contract__client",
        )
        .all()
    )
    serializer_class = DocumentSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_class = DocumentFilter
    search_fields = (
        "filing_number",
        "original_filename",
        "external_sender_name",
        "digital_record__contract__contract_number",
        "digital_record__contract__client__name",
        "digital_record__contract__client__identification_number",
    )
    ordering_fields = ("created_at", "expiration_date", "document_date", "ai_confidence_score", "filing_number")
    ordering = ("-created_at",)

    # ----------------------------------------------------------- vencimientos --
    @action(detail=False, methods=["get"], url_path="expiring")
    def expiring(self, request):
        """Documentos vencidos o por vencer (ventana `days`, 30 por defecto) para el panel de alertas."""
        try:
            days = int(request.query_params.get("days", alert_window_days()))
        except ValueError:
            return Response({"days": "Debe ser un entero."}, status=status.HTTP_400_BAD_REQUEST)
        days = max(0, min(days, 365))
        include_expired = str(request.query_params.get("include_expired", "true")).lower() not in ("false", "0", "no")
        try:
            limit = max(1, min(int(request.query_params.get("limit", 50)), 200))
        except ValueError:
            limit = 50

        today = timezone.localdate()
        queryset = expiring_documents_queryset(days, include_expired=include_expired, today=today)
        documents = list(queryset[:limit])
        expired = sum(1 for d in documents if d.expiration_date < today)
        return Response(
            {
                "as_of": today.isoformat(),
                "days": days,
                "count": queryset.count(),
                "expired": expired,
                "expiring_soon": len(documents) - expired,
                "results": self.get_serializer(documents, many=True).data,
            }
        )

    # ------------------------------------------------------------- radicación --
    @action(
        detail=False,
        methods=["post"],
        url_path="upload",
        parser_classes=(MultiPartParser, FormParser),
    )
    def upload(self, request):
        """US-002/004/005/006: radica un documento y encola su procesamiento."""
        serializer = DocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        document = register_document(
            file=data["file"],
            source_channel=data["source_channel"],
            user=request.user,
            digital_record=data.get("digital_record"),
            request=request,
            external_sender_name=data.get("external_sender_name", ""),
            document_date=data.get("document_date"),
        )
        return Response(DocumentReceiptSerializer(document).data, status=status.HTTP_201_CREATED)

    @action(
        detail=False,
        methods=["post"],
        url_path="batch-upload",
        parser_classes=(MultiPartParser, FormParser),
    )
    def batch_upload(self, request):
        """US-011: radica varios documentos en un solo envío."""
        serializer = DocumentBatchUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        documents = register_documents_batch(
            files=data["files"],
            source_channel=data["source_channel"],
            user=request.user,
            digital_record=data.get("digital_record"),
            request=request,
        )
        items = [
            {
                "id": str(doc.pk),
                "filing_number": doc.filing_number,
                "filename": doc.original_filename,
                "status": doc.processing_status,
            }
            for doc in documents
        ]
        return Response(
            {
                "message": f"{len(items)} documentos recibidos para radicación y procesamiento asíncrono.",
                "items": items,
            },
            status=status.HTTP_202_ACCEPTED,
        )

    # ----------------------------------------------------------- bandeja HITL --
    @action(detail=False, methods=["get"], url_path="pending-review")
    def pending_review(self, request):
        queryset = self.filter_queryset(
            self.get_queryset().filter(processing_status=Document.ProcessingStatus.NEEDS_REVIEW)
        ).order_by("created_at")
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page if page is not None else queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="validate")
    def validate(self, request, pk=None):
        """Confirmación o corrección humana: archiva el documento en el expediente."""
        document = self.get_object()
        serializer = DocumentValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        previous = {
            "processing_status": document.processing_status,
            "contract_number": (
                document.digital_record.contract.contract_number if document.digital_record else None
            ),
            "document_type": document.document_type.code if document.document_type else None,
            "expiration_date": document.expiration_date.isoformat() if document.expiration_date else None,
        }

        with transaction.atomic():
            document.digital_record = data["contract"].digital_record
            document.document_type = data["document_type"]
            if data.get("expiration_date") is not None:
                document.expiration_date = data["expiration_date"]
            if data.get("document_date") is not None:
                document.document_date = data["document_date"]
            document.processing_status = Document.ProcessingStatus.PROCESSED
            document.save()

            log_action(
                document,
                AuditLog.Action.HUMAN_VALIDATE,
                request=request,
                details={
                    "previous": previous,
                    "new": {
                        "processing_status": document.processing_status,
                        "contract_number": data["contract"].contract_number,
                        "document_type": data["document_type"].code,
                        "expiration_date": (
                            document.expiration_date.isoformat() if document.expiration_date else None
                        ),
                    },
                    "ai_confidence_score": document.ai_confidence_score,
                    "ai_suggested_contract": (document.ai_extracted_data or {}).get("contract_number"),
                },
            )

        document.refresh_from_db()
        return Response(self.get_serializer(document).data, status=status.HTTP_200_OK)

    # -------------------------------------------------------------- metadatos --
    @action(detail=True, methods=["patch"], url_path="metadata")
    def metadata(self, request, pk=None):
        """US-007: actualiza metadatos y registra estado anterior / nuevo en AuditLog."""
        document = self.get_object()
        serializer = DocumentMetadataUpdateSerializer(document, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        def snapshot(doc: Document) -> dict:
            return {
                "document_type": doc.document_type.code if doc.document_type else None,
                "expiration_date": doc.expiration_date.isoformat() if doc.expiration_date else None,
                "document_date": doc.document_date.isoformat() if doc.document_date else None,
                "external_sender_name": doc.external_sender_name,
            }

        previous = snapshot(document)
        with transaction.atomic():
            document = serializer.save()
            current = snapshot(document)
            changed = {k: {"before": previous[k], "after": current[k]} for k in current if previous[k] != current[k]}
            log_action(
                document,
                AuditLog.Action.METADATA_UPDATE,
                request=request,
                details={"changes": changed, "fields": list(changed.keys())},
            )
        return Response(self.get_serializer(document).data)

    # ------------------------------------------------------ consulta y descarga --
    @action(detail=True, methods=["get"], url_path="view-url")
    def view_url(self, request, pk=None):
        """URL prefirmada de lectura (15 min) + registro de CONSULTA_VISUAL."""
        document = self.get_object()
        url = get_presigned_url(document.file_path)
        log_action(
            document,
            AuditLog.Action.VIEW,
            request=request,
            details={"storage_key": document.file_path, "expires_in_seconds": presigned_url_ttl_seconds()},
        )
        payload = PresignedUrlSerializer(
            {
                "filing_number": document.filing_number,
                "view_url": url,
                "expires_in_seconds": presigned_url_ttl_seconds(),
            }
        ).data
        return Response(payload)

    @action(detail=True, methods=["get"], url_path="download-url")
    def download_url(self, request, pk=None):
        """Igual que view-url pero deja rastro de DESCARGA."""
        document = self.get_object()
        url = get_presigned_url(document.file_path)
        log_action(
            document,
            AuditLog.Action.DOWNLOAD,
            request=request,
            details={"storage_key": document.file_path, "expires_in_seconds": presigned_url_ttl_seconds()},
        )
        return Response(
            {
                "filing_number": document.filing_number,
                "download_url": url,
                "original_filename": document.original_filename,
                "expires_in_seconds": presigned_url_ttl_seconds(),
            }
        )

    # -------------------------------------------------------------- auditoría --
    @action(detail=True, methods=["get"], url_path="audit-trail")
    def audit_trail(self, request, pk=None):
        document = self.get_object()
        logs = document.audit_logs.select_related("performed_by", "document").order_by("-timestamp")
        page = self.paginate_queryset(logs)
        serializer = AuditLogSerializer(page if page is not None else logs, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)


class AuditLogViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """Módulo global de auditoría (US-023/024/025): solo lectura, paginado y filtrable.

    La tabla es append-only: además del ORM, triggers BEFORE UPDATE/DELETE en
    PostgreSQL impiden cualquier modificación o borrado (migración documents.0002).
    """

    queryset = AuditLog.objects.select_related(
        "performed_by", "document", "document__digital_record__contract"
    ).all()
    serializer_class = AuditLogSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    filterset_class = AuditLogFilter
    ordering_fields = ("timestamp", "action")
    ordering = ("-timestamp",)

    @action(detail=False, methods=["get"], url_path="actions")
    def actions(self, request):
        """Catálogo de acciones con conteos, para los selectores del frontend."""
        counts = dict(
            self.filter_queryset(self.get_queryset())
            .values_list("action")
            .annotate(total=Count("id"))
            .values_list("action", "total")
        )
        return Response(
            [
                {"code": choice.value, "label": choice.label, "count": counts.get(choice.value, 0)}
                for choice in AuditLog.Action
            ]
        )


class MetricsSummaryView(APIView):
    """KPIs ejecutivos de gestión documental para Coltebienes."""

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        try:
            period_days = int(request.query_params.get("days", 30))
        except ValueError:
            return Response({"days": "Debe ser un entero."}, status=status.HTTP_400_BAD_REQUEST)
        period_days = max(1, min(period_days, 365))
        return Response(metrics_service.summary(period_days))
