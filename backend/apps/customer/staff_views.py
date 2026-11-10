"""
Atención de requerimientos por el personal de Coltebienes: /api/v1/service-requests/ (JWT).

Hasta el Sprint 2 el personal solo podía gestionar los requerimientos desde el admin de Django. Estos
endpoints alimentan la pantalla /admin/requerimientos del panel: bandeja con filtros, cambio de estado,
asignación, respuesta en el chat y adjuntos. Cada cambio deja rastro en la línea de seguimiento que ve
el cliente en Mi Portal, y el cliente recibe un aviso por correo.
"""

from __future__ import annotations

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.generics import ListAPIView
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.customer import services
from apps.customer.models import ServiceRequest, ServiceRequestMessage
from apps.customer.serializers import (
    AttachmentSerializer,
    MessageCreateSerializer,
    MessageSerializer,
    ServiceRequestDetailSerializer,
    ServiceRequestListSerializer,
    validate_attachment,
)
from apps.documents.services.storage import (
    FILE_UNAVAILABLE_MESSAGE,
    file_exists,
    get_presigned_url,
    presigned_url_ttl_seconds,
)

CLOSED_MESSAGE = "El requerimiento está cerrado y ya no admite cambios, mensajes ni adjuntos."


def staff_name(user) -> str:
    return user.get_full_name() or user.username


class StaffRequestListSerializer(ServiceRequestListSerializer):
    client_name = serializers.CharField(source="client.name", read_only=True)
    client_identification = serializers.CharField(source="client.identification_number", read_only=True)
    message_count = serializers.IntegerField(read_only=True)
    attachment_count = serializers.IntegerField(read_only=True)

    class Meta(ServiceRequestListSerializer.Meta):
        fields = ServiceRequestListSerializer.Meta.fields + (
            "case_type", "client_name", "client_identification", "message_count", "attachment_count",
            "updated_at",
        )  # fmt: skip


class StaffRequestDetailSerializer(ServiceRequestDetailSerializer):
    client_name = serializers.CharField(source="client.name", read_only=True)
    client_identification = serializers.CharField(source="client.identification_number", read_only=True)
    client_email = serializers.CharField(source="client.email", read_only=True)
    client_phone = serializers.CharField(source="client.phone", read_only=True)
    contract_id = serializers.UUIDField(source="contract.id", read_only=True)

    class Meta(ServiceRequestDetailSerializer.Meta):
        fields = ServiceRequestDetailSerializer.Meta.fields + (
            "client_name", "client_identification", "client_email", "client_phone", "contract_id",
        )  # fmt: skip


class StaffRequestUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ServiceRequest.Status.choices, required=False)
    assigned_to = serializers.CharField(max_length=120, required=False, allow_blank=True)
    solution = serializers.CharField(max_length=5000, required=False, allow_blank=True)
    note = serializers.CharField(max_length=1000, required=False, allow_blank=True)

    def validate(self, attrs):
        if not any(key in attrs for key in ("status", "assigned_to", "solution", "note")):
            raise serializers.ValidationError(
                "Indica al menos un cambio (estado, asignación, solución o nota)."
            )
        return attrs


def annotated_queryset():
    return ServiceRequest.objects.select_related("client", "contract").annotate(
        message_count=Count("messages", distinct=True),
        attachment_count=Count("attachments", distinct=True),
    )


class StaffRequestListView(ListAPIView):
    """Bandeja de requerimientos: filtros `status` (uno o varios separados por coma) y `q`."""

    permission_classes = (IsAuthenticated,)
    serializer_class = StaffRequestListSerializer

    def get_queryset(self):
        queryset = annotated_queryset().order_by("-created_at")
        status_param = self.request.query_params.get("status", "").strip()
        if status_param:
            queryset = queryset.filter(status__in=[s for s in status_param.split(",") if s])
        search = self.request.query_params.get("q", "").strip()
        if search:
            filters = (
                Q(subject__icontains=search)
                | Q(subcategory__icontains=search)
                | Q(client__name__icontains=search)
                | Q(client__identification_number__icontains=search)
                | Q(contract__contract_number__icontains=search)
                | Q(assigned_to__icontains=search)
            )
            if search.lstrip("#").isdigit():
                filters |= Q(pk=int(search.lstrip("#")))
            queryset = queryset.filter(filters)
        return queryset


class StaffRequestSummaryView(APIView):
    """Conteo por estado para las pestañas de la bandeja y el contador del menú."""

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        counts = dict(ServiceRequest.objects.values_list("status").annotate(total=Count("id")))
        by_status = [
            {"code": choice.value, "label": choice.label, "count": counts.get(choice.value, 0)}
            for choice in ServiceRequest.Status
        ]
        open_count = sum(
            item["count"] for item in by_status if item["code"] != ServiceRequest.Status.CLOSED.value
        )
        return Response({"total": sum(counts.values()), "open": open_count, "by_status": by_status})


class StaffRequestMixin:
    def get_request_object(self, pk) -> ServiceRequest:
        return get_object_or_404(ServiceRequest.objects.select_related("client", "contract"), pk=pk)


class StaffRequestDetailView(StaffRequestMixin, APIView):
    permission_classes = (IsAuthenticated,)
    parser_classes = (JSONParser,)

    def get(self, request, pk):
        return Response(StaffRequestDetailSerializer(self.get_request_object(pk)).data)

    def patch(self, request, pk):
        service_request = self.get_request_object(pk)
        serializer = StaffRequestUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            services.staff_update_request(
                service_request,
                actor=staff_name(request.user),
                status=data.get("status"),
                assigned_to=data.get("assigned_to"),
                solution=data.get("solution"),
                note=data.get("note", ""),
            )
        except services.ServiceRequestClosed:
            return Response({"detail": CLOSED_MESSAGE}, status=status.HTTP_409_CONFLICT)
        except services.SolutionRequired:
            return Response(
                {
                    "solution": [
                        "Registra la solución antes de marcar el requerimiento como resuelto o cerrado."
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(StaffRequestDetailSerializer(self.get_request_object(pk)).data)


class StaffRequestMessageView(StaffRequestMixin, APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, pk):
        service_request = self.get_request_object(pk)
        if service_request.is_closed:
            return Response({"detail": CLOSED_MESSAGE}, status=status.HTTP_409_CONFLICT)
        serializer = MessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = ServiceRequestMessage.objects.create(
            request=service_request,
            author_type=ServiceRequestMessage.Author.STAFF,
            author_name=staff_name(request.user),
            body=serializer.validated_data["body"].strip(),
        )
        services.notify_client(
            service_request,
            "Tienes una nueva respuesta",
            f"{message.author_name} de Coltebienes respondió tu requerimiento:\n\n{message.body}",
        )
        return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)


class StaffRequestAttachmentView(StaffRequestMixin, APIView):
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, pk):
        service_request = self.get_request_object(pk)
        if service_request.is_closed:
            return Response({"detail": CLOSED_MESSAGE}, status=status.HTTP_409_CONFLICT)
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
        created = [services.add_attachment(service_request, file, from_client=False) for file in files]
        return Response(AttachmentSerializer(created, many=True).data, status=status.HTTP_201_CREATED)


class StaffRequestAttachmentDownloadView(StaffRequestMixin, APIView):
    permission_classes = (IsAuthenticated,)

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
