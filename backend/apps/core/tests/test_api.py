"""Pruebas de /api/v1/clients/, /api/v1/contracts/ y /api/v1/document-types/ (US-008)."""
import pytest
from django.core.files.storage import default_storage

from apps.core.models import Client, Contract, DigitalRecord
from apps.documents.models import AuditLog
from apps.documents.services.audit import log_action

CONTRACTS = "/api/v1/contracts/"
CLIENTS = "/api/v1/clients/"
TYPES = "/api/v1/document-types/"


@pytest.mark.django_db
class TestContractsApi:
    def test_create_contract_generates_record_and_storage_folder(self, api_client, tenant):
        payload = {
            "contract_number": "CONT-2026-077",
            "client": str(tenant.pk),
            "property_address": "Bodega 7, Vía Las Palmas",
            "start_date": "2026-10-01",
            "end_date": "2027-09-30",
        }

        response = api_client.post(CONTRACTS, payload, format="json")

        assert response.status_code == 201, response.content
        body = response.json()
        assert body["contract_number"] == "CONT-2026-077"
        assert body["status"] == "ACTIVO"
        assert body["client_detail"]["identification_number"] == "900123456-1"
        assert body["digital_record"]["storage_path"] == "expedientes/CONT-2026-077/"
        assert body["digital_record"]["documents_count"] == 0

        record = DigitalRecord.objects.get(contract__contract_number="CONT-2026-077")
        assert default_storage.exists("expedientes/CONT-2026-077/.expediente.json")
        assert record.storage_path == "expedientes/CONT-2026-077/"

    def test_create_rejects_end_before_start(self, api_client, tenant):
        response = api_client.post(
            CONTRACTS,
            {
                "contract_number": "CONT-2026-078",
                "client": str(tenant.pk),
                "property_address": "Local 1",
                "start_date": "2026-10-01",
                "end_date": "2026-09-01",
            },
            format="json",
        )
        assert response.status_code == 400
        assert "end_date" in response.json()
        assert not Contract.objects.filter(contract_number="CONT-2026-078").exists()

    def test_create_rejects_duplicate_number(self, api_client, contract, tenant):
        response = api_client.post(
            CONTRACTS,
            {
                "contract_number": contract.contract_number,
                "client": str(tenant.pk),
                "property_address": "Otro",
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
            },
            format="json",
        )
        assert response.status_code == 400
        assert "contract_number" in response.json()

    def test_list_and_search(self, api_client, contract):
        assert api_client.get(CONTRACTS).json()["count"] == 1
        assert api_client.get(CONTRACTS, {"search": "Logística"}).json()["count"] == 1
        assert api_client.get(CONTRACTS, {"search": "inexistente"}).json()["count"] == 0
        assert api_client.get(CONTRACTS, {"status": "TERMINADO"}).json()["count"] == 0

    def test_patch_status(self, api_client, contract):
        response = api_client.patch(f"{CONTRACTS}{contract.pk}/", {"status": "EN_RENOVACION"}, format="json")
        assert response.status_code == 200
        assert response.json()["status_label"] == "En Renovación"

    def test_delete_is_not_allowed(self, api_client, contract):
        assert api_client.delete(f"{CONTRACTS}{contract.pk}/").status_code == 405

    def test_contract_documents_returns_expediente_with_filters(
        self, api_client, contract, document, document_type
    ):
        document.digital_record = contract.digital_record
        document.document_type = document_type
        document.save()

        body = api_client.get(f"{CONTRACTS}{contract.pk}/documents/").json()
        assert body["count"] == 1
        assert body["results"][0]["filing_number"] == document.filing_number

        assert api_client.get(f"{CONTRACTS}{contract.pk}/documents/", {"document_type": "FACTURA"}).json()["count"] == 0
        assert api_client.get(f"{CONTRACTS}{contract.pk}/documents/", {"category": "POLIZA"}).json()["count"] == 1

    def test_contract_audit_trail_aggregates_document_logs(self, api_client, contract, document, user):
        from datetime import datetime, timedelta, timezone as dt_timezone
        from unittest.mock import patch

        document.digital_record = contract.digital_record
        document.save()
        base = datetime(2026, 9, 20, 15, 0, 0, tzinfo=dt_timezone.utc)
        with patch("django.utils.timezone.now", side_effect=[base, base + timedelta(seconds=1)]):
            log_action(document, AuditLog.Action.UPLOAD, user=user)
            log_action(document, AuditLog.Action.VIEW, user=user)

        body = api_client.get(f"{CONTRACTS}{contract.pk}/audit-trail/").json()

        assert body["count"] == 2
        assert [e["action"] for e in body["results"]] == ["CONSULTA_VISUAL", "CARGA"]
        assert body["results"][0]["filing_number"] == document.filing_number

    def test_requires_authentication(self, anonymous_client):
        assert anonymous_client.get(CONTRACTS).status_code == 401


@pytest.mark.django_db
class TestClientsApi:
    def test_create_list_and_update_client(self, api_client):
        response = api_client.post(
            CLIENTS,
            {
                "name": "Juan Pérez",
                "document_type": "CC",
                "identification_number": "1020304050",
                "email": "juan@example.com",
                "client_type": "NATURAL",
            },
            format="json",
        )
        assert response.status_code == 201, response.content
        client_id = response.json()["id"]
        assert response.json()["contracts_count"] == 0

        assert api_client.get(CLIENTS, {"search": "1020304050"}).json()["count"] == 1

        patched = api_client.patch(f"{CLIENTS}{client_id}/", {"phone": "3001234567"}, format="json")
        assert patched.status_code == 200
        assert Client.objects.get(pk=client_id).phone == "3001234567"

    def test_duplicate_identification_is_rejected(self, api_client, tenant):
        response = api_client.post(
            CLIENTS,
            {"name": "Duplicado", "identification_number": tenant.identification_number, "email": "d@x.co"},
            format="json",
        )
        assert response.status_code == 400
        assert "identification_number" in response.json()

    def test_delete_is_not_allowed(self, api_client, tenant):
        assert api_client.delete(f"{CLIENTS}{tenant.pk}/").status_code == 405


@pytest.mark.django_db
class TestDocumentTypesApi:
    def test_catalog_is_listed_without_pagination(self, api_client):
        body = api_client.get(TYPES).json()

        assert isinstance(body, list)
        codes = {item["code"] for item in body}
        assert {"POLIZA_CUMPLIMIENTO", "FACTURA", "SERVICIO_PUBLICO", "OTRO"} <= codes
        policy = next(item for item in body if item["code"] == "POLIZA_CUMPLIMIENTO")
        assert policy["requires_expiration"] is True
        assert policy["category_label"] == "Pólizas y Seguros"

    def test_filter_by_category(self, api_client):
        body = api_client.get(TYPES, {"category": "POLIZA"}).json()
        assert body and all(item["category"] == "POLIZA" for item in body)

    def test_catalog_is_read_only(self, api_client):
        response = api_client.post(TYPES, {"code": "X", "name": "X"}, format="json")
        assert response.status_code == 405
