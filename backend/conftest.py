"""Fixtures compartidas para la suite de pruebas de Brevetto (pytest-django)."""
from datetime import date
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.core.models import Client, Contract, DocumentType
from apps.documents.models import Document, FilingSequence


# --------------------------------------------------------------- entorno ---
@pytest.fixture(autouse=True)
def in_memory_storage(settings):
    """Sustituye S3/MinIO por un storage en memoria, aislado por prueba."""
    settings.MEDIA_URL = "/media/"
    settings.AWS_QUERYSTRING_EXPIRE = 900
    settings.STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }


@pytest.fixture(autouse=True)
def mock_celery_delay():
    """Evita publicar en Redis durante las pruebas; permite verificar el encolado."""
    with patch("apps.documents.tasks.process_document_content_task.delay") as mocked:
        yield mocked


# --------------------------------------------------------------- usuarios ---
@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(username="analista", password="secreto-123")


@pytest.fixture
def api_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def anonymous_client():
    return APIClient()


# ---------------------------------------------------------------- dominio ---
@pytest.fixture
def tenant(db):
    """Cliente arrendatario (persona jurídica)."""
    return Client.objects.create(
        name="Logística Andina S.A.S.",
        document_type=Client.IdentificationType.NIT,
        identification_number="900123456-1",
        email="contacto@logandina.co",
        phone="+57 604 123 4567",
    )


@pytest.fixture
def contract(tenant):
    return Contract.objects.create(
        contract_number="CONT-2026-042",
        client=tenant,
        property_address="Bodega 12, Parque Industrial Zona Franca, Rionegro",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )


@pytest.fixture
def document_type(db):
    """Póliza de Cumplimiento (sembrada por la migración core.0002)."""
    return DocumentType.objects.get(code="POLIZA_CUMPLIMIENTO")


@pytest.fixture
def invoice_type(db):
    return DocumentType.objects.get(code="FACTURA")


@pytest.fixture
def document(db, user):
    return Document.objects.create(
        filing_number=FilingSequence.get_next_number(date(2026, 9, 20)),
        file_path="radicados/sin_clasificar/2026/09/RAD-20260920-000001_cuenta_cobro_sep.pdf",
        original_filename="cuenta_cobro_sep.pdf",
        file_hash="a" * 64,
        file_size_bytes=1_048_576,
        mime_type="application/pdf",
        source_channel=Document.SourceChannel.DIGITAL_INTERNAL,
        registered_by=user,
    )


# ---------------------------------------------------------------- archivos ---
def make_pdf(name="documento.pdf", size=2048, content_type="application/pdf") -> SimpleUploadedFile:
    header = b"%PDF-1.4\n"
    body = header + b"0" * max(0, size - len(header))
    return SimpleUploadedFile(name, body, content_type=content_type)


@pytest.fixture
def pdf_factory():
    return make_pdf
