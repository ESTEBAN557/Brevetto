"""
Modelos de "Mi Portal" (apps.customer): cuenta del cliente, códigos de acceso y requerimientos (PQRS).

El cliente NO es un `User` de Django: su sesión es un token firmado propio (ver `auth.py`), por lo
que jamás puede alcanzar los endpoints administrativos protegidos con JWT.
"""

from __future__ import annotations

from django.contrib.auth.hashers import check_password, make_password
from django.db import models

from apps.core.models import Client, Contract, TimeStampedModel


class ClientAccount(TimeStampedModel):
    """Cuenta de acceso al portal de un cliente. Se crea al validar el primer código OTP."""

    client = models.OneToOneField(Client, on_delete=models.CASCADE, related_name="portal_account")
    email = models.EmailField(unique=True, help_text="Correo con el que el cliente inicia sesión")
    password_hash = models.CharField(max_length=255, blank=True)
    last_login_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Cuenta de Cliente"
        verbose_name_plural = "Cuentas de Clientes"

    def __str__(self):
        return f"{self.email} ({self.client.name})"

    @property
    def has_password(self) -> bool:
        return bool(self.password_hash)

    def set_password(self, raw_password: str) -> None:
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return bool(self.password_hash) and check_password(raw_password, self.password_hash)


class LoginCode(TimeStampedModel):
    """Código de un solo uso (OTP) enviado por SMS o correo. Solo se guarda su hash."""

    class Channel(models.TextChoices):
        SMS = "sms", "Mensaje de texto"
        EMAIL = "email", "Correo electrónico"

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="login_codes")
    channel = models.CharField(max_length=10, choices=Channel.choices)
    code_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Código de Acceso"
        verbose_name_plural = "Códigos de Acceso"
        ordering = ["-created_at"]


class ServiceRequest(TimeStampedModel):
    """Requerimiento (solicitud, queja o sugerencia) del cliente. El radicado visible es `#id`."""

    class Status(models.TextChoices):
        NEW = "NUEVO", "Nuevo"
        ASSIGNED = "ASIGNADO", "Asignado"
        IN_PROGRESS = "EN_PROCESO", "En proceso"
        RESOLVED = "RESUELTO", "Resuelto"
        CLOSED = "CERRADO", "Cerrado"

    id = models.BigAutoField(primary_key=True)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="service_requests")
    contract = models.ForeignKey(Contract, on_delete=models.PROTECT, related_name="service_requests")
    case_type = models.CharField(max_length=60)
    service = models.CharField(max_length=80)
    subcategory = models.CharField(max_length=120)
    subject = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW, db_index=True)
    assigned_to = models.CharField(max_length=120, blank=True, help_text="Nombre del asesor asignado")
    solution = models.TextField(blank=True)

    class Meta:
        verbose_name = "Requerimiento"
        verbose_name_plural = "Requerimientos"
        ordering = ["-created_at"]

    def __str__(self):
        return f"#{self.pk} {self.subject}"

    @property
    def is_closed(self) -> bool:
        return self.status == self.Status.CLOSED

    def change_status(self, new_status: str, *, actor: str = "", note: str = "") -> None:
        """Cambia el estado y deja el rastro en la línea de seguimiento."""
        self.status = new_status
        self.save(update_fields=["status", "updated_at"])
        ServiceRequestEvent.objects.create(request=self, status=new_status, actor=actor, note=note)


class ServiceRequestEvent(models.Model):
    """Línea de seguimiento (append-only a nivel de aplicación) de un requerimiento."""

    request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name="events")
    status = models.CharField(max_length=20, choices=ServiceRequest.Status.choices)
    actor = models.CharField(max_length=120, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["created_at", "id"]


class ServiceRequestMessage(models.Model):
    class Author(models.TextChoices):
        CLIENT = "CLIENTE", "Cliente"
        STAFF = "PERSONAL", "Personal Coltebienes"

    request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name="messages")
    author_type = models.CharField(max_length=10, choices=Author.choices)
    author_name = models.CharField(max_length=120)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["created_at", "id"]


class ServiceRequestAttachment(models.Model):
    request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name="attachments")
    from_client = models.BooleanField(default=True)
    file_path = models.CharField(max_length=1000)
    original_filename = models.CharField(max_length=255)
    file_size_bytes = models.BigIntegerField()
    mime_type = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
