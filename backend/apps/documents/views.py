"""Vistas del módulo de documentos."""
from rest_framework import generics, status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.documents.models import Document
from apps.documents.serializers import (
    DocumentRegistrationSerializer,
    DocumentSerializer,
)
from apps.documents.services import create_document_record

# --- US-004: Crear registro de documento -----------------------------------
class DocumentRegistrationView(CreateAPIView):
    """Crea un registro de documento (US-004).

    `POST /api/v1/documents/register/`
      - Valida la información obligatoria del formulario (AC-019).
      - Crea el registro y genera/asocia el número de radicado (AC-016, AC-017).
      - Almacena el registro y responde `201 Created` (AC-018).
    """

    serializer_class = DocumentRegistrationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user if request.user.is_authenticated else None
        document = create_document_record(
            registered_by=user,
            **serializer.validated_data,
        )

        output = self.get_serializer(document)
        headers = self.get_success_headers(output.data)
        return Response(output.data, status=status.HTTP_201_CREATED, headers=headers)

# --- Otra HU: Listar y consultar documentos ---------------------------------
class DocumentListCreateView(generics.ListCreateAPIView):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = (IsAuthenticated,)

class DocumentDetailView(generics.RetrieveAPIView):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = (IsAuthenticated,)

        output = self.get_serializer(document)
        headers = self.get_success_headers(output.data)
        return Response(output.data, status=status.HTTP_201_CREATED, headers=headers)
