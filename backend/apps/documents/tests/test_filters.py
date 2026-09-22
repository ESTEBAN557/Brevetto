"""Pruebas de búsqueda facetada (US-018 / US-022) en documentos, contratos y clientes."""
from datetime import date, timedelta

import pytest
from django.utils import timezone

from apps.core.models import Client, Contract, DocumentType
from apps.documents.models import Document

DOCS = "/api/v1/documents/"
CONTRACTS = "/api/v1/contracts/"
CLIENTS = "/api/v1/clients/"


def make_doc(filing, **kwargs):
    defaults = dict(
        file_path=f"x/{filing}.pdf",
        original_filename=f"{filing}.pdf",
        file_hash="d" * 64,
        file_size_bytes=10,
    )
    defaults.update(kwargs)
    return Document.objects.create(filing_number=filing, **defaults)


@pytest.fixture
def dataset(tenant, contract, document_type, invoice_type):
    """Dos clientes, dos contratos y cuatro documentos con atributos distintos."""
    other_client = Client.objects.create(
        name="Comercializadora Pacífico Ltda.",
        identification_number="800.222.333-9",
        email="pacifico@example.com",
    )
    other_contract = Contract.objects.create(
        contract_number="CONT-2024-003",
        client=other_client,
        property_address="Local 5, Centro Comercial Oviedo",
        start_date=date(2024, 1, 1),
        end_date=timezone.localdate() + timedelta(days=45),
    )
    today = timezone.localdate()
    docs = {
        "policy_expiring": make_doc(
            "RAD-20260920-000201",
            digital_record=contract.digital_record,
            document_type=document_type,
            processing_status=Document.ProcessingStatus.PROCESSED,
            expiration_date=today + timedelta(days=10),
            ai_confidence_score=0.95,
            source_channel=Document.SourceChannel.PHYSICAL,
        ),
        "policy_expired": make_doc(
            "RAD-20260920-000202",
            digital_record=other_contract.digital_record,
            document_type=document_type,
            processing_status=Document.ProcessingStatus.PROCESSED,
            expiration_date=today - timedelta(days=5),
            ai_confidence_score=0.88,
        ),
        "invoice": make_doc(
            "RAD-20260920-000203",
            digital_record=contract.digital_record,
            document_type=invoice_type,
            processing_status=Document.ProcessingStatus.PROCESSED,
            ai_confidence_score=0.7,
            source_channel=Document.SourceChannel.EMAIL,
        ),
        "orphan_review": make_doc(
            "RAD-20260920-000204",
            processing_status=Document.ProcessingStatus.NEEDS_REVIEW,
            external_sender_name="Carolina Restrepo",
            ai_confidence_score=0.4,
        ),
    }
    return {"docs": docs, "other_client": other_client, "other_contract": other_contract, "today": today}


def ids(response):
    body = response.json()
    results = body["results"] if isinstance(body, dict) else body
    return {item["filing_number"] for item in results}


@pytest.mark.django_db
class TestDocumentFacetedSearch:
    def test_quick_search_matches_client_name_full_text(self, api_client, dataset):
        assert ids(api_client.get(DOCS, {"q": "andina"})) == {"RAD-20260920-000201", "RAD-20260920-000203"}
        assert ids(api_client.get(DOCS, {"q": "Logística"})) == {"RAD-20260920-000201", "RAD-20260920-000203"}

    def test_quick_search_matches_nit_ignoring_punctuation(self, api_client, dataset):
        assert ids(api_client.get(DOCS, {"q": "900.123.456-1"})) == {"RAD-20260920-000201", "RAD-20260920-000203"}
        assert ids(api_client.get(DOCS, {"q": "9001234561"})) == {"RAD-20260920-000201", "RAD-20260920-000203"}
        assert ids(api_client.get(DOCS, {"q": "8002223339"})) == {"RAD-20260920-000202"}

    def test_quick_search_matches_filing_number_contract_and_sender(self, api_client, dataset):
        assert ids(api_client.get(DOCS, {"q": "000204"})) == {"RAD-20260920-000204"}
        assert ids(api_client.get(DOCS, {"q": "CONT-2024-003"})) == {"RAD-20260920-000202"}
        assert ids(api_client.get(DOCS, {"q": "restrepo"})) == {"RAD-20260920-000204"}

    def test_status_and_channel_accept_comma_separated_lists(self, api_client, dataset):
        assert ids(api_client.get(DOCS, {"status": "REQUIERE_REVISION,FALLIDO"})) == {"RAD-20260920-000204"}
        assert ids(api_client.get(DOCS, {"channel": "FISICO_ESCANEADO,CORREO"})) == {
            "RAD-20260920-000201",
            "RAD-20260920-000203",
        }
        # Compatibilidad con el parámetro simple del Sprint 1
        assert ids(api_client.get(DOCS, {"processing_status": "PROCESADO"})) == {
            "RAD-20260920-000201",
            "RAD-20260920-000202",
            "RAD-20260920-000203",
        }

    def test_filter_by_category_and_document_type_code(self, api_client, dataset):
        assert ids(api_client.get(DOCS, {"category": "POLIZA"})) == {"RAD-20260920-000201", "RAD-20260920-000202"}
        assert ids(api_client.get(DOCS, {"category": "POLIZA,FINANCIERO"})) == {
            "RAD-20260920-000201",
            "RAD-20260920-000202",
            "RAD-20260920-000203",
        }
        assert ids(api_client.get(DOCS, {"document_type_code": "factura"})) == {"RAD-20260920-000203"}

    def test_filter_by_contract_and_client(self, api_client, dataset, contract, tenant):
        assert ids(api_client.get(DOCS, {"contract": str(contract.pk)})) == {"RAD-20260920-000201", "RAD-20260920-000203"}
        assert ids(api_client.get(DOCS, {"contract_number": "cont-2024-003"})) == {"RAD-20260920-000202"}
        assert ids(api_client.get(DOCS, {"client": str(tenant.pk)})) == {"RAD-20260920-000201", "RAD-20260920-000203"}
        assert ids(api_client.get(DOCS, {"client_identification": "900123456"})) == {
            "RAD-20260920-000201",
            "RAD-20260920-000203",
        }
        assert ids(api_client.get(DOCS, {"has_contract": "false"})) == {"RAD-20260920-000204"}

    def test_created_date_range_uses_local_dates(self, api_client, dataset):
        today = dataset["today"]
        yesterday = today - timedelta(days=1)
        assert api_client.get(DOCS, {"created_from": today.isoformat()}).json()["count"] == 4
        assert api_client.get(DOCS, {"created_to": yesterday.isoformat()}).json()["count"] == 0
        assert api_client.get(DOCS, {"created_from": yesterday.isoformat(), "created_to": today.isoformat()}).json()["count"] == 4

    def test_expiration_filters(self, api_client, dataset):
        today = dataset["today"]
        assert ids(api_client.get(DOCS, {"expiring_within_days": 30})) == {"RAD-20260920-000201", "RAD-20260920-000202"}
        assert ids(api_client.get(DOCS, {"expiring_within_days": 30, "include_expired": "false"})) == {"RAD-20260920-000201"}
        assert ids(api_client.get(DOCS, {"expiring_within_days": 5})) == {"RAD-20260920-000202"}
        assert ids(api_client.get(DOCS, {"expired": "true"})) == {"RAD-20260920-000202"}
        assert ids(api_client.get(DOCS, {"expired": "false"})) == {"RAD-20260920-000201"}
        assert ids(
            api_client.get(DOCS, {"expiration_from": today.isoformat(), "expiration_to": (today + timedelta(days=15)).isoformat()})
        ) == {"RAD-20260920-000201"}

    def test_confidence_range_and_ordering(self, api_client, dataset):
        assert ids(api_client.get(DOCS, {"min_confidence": 0.85})) == {"RAD-20260920-000201", "RAD-20260920-000202"}
        assert ids(api_client.get(DOCS, {"max_confidence": 0.5})) == {"RAD-20260920-000204"}

        ordered = api_client.get(DOCS, {"ordering": "expiration_date", "expired": "false"}).json()["results"]
        assert ordered[0]["filing_number"] == "RAD-20260920-000201"

    def test_filters_combine(self, api_client, dataset):
        response = api_client.get(DOCS, {"q": "andina", "category": "POLIZA", "status": "PROCESADO", "expiring_within_days": 30})
        assert ids(response) == {"RAD-20260920-000201"}

    def test_invalid_filter_value_returns_400(self, api_client, dataset):
        assert api_client.get(DOCS, {"created_from": "no-es-fecha"}).status_code == 400
        assert api_client.get(DOCS, {"contract": "no-es-uuid"}).status_code == 400


@pytest.mark.django_db
class TestContractFacetedSearch:
    def test_quick_search_by_nit_name_and_address(self, api_client, dataset):
        assert {c["contract_number"] for c in api_client.get(CONTRACTS, {"q": "8002223339"}).json()["results"]} == {"CONT-2024-003"}
        assert {c["contract_number"] for c in api_client.get(CONTRACTS, {"q": "logística andina"}).json()["results"]} == {"CONT-2026-042"}
        assert {c["contract_number"] for c in api_client.get(CONTRACTS, {"q": "Oviedo"}).json()["results"]} == {"CONT-2024-003"}
        assert api_client.get(CONTRACTS, {"q": "inexistente"}).json()["count"] == 0

    def test_status_list_and_client_identification(self, api_client, dataset, contract):
        contract.status = Contract.ContractStatus.IN_RENEWAL
        contract.save()
        assert api_client.get(CONTRACTS, {"status": "ACTIVO"}).json()["count"] == 1
        assert api_client.get(CONTRACTS, {"status": "ACTIVO,EN_RENOVACION"}).json()["count"] == 2
        assert api_client.get(CONTRACTS, {"client_identification": "900.123.456"}).json()["count"] == 1

    def test_end_date_range_and_expiring_contracts(self, api_client, dataset):
        today = dataset["today"]
        assert {c["contract_number"] for c in api_client.get(CONTRACTS, {"expiring_within_days": 60}).json()["results"]} == {"CONT-2024-003"}
        assert api_client.get(CONTRACTS, {"expiring_within_days": 30}).json()["count"] == 0
        assert {c["contract_number"] for c in api_client.get(CONTRACTS, {"end_from": (today + timedelta(days=100)).isoformat()}).json()["results"]} == {"CONT-2026-042"}
        assert api_client.get(CONTRACTS, {"expired": "true"}).json()["count"] == 0

    def test_has_documents(self, api_client, dataset, tenant):
        Contract.objects.create(
            contract_number="CONT-2026-999",
            client=tenant,
            property_address="Sin documentos",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        assert {c["contract_number"] for c in api_client.get(CONTRACTS, {"has_documents": "false"}).json()["results"]} == {"CONT-2026-999"}
        assert api_client.get(CONTRACTS, {"has_documents": "true"}).json()["count"] == 2


@pytest.mark.django_db
class TestClientSearch:
    def test_quick_search_by_name_and_nit(self, api_client, dataset):
        assert api_client.get(CLIENTS, {"q": "pacífico"}).json()["count"] == 1
        assert api_client.get(CLIENTS, {"q": "900123456"}).json()["count"] == 1
        assert api_client.get(CLIENTS, {"client_type": "JURIDICA"}).json()["count"] == 2
