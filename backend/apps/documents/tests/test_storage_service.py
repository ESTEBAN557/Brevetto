"""Pruebas del servicio de almacenamiento: claves de objeto y URLs prefirmadas."""
from unittest.mock import MagicMock, patch

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from apps.documents.services.storage import (
    build_object_key,
    ensure_record_prefix,
    get_file_bytes,
    get_presigned_url,
    store_document_file,
)


class TestObjectKeys:
    def test_unclassified_documents_go_to_year_month_prefix(self):
        key = build_object_key("RAD-20260920-000007", "Cuenta de cobro (sep).pdf")
        assert key == "radicados/sin_clasificar/2026/09/RAD-20260920-000007_Cuenta_de_cobro_sep.pdf"

    @pytest.mark.django_db
    def test_documents_with_contract_go_to_record_prefix(self, contract):
        key = build_object_key("RAD-20260920-000007", "poliza.pdf", contract.digital_record)
        assert key == "expedientes/CONT-2026-042/RAD-20260920-000007_poliza.pdf"

    def test_filename_without_valid_chars_gets_fallback(self):
        assert build_object_key("RAD-20260920-000001", "¿¿??").endswith("RAD-20260920-000001_documento")
        assert build_object_key("RAD-20260920-000001", "¿¿??.pdf").endswith("RAD-20260920-000001_documento.pdf")
        assert build_object_key("RAD-20260920-000001", "").endswith("RAD-20260920-000001_documento")
        assert build_object_key("RAD-20260920-000001", "..").endswith("RAD-20260920-000001_documento")


@pytest.mark.django_db
class TestStorageRoundTrip:
    def test_store_and_read_back(self):
        key = store_document_file("pruebas/archivo.pdf", ContentFile(b"%PDF-1.4 hola"))
        assert default_storage.exists(key)
        assert get_file_bytes(key) == b"%PDF-1.4 hola"

    def test_ensure_record_prefix_is_idempotent(self, contract):
        first = ensure_record_prefix(contract.digital_record)
        second = ensure_record_prefix(contract.digital_record)

        assert first == second == "expedientes/CONT-2026-042/.expediente.json"
        assert b"CONT-2026-042" in get_file_bytes(first)


class TestPresignedUrls:
    def test_falls_back_to_storage_url_when_not_s3(self):
        url = get_presigned_url("radicados/x.pdf")
        assert url == "/media/radicados/x.pdf"

    def test_signs_against_public_endpoint_when_configured(self, settings):
        settings.STORAGES = {
            "default": {"BACKEND": "storages.backends.s3.S3Storage"},
            "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
        }
        settings.AWS_S3_PUBLIC_ENDPOINT_URL = "http://localhost:9000"
        settings.AWS_STORAGE_BUCKET_NAME = "brevetto-docs"
        settings.AWS_QUERYSTRING_EXPIRE = 900
        fake_client = MagicMock()
        fake_client.generate_presigned_url.return_value = (
            "http://localhost:9000/brevetto-docs/radicados/x.pdf?X-Amz-Signature=abc"
        )

        with patch("boto3.client", return_value=fake_client) as client_factory:
            url = get_presigned_url("radicados/x.pdf")

        assert url.startswith("http://localhost:9000/brevetto-docs/")
        assert client_factory.call_args.kwargs["endpoint_url"] == "http://localhost:9000"
        fake_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "brevetto-docs", "Key": "radicados/x.pdf"},
            ExpiresIn=900,
        )

    def test_public_endpoint_is_ignored_for_non_s3_backends(self, settings):
        settings.AWS_S3_PUBLIC_ENDPOINT_URL = "http://localhost:9000"
        with patch("boto3.client") as client_factory:
            url = get_presigned_url("radicados/x.pdf")
        client_factory.assert_not_called()
        assert url == "/media/radicados/x.pdf"
