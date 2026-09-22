"""Pruebas de los modelos maestros: Client, Contract, DigitalRecord y DocumentType."""
from datetime import date

import pytest
from django.db import IntegrityError
from django.db.models import ProtectedError

from apps.core.models import Client, Contract, DigitalRecord, DocumentType


@pytest.mark.django_db
class TestClient:
    def test_str_and_defaults(self, tenant):
        assert str(tenant) == "900123456-1 - Logística Andina S.A.S."
        assert tenant.client_type == Client.ClientType.PERSONA_JURIDICA
        assert tenant.document_type == Client.IdentificationType.NIT

    def test_identification_number_is_unique(self, tenant):
        with pytest.raises(IntegrityError):
            Client.objects.create(
                name="Otro", identification_number="900123456-1", email="otro@x.co"
            )

    def test_client_with_contracts_cannot_be_deleted(self, contract):
        with pytest.raises(ProtectedError):
            contract.client.delete()


@pytest.mark.django_db
class TestContract:
    def test_str_and_defaults(self, contract):
        assert str(contract) == "Contrato CONT-2026-042 (Logística Andina S.A.S.)"
        assert contract.status == Contract.ContractStatus.ACTIVE
        assert contract.is_active is True

    def test_end_date_must_not_precede_start_date(self, tenant):
        with pytest.raises(IntegrityError):
            Contract.objects.create(
                contract_number="CONT-2026-999",
                client=tenant,
                property_address="Local 3",
                start_date=date(2026, 6, 1),
                end_date=date(2026, 5, 31),
            )

    def test_contract_number_is_unique(self, contract, tenant):
        with pytest.raises(IntegrityError):
            Contract.objects.create(
                contract_number="CONT-2026-042",
                client=tenant,
                property_address="Duplicado",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 12, 31),
            )


@pytest.mark.django_db
class TestDigitalRecord:
    def test_digital_record_is_created_automatically_with_contract(self, contract):
        record = contract.digital_record

        assert isinstance(record, DigitalRecord)
        assert record.storage_path == "expedientes/CONT-2026-042/"
        assert str(record) == "Expediente - Contrato CONT-2026-042"

    def test_only_one_digital_record_per_contract(self, contract):
        contract.status = Contract.ContractStatus.IN_RENEWAL
        contract.save()  # una actualización no debe crear un segundo expediente

        assert DigitalRecord.objects.filter(contract=contract).count() == 1
        with pytest.raises(IntegrityError):
            DigitalRecord.objects.create(contract=contract, storage_path="dup/")

    def test_storage_path_sanitizes_contract_number(self, tenant):
        contract = Contract(contract_number=" ARR/2026 07 ", client=tenant)

        assert DigitalRecord.build_storage_path(contract) == "expedientes/ARR-2026_07/"

    def test_deleting_contract_removes_digital_record(self, contract):
        record_id = contract.digital_record.pk
        contract.delete()

        assert not DigitalRecord.objects.filter(pk=record_id).exists()


@pytest.mark.django_db
class TestDocumentType:
    def test_str_and_defaults(self, document_type):
        assert str(document_type) == "[POLIZA] Póliza de Cumplimiento"
        assert document_type.requires_expiration is True

    def test_code_is_unique(self, document_type):
        with pytest.raises(IntegrityError):
            DocumentType.objects.create(name="Otra póliza", code="POLIZA_CUMPLIMIENTO")

    def test_default_category_is_legal(self, db):
        certificate = DocumentType.objects.create(
            name="Certificado de Tradición y Libertad", code="CERTIFICADO_TRADICION"
        )
        assert certificate.category == DocumentType.Category.LEGAL

    def test_catalog_is_seeded_by_migration(self, db):
        codes = set(DocumentType.objects.values_list("code", flat=True))
        assert {"POLIZA_CUMPLIMIENTO", "FACTURA", "SERVICIO_PUBLICO", "CARTA_SOLICITUD", "ACTA_ENTREGA", "OTRO"} <= codes
