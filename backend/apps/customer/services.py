"""Reglas de negocio de Mi Portal: códigos OTP, cuentas, catálogo de requerimientos y consulta documental."""

from __future__ import annotations

import hashlib
import hmac
import logging
import re
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from apps.core.models import Client, Contract, DocumentType
from apps.customer.models import (
    ClientAccount,
    LoginCode,
    ServiceRequest,
    ServiceRequestAttachment,
    ServiceRequestEvent,
)
from apps.documents.models import Document
from apps.documents.services.storage import store_document_file
from apps.portal.services import normalize_identification

logger = logging.getLogger(__name__)

CODE_TTL = timedelta(minutes=10)
RESEND_COOLDOWN = timedelta(seconds=45)
MAX_ATTEMPTS = 5
ACTIVE_CONTRACT_STATUSES = (Contract.ContractStatus.ACTIVE, Contract.ContractStatus.IN_RENEWAL)

# Categorías del menú "Documentos" -> tipos documentales.
DOCUMENT_CATEGORIES = {
    "estados-de-cuenta": ("ESTADO_CUENTA",),
    "certificados": ("CERTIFICADO_RETENCION",),
    "facturas": ("FACTURA", "CUENTA_COBRO"),
    "contratos": ("CONTRATO",),
}

# Catálogo (tipo, servicio, subcategoría) para "¿Qué necesitas reportar?".
REQUEST_CATALOG = [
    ("Administrativo", "Contabilidad", "Información de estados de cuenta"),
    ("Administrativo", "Contabilidad", "Facturación y comisiones"),
    ("Administrativo", "Contabilidad", "Certificados de retención"),
    ("Administrativo", "Jurídico", "Renovación o prórroga del contrato"),
    ("Administrativo", "Jurídico", "Otrosí o modificación del contrato"),
    ("Administrativo", "Documental", "Actualización de pólizas o documentos vencidos"),
    ("Administrativo", "Documental", "Corrección de un documento radicado"),
    ("Servicio al cliente", "Servicio al cliente", "Solicitud de información"),
    ("Servicio al cliente", "Servicio al cliente", "Queja"),
    ("Servicio al cliente", "Servicio al cliente", "Sugerencia"),
    ("Mantenimiento", "Inmueble", "Reparaciones locativas"),
]


# ------------------------------------------------------------------ códigos --
def _hash_code(code: str, client_id) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), f"{client_id}:{code}".encode(), hashlib.sha256).hexdigest()


def find_client(document_type: str, identification_number: str) -> Client | None:
    wanted = normalize_identification(identification_number)
    if not wanted:
        return None
    for client in Client.objects.filter(document_type=document_type):
        if normalize_identification(client.identification_number) == wanted:
            return client
    return None


def mask_destination(channel: str, client: Client) -> str:
    if channel == LoginCode.Channel.EMAIL:
        local, _, domain = client.email.partition("@")
        return f"{local[:2]}{'*' * max(len(local) - 2, 2)}@{domain}"
    digits = re.sub(r"\D", "", client.phone)
    return f"{'*' * max(len(digits) - 4, 4)}{digits[-4:]}"


def deliver_code(client: Client, channel: str, code: str) -> None:
    message = f"Tu código de acceso a Mi Portal de Coltebienes es {code}. Vence en 10 minutos."
    if channel == LoginCode.Channel.EMAIL:
        send_mail(
            "Tu código de acceso · Mi Portal Coltebienes",
            message,
            getattr(settings, "DEFAULT_FROM_EMAIL", None),
            [client.email],
            fail_silently=True,
        )
    else:
        # No hay proveedor SMS integrado: se deja en el log hasta configurar uno (Twilio, Infobip, etc.).
        logger.warning("SMS no configurado; código para %s: %s", client.phone, code)


class CodeRequestRejected(Exception):
    """Solicitud de código bloqueada por el enfriamiento entre envíos."""


def request_login_code(client: Client, channel: str) -> tuple[str, str]:
    """Genera y envía un código. Devuelve (código, canal usado); el código en claro solo sirve al eco de desarrollo."""
    if channel == LoginCode.Channel.SMS and not client.phone.strip():
        channel = LoginCode.Channel.EMAIL
    now = timezone.now()
    latest = LoginCode.objects.filter(client=client).order_by("-created_at").first()
    if latest and now - latest.created_at < RESEND_COOLDOWN:
        raise CodeRequestRejected()

    code = f"{secrets.randbelow(10**6):06d}"
    with transaction.atomic():
        LoginCode.objects.filter(client=client, consumed_at__isnull=True).update(consumed_at=now)
        LoginCode.objects.create(
            client=client, channel=channel, code_hash=_hash_code(code, client.pk), expires_at=now + CODE_TTL
        )
    deliver_code(client, channel, code)
    return code, channel


def verify_login_code(client: Client, code: str) -> ClientAccount | None:
    """Valida el OTP vigente (máximo 5 intentos) y devuelve la cuenta, creándola si es la primera vez."""
    now = timezone.now()
    with transaction.atomic():
        login_code = (
            LoginCode.objects.select_for_update()
            .filter(client=client, consumed_at__isnull=True, expires_at__gt=now)
            .order_by("-created_at")
            .first()
        )
        if login_code is None or login_code.attempts >= MAX_ATTEMPTS:
            return None
        login_code.attempts += 1
        if not hmac.compare_digest(login_code.code_hash, _hash_code((code or "").strip(), client.pk)):
            login_code.save(update_fields=["attempts", "updated_at"])
            return None
        login_code.consumed_at = now
        login_code.save(update_fields=["attempts", "consumed_at", "updated_at"])
        account, _ = ClientAccount.objects.get_or_create(client=client, defaults={"email": client.email.lower()})
        account.last_login_at = now
        account.save(update_fields=["last_login_at", "updated_at"])
        return account


def login_with_password(email: str, password: str) -> ClientAccount | None:
    account = ClientAccount.objects.select_related("client").filter(email__iexact=(email or "").strip()).first()
    if account is None:
        # Hash ficticio para igualar el tiempo de respuesta y no revelar si el correo existe.
        ClientAccount(password_hash="").check_password(password)
        return None
    if not account.check_password(password):
        return None
    account.last_login_at = timezone.now()
    account.save(update_fields=["last_login_at", "updated_at"])
    return account


# ---------------------------------------------------------------- documentos --
def client_contracts(client: Client):
    return client.contracts.filter(status__in=ACTIVE_CONTRACT_STATUSES).select_related("digital_record")


def client_documents(client: Client, *, category: str | None = None, contract_id=None):
    """Documentos ya clasificados del expediente de los contratos vigentes del cliente."""
    queryset = Document.objects.select_related("document_type", "digital_record__contract").filter(
        digital_record__contract__in=client_contracts(client),
        processing_status=Document.ProcessingStatus.PROCESSED,
    )
    if contract_id:
        queryset = queryset.filter(digital_record__contract_id=contract_id)
    if category:
        queryset = queryset.filter(document_type__code__in=DOCUMENT_CATEGORIES.get(category, ()))
    return queryset.order_by("-document_date", "-created_at")


def publishable_document_types():
    """Tipos que el cliente puede radicar (excluye los que emite Coltebienes)."""
    return DocumentType.objects.exclude(
        code__in=("CONTRATO", "ACTA_ENTREGA", "NOTIFICACION", "ESTADO_CUENTA", "CERTIFICADO_RETENCION")
    ).order_by("category", "name")


# ------------------------------------------------------------ requerimientos --
def catalog_entries() -> list[dict]:
    return [
        {"id": index, "case_type": t, "service": s, "subcategory": sub}
        for index, (t, s, sub) in enumerate(REQUEST_CATALOG)
    ]


@transaction.atomic
def create_service_request(
    *, client: Client, contract: Contract, catalog_id: int, subject: str, description: str, files
) -> ServiceRequest:
    case_type, service, subcategory = REQUEST_CATALOG[catalog_id]
    service_request = ServiceRequest.objects.create(
        client=client,
        contract=contract,
        case_type=case_type,
        service=service,
        subcategory=subcategory,
        subject=subject.strip(),
        description=description.strip(),
    )
    ServiceRequestEvent.objects.create(
        request=service_request,
        status=ServiceRequest.Status.NEW,
        actor=client.name,
        note=(
            f"El cliente creó el requerimiento. Tipo: {case_type} · Servicio: {service} · "
            f"Subcategoría: {subcategory}."
        ),
    )
    for file in files:
        add_attachment(service_request, file, from_client=True)
    return service_request


def add_attachment(service_request: ServiceRequest, file, *, from_client: bool) -> ServiceRequestAttachment:
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", file.name)[:120] or "adjunto"
    key = f"requerimientos/{service_request.pk}/{secrets.token_hex(6)}-{safe_name}"
    stored_key = store_document_file(key, file)
    return ServiceRequestAttachment.objects.create(
        request=service_request,
        from_client=from_client,
        file_path=stored_key,
        original_filename=file.name[:255],
        file_size_bytes=file.size,
        mime_type=(getattr(file, "content_type", "") or "application/octet-stream")[:100],
    )
