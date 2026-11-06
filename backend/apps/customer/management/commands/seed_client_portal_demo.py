"""
Datos de demostración de Mi Portal (idempotente). Requiere haber corrido `seed_demo_data`.

    python manage.py seed_client_portal_demo

Publica en el expediente de CONT-2025-018 (Distribuciones Guayabal S.A.S., NIT 900.845.112-3) estados
de cuenta, facturas, un certificado de retención y el contrato, y crea dos requerimientos de ejemplo.
Los PDF son sintéticos: sirven para recorrer el portal, no representan información financiera real.
"""

from __future__ import annotations

from datetime import date, timedelta

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.core.management.commands.seed_demo_data import DEMO_SEED_KEY
from apps.core.models import Contract, DocumentType
from apps.customer.models import ServiceRequest, ServiceRequestEvent, ServiceRequestMessage
from apps.documents.models import AuditLog, Document
from apps.documents.services.audit import log_action
from apps.documents.services.filing import generate_filing_number
from apps.documents.services.ingestion import compute_sha256
from apps.documents.services.storage import build_object_key, store_document_file
from scripts.make_sample_pdf import sample_pdf

CONTRACT_NUMBER = "CONT-2025-018"
MONTHS_ES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
    "noviembre", "diciembre",
]  # fmt: skip


def month_start(today: date, back: int) -> date:
    index = today.year * 12 + today.month - 1 - back
    return date(index // 12, index % 12 + 1, 8)


class Command(BaseCommand):
    help = "Publica documentos y requerimientos de ejemplo para recorrer Mi Portal."

    def handle(self, *args, **options):
        contract = (
            Contract.objects.select_related("client", "digital_record")
            .filter(contract_number=CONTRACT_NUMBER)
            .first()
        )
        if contract is None:
            raise CommandError("Falta el contrato demo. Ejecuta primero: python manage.py seed_demo_data")

        today = timezone.localdate()
        created = 0
        for back in range(3):
            issued = month_start(today, back)
            label = f"{MONTHS_ES[issued.month - 1]} de {issued.year}"
            created += self._document(contract, f"demo-portal-ec-{issued:%Y%m}", "ESTADO_CUENTA",
                                      f"Estado de cuenta {label}.pdf", issued, "factura")  # fmt: skip
            created += self._document(contract, f"demo-portal-fv-{issued:%Y%m}", "FACTURA",
                                      f"Comisión inmobiliaria {label}.pdf", issued, "factura")  # fmt: skip
        created += self._document(contract, f"demo-portal-ret-{today.year}", "CERTIFICADO_RETENCION",
                                  f"Certificado de retención {today.year}.pdf", date(today.year, 1, 15), "certificado")  # fmt: skip
        created += self._document(contract, "demo-portal-contrato", "CONTRATO",
                                  f"{contract.contract_number}_contrato_firmado.pdf", contract.start_date, "carta")  # fmt: skip

        requests = self._requests(contract)
        self.stdout.write(
            self.style.SUCCESS(f"Documentos nuevos: {created} · requerimientos nuevos: {requests}")
        )
        self.stdout.write(
            f"Ingresa en /login con tipo NIT, número {contract.client.identification_number} y el código "
            "que se muestra en la consola/log del backend (o en dev_code si CLIENT_OTP_DEV_ECHO está activo)."
        )

    @transaction.atomic
    def _document(self, contract, key, type_code, filename, issued, kind) -> int:
        if Document.objects.filter(**{f"ai_extracted_data__{DEMO_SEED_KEY}": key}).exists():
            return 0
        pdf = sample_pdf(
            kind,
            contract=contract.contract_number,
            nit=contract.client.identification_number,
            client=contract.client.name,
            address=contract.property_address,
            issued=issued.isoformat(),
            end=(issued + timedelta(days=365)).isoformat(),
        )
        content = ContentFile(pdf, name=filename)
        filing_number = generate_filing_number()
        file_hash = compute_sha256(content)
        stored_key = store_document_file(
            build_object_key(filing_number, filename, contract.digital_record), content
        )
        document = Document.objects.create(
            filing_number=filing_number,
            digital_record=contract.digital_record,
            document_type=DocumentType.objects.get(code=type_code),
            file_path=stored_key,
            original_filename=filename,
            file_hash=file_hash,
            file_size_bytes=len(pdf),
            mime_type="application/pdf",
            source_channel=Document.SourceChannel.DIGITAL_INTERNAL,
            processing_status=Document.ProcessingStatus.PROCESSED,
            ai_extracted_data={DEMO_SEED_KEY: key, "model_used": "seed_client_portal_demo"},
            document_date=issued,
        )
        log_action(
            document,
            AuditLog.Action.UPLOAD,
            details={"filing_number": filing_number, "file_hash": file_hash, "seed": True},
        )
        return 1

    @transaction.atomic
    def _requests(self, contract) -> int:
        if ServiceRequest.objects.filter(client=contract.client, subject__startswith="[demo]").exists():
            return 0
        closed = ServiceRequest.objects.create(
            client=contract.client,
            contract=contract,
            case_type="Administrativo",
            service="Contabilidad",
            subcategory="Información de estados de cuenta",
            subject="[demo] Solicitud de estado de cuenta y explicación de giros",
            description="Solicito el estado de cuenta detallado de los últimos meses con la explicación de los descuentos.",
            assigned_to="Equipo de Contabilidad",
            solution="Muy amablemente, de acuerdo a su solicitud, adjuntamos los estados de cuenta. Quedamos atentos.",
        )
        ServiceRequestEvent.objects.create(
            request=closed,
            status="NUEVO",
            actor=contract.client.name,
            note="El cliente creó el requerimiento.",
        )
        closed.change_status("ASIGNADO", actor="Sistema", note="Asignado automáticamente a Contabilidad.")
        closed.change_status(
            "RESUELTO", actor="Equipo de Contabilidad", note="Se envió la información solicitada."
        )
        closed.change_status("CERRADO", actor="Equipo de Contabilidad", note="Resuelto satisfactoriamente.")

        open_request = ServiceRequest.objects.create(
            client=contract.client,
            contract=contract,
            case_type="Servicio al cliente",
            service="Servicio al cliente",
            subcategory="Solicitud de información",
            subject="[demo] Consulta sobre renovación del contrato",
            description="Quisiera conocer el proceso y los tiempos para renovar el contrato.",
            assigned_to="Equipo de Servicio al Cliente",
        )
        ServiceRequestEvent.objects.create(
            request=open_request,
            status="NUEVO",
            actor=contract.client.name,
            note="El cliente creó el requerimiento.",
        )
        open_request.change_status("ASIGNADO", actor="Sistema", note="Asignado a Servicio al Cliente.")
        open_request.change_status("EN_PROCESO", actor="Equipo de Servicio al Cliente")
        ServiceRequestMessage.objects.create(
            request=open_request,
            author_type=ServiceRequestMessage.Author.STAFF,
            author_name="Equipo de Servicio al Cliente",
            body="Hola, estamos revisando tu contrato. En breve te compartimos los pasos de la renovación.",
        )
        return 2
