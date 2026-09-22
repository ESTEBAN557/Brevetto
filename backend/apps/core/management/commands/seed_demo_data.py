"""
Datos de demostración para la sustentación de Brevetto (idempotente).

    python manage.py seed_demo_data [--password ...] [--skip-alerts]

Crea (o reutiliza si ya existen):
  - Usuario administrador `demo` (staff) para el portal administrativo.
  - 3 clientes arrendatarios con NIT realistas.
  - 3 contratos activos con su expediente digital y carpeta en S3/MinIO.
  - 5 documentos radicados con PDF real en el bucket y estados variados:
      PROCESADO (póliza por vencer, factura, certificado vencido) y
      REQUIERE_REVISION (carta con baja confianza, póliza con contrato desconocido).
  - Bitácora de auditoría coherente y alertas de vencimiento ya calculadas.

Los documentos se identifican por `ai_extracted_data.demo_seed_key`, por lo que
volver a ejecutar el comando no duplica registros ni consume nuevos radicados.
"""
from __future__ import annotations

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.core.models import Client, Contract, DocumentType
from apps.core.services import create_contract
from apps.documents.models import AuditLog, Document
from apps.documents.services.audit import log_action
from apps.documents.services.expirations import check_expiring_documents
from apps.documents.services.filing import generate_filing_number
from apps.documents.services.ingestion import compute_sha256
from apps.documents.services.storage import build_object_key, store_document_file
from scripts.make_sample_pdf import sample_pdf

DEMO_USERNAME = "demo"
DEMO_SEED_KEY = "demo_seed_key"

CLIENTS = [
    {
        "name": "Distribuciones Guayabal S.A.S.",
        "document_type": Client.IdentificationType.NIT,
        "identification_number": "900.845.112-3",
        "email": "administracion@disguayabal.co",
        "phone": "+57 604 444 1122",
        "client_type": Client.ClientType.PERSONA_JURIDICA,
    },
    {
        "name": "Moda Urbana El Poblado S.A.S.",
        "document_type": Client.IdentificationType.NIT,
        "identification_number": "901.233.874-6",
        "email": "gerencia@modaurbana.co",
        "phone": "+57 310 555 7788",
        "client_type": Client.ClientType.PERSONA_JURIDICA,
    },
    {
        "name": "Logística Calle 80 Ltda.",
        "document_type": Client.IdentificationType.NIT,
        "identification_number": "800.156.902-1",
        "email": "contabilidad@logisticacalle80.com",
        "phone": "+57 601 742 3390",
        "client_type": Client.ClientType.PERSONA_JURIDICA,
    },
]

CONTRACTS = [
    {
        "contract_number": "CONT-2025-018",
        "client_index": 0,
        "property_address": "Bodega 4, Cra 52 # 29-15, Guayabal, Medellín",
        "start_date": date(2025, 3, 1),
        "end_date": date(2027, 2, 28),
    },
    {
        "contract_number": "CONT-2026-007",
        "client_index": 1,
        "property_address": "Local 203, Cra 43A # 6 Sur-15, El Poblado, Medellín",
        "start_date": date(2026, 2, 1),
        "end_date": date(2027, 1, 31),
    },
    {
        "contract_number": "CONT-2024-091",
        "client_index": 2,
        "property_address": "Módulo 12, Centro Logístico Calle 80, Km 3 vía Siberia, Cota",
        "start_date": date(2024, 9, 1),
        "end_date": date(2026, 12, 31),
    },
]


def document_specs(today: date) -> list[dict]:
    """Definición de los 5 documentos de muestra con fechas relativas a hoy."""
    return [
        {
            "key": "demo-01-poliza-por-vencer",
            "kind": "poliza",
            "filename": "poliza_cumplimiento_guayabal_2026.pdf",
            "contract_index": 0,
            "document_type_code": "POLIZA_CUMPLIMIENTO",
            "status": Document.ProcessingStatus.PROCESSED,
            "source_channel": Document.SourceChannel.PHYSICAL,
            "document_date": today - timedelta(days=353),
            "expiration_date": today + timedelta(days=12),
            "confidence": 0.96,
            "summary": "Póliza de cumplimiento del contrato de arrendamiento de la bodega de Guayabal, próxima a vencer.",
        },
        {
            "key": "demo-02-factura-mantenimiento",
            "kind": "factura",
            "filename": "factura_FV-2026-0451_mantenimiento.pdf",
            "contract_index": 1,
            "document_type_code": "FACTURA",
            "status": Document.ProcessingStatus.PROCESSED,
            "source_channel": Document.SourceChannel.EMAIL,
            "document_date": today - timedelta(days=20),
            "expiration_date": None,
            "confidence": 0.91,
            "summary": "Factura por mantenimiento preventivo de cubierta emitida a Coltebienes S.A.",
        },
        {
            "key": "demo-03-carta-baja-confianza",
            "kind": "carta",
            "filename": "solicitud_adecuaciones_local.pdf",
            "contract_index": None,
            "ai_contract_number": None,
            "ai_client_name": "Moda Urbana",
            "document_type_code": None,
            "status": Document.ProcessingStatus.NEEDS_REVIEW,
            "source_channel": Document.SourceChannel.DIGITAL_INTERNAL,
            "document_date": today - timedelta(days=3),
            "expiration_date": None,
            "confidence": 0.58,
            "reason": "low_confidence",
            "summary": "Carta solicitando autorización para adecuaciones; no se identifica número de contrato explícito.",
        },
        {
            "key": "demo-04-poliza-contrato-desconocido",
            "kind": "poliza",
            "filename": "poliza_todo_riesgo_renovacion.pdf",
            "contract_index": None,
            "ai_contract_number": "CONT-2019-555",
            "ai_client_name": "Distribuciones Guayabal S.A.S.",
            "document_type_code": None,
            "status": Document.ProcessingStatus.NEEDS_REVIEW,
            "source_channel": Document.SourceChannel.WEB_PORTAL,
            "external_sender_name": "Carolina Restrepo",
            "document_date": today - timedelta(days=1),
            "expiration_date": today + timedelta(days=365),
            "confidence": 0.9,
            "reason": "contract_not_found",
            "summary": "Renovación de póliza todo riesgo que referencia un contrato inexistente en el sistema.",
        },
        {
            "key": "demo-05-certificado-vencido",
            "kind": "certificado",
            "filename": "certificado_camara_comercio_calle80.pdf",
            "contract_index": 2,
            "document_type_code": "CAMARA_COMERCIO",
            "status": Document.ProcessingStatus.PROCESSED,
            "source_channel": Document.SourceChannel.DIGITAL_INTERNAL,
            "document_date": today - timedelta(days=39),
            "expiration_date": today - timedelta(days=9),
            "confidence": 0.94,
            "summary": "Certificado de existencia y representación legal con vigencia de 30 días, ya vencido.",
        },
    ]


class Command(BaseCommand):
    help = "Crea datos de demostración idempotentes (usuario demo, clientes, contratos y documentos)."

    def add_arguments(self, parser):
        parser.add_argument("--password", default="Brevetto2026!", help="Contraseña del usuario demo.")
        parser.add_argument("--skip-alerts", action="store_true", help="No calcular alertas de vencimiento.")

    def handle(self, *args, **options):
        today = timezone.localdate()
        summary = {"created": [], "reused": []}

        user = self._ensure_user(options["password"], summary)
        clients = [self._ensure_client(spec, summary) for spec in CLIENTS]
        contracts = [self._ensure_contract(spec, clients, summary) for spec in CONTRACTS]
        documents = [self._ensure_document(spec, contracts, user, today, summary) for spec in document_specs(today)]

        alerts = None
        if not options["skip_alerts"]:
            alerts = check_expiring_documents(today=today)

        self._report(user, clients, contracts, documents, alerts, summary)

    # ------------------------------------------------------------------ helpers --
    def _ensure_user(self, password, summary):
        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=DEMO_USERNAME,
            defaults={"first_name": "Usuario", "last_name": "Demo", "email": "demo@coltebienes.co", "is_staff": True},
        )
        if created:
            summary["created"].append(f"usuario {DEMO_USERNAME}")
        else:
            summary["reused"].append(f"usuario {DEMO_USERNAME}")
        user.set_password(password)
        user.is_staff = True
        user.save()
        return user

    def _ensure_client(self, spec, summary):
        client, created = Client.objects.get_or_create(
            identification_number=spec["identification_number"],
            defaults={k: v for k, v in spec.items() if k != "identification_number"},
        )
        summary["created" if created else "reused"].append(f"cliente {client.name}")
        return client

    def _ensure_contract(self, spec, clients, summary):
        existing = Contract.objects.filter(contract_number=spec["contract_number"]).first()
        if existing:
            summary["reused"].append(f"contrato {existing.contract_number}")
            return existing
        contract = create_contract(
            contract_number=spec["contract_number"],
            client=clients[spec["client_index"]],
            property_address=spec["property_address"],
            start_date=spec["start_date"],
            end_date=spec["end_date"],
            status=Contract.ContractStatus.ACTIVE,
        )
        summary["created"].append(f"contrato {contract.contract_number}")
        return contract

    def _ensure_document(self, spec, contracts, user, today, summary):
        existing = Document.objects.filter(**{f"ai_extracted_data__{DEMO_SEED_KEY}": spec["key"]}).first()
        if existing:
            summary["reused"].append(f"documento {existing.filing_number}")
            return existing

        contract = contracts[spec["contract_index"]] if spec.get("contract_index") is not None else None
        pdf_contract_number = contract.contract_number if contract else (spec.get("ai_contract_number") or "SIN-CONTRATO")
        pdf_client = contract.client if contract else None
        pdf_bytes = sample_pdf(
            spec["kind"],
            contract=pdf_contract_number,
            nit=pdf_client.identification_number if pdf_client else "900.000.000-0",
            client=pdf_client.name if pdf_client else (spec.get("ai_client_name") or "Cliente externo"),
            address=contract.property_address if contract else "Inmueble por identificar",
            issued=spec["document_date"].isoformat(),
            end=(spec["expiration_date"] or today).isoformat(),
        )

        document_type = (
            DocumentType.objects.filter(code=spec["document_type_code"]).first() if spec.get("document_type_code") else None
        )
        ai_data = {
            DEMO_SEED_KEY: spec["key"],
            "contract_number": contract.contract_number if contract else spec.get("ai_contract_number"),
            "client_identification": pdf_client.identification_number.replace(".", "").replace("-", "") if pdf_client else None,
            "client_name": pdf_client.name if pdf_client else spec.get("ai_client_name"),
            "document_type": {"poliza": "POLIZA", "factura": "FACTURA", "carta": "CARTA_SOLICITUD", "certificado": "OTRO"}[spec["kind"]],
            "document_date": spec["document_date"].isoformat(),
            "expiration_date": spec["expiration_date"].isoformat() if spec["expiration_date"] else None,
            "extracted_text_summary": spec["summary"],
            "confidence_score": spec["confidence"],
            "model_used": "seed_demo_data",
        }

        with transaction.atomic():
            filing_number = generate_filing_number()
            from django.core.files.base import ContentFile

            content = ContentFile(pdf_bytes, name=spec["filename"])
            file_hash = compute_sha256(content)
            stored_key = store_document_file(
                build_object_key(filing_number, spec["filename"], contract.digital_record if contract else None),
                content,
            )
            is_processed = spec["status"] == Document.ProcessingStatus.PROCESSED
            document = Document.objects.create(
                filing_number=filing_number,
                digital_record=contract.digital_record if contract else None,
                document_type=document_type if is_processed else None,
                file_path=stored_key,
                original_filename=spec["filename"],
                file_hash=file_hash,
                file_size_bytes=len(pdf_bytes),
                mime_type="application/pdf",
                source_channel=spec["source_channel"],
                processing_status=spec["status"],
                ai_extracted_data=ai_data,
                ai_confidence_score=spec["confidence"],
                document_date=spec["document_date"] if is_processed else None,
                expiration_date=spec["expiration_date"] if is_processed else None,
                registered_by=None if spec["source_channel"] == Document.SourceChannel.WEB_PORTAL else user,
                external_sender_name=spec.get("external_sender_name", ""),
            )
            log_action(
                document,
                AuditLog.Action.UPLOAD,
                user=document.registered_by,
                details={"filing_number": filing_number, "file_hash": file_hash, "source_channel": spec["source_channel"], "seed": True},
            )
            classify_details = {"confidence": spec["confidence"], "threshold": 0.85, "seed": True}
            if is_processed:
                classify_details.update({"auto_associated": True, "contract_resolution": "contract_number"})
            else:
                classify_details.update({"needs_human_validation": True, "reason": spec.get("reason")})
            log_action(document, AuditLog.Action.AI_CLASSIFY, details=classify_details)

        summary["created"].append(f"documento {document.filing_number} ({spec['key']})")
        return document

    def _report(self, user, clients, contracts, documents, alerts, summary):
        self.stdout.write(self.style.MIGRATE_HEADING("Datos de demostración Brevetto"))
        self.stdout.write(f"  Usuario admin: {user.username} (is_staff={user.is_staff})")
        self.stdout.write(f"  Clientes:      {len(clients)}  | Contratos: {len(contracts)}  | Documentos: {len(documents)}")
        for doc in documents:
            contract = doc.digital_record.contract.contract_number if doc.digital_record else "—"
            exp = doc.expiration_date.isoformat() if doc.expiration_date else "—"
            self.stdout.write(f"    - {doc.filing_number}  {doc.processing_status:<18} contrato={contract:<14} vence={exp}  {doc.original_filename}")
        if alerts is not None:
            self.stdout.write(
                f"  Alertas de vencimiento: {alerts['alerts_created']} nuevas "
                f"(vencidos={alerts['expired']}, críticos={alerts['critical']}, aviso={alerts['warning']})"
            )
        self.stdout.write(self.style.SUCCESS(f"  Creados: {len(summary['created'])} · Reutilizados: {len(summary['reused'])}"))
