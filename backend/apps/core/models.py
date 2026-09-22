"""
Modelos de dominio del núcleo de Brevetto (apps.core).

Contiene las entidades maestras: Cliente, Contrato, Expediente Digital y el
catálogo de Tipos Documentales. Ver docs/03_DATABASE_MODELS.md.
"""
import uuid

from django.db import models


class TimeStampedModel(models.Model):
    """Base abstracta con UUID como PK y marcas de tiempo automáticas."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# 1. CLIENTE (Arrendatario / Propietario)
class Client(TimeStampedModel):
    class ClientType(models.TextChoices):
        PERSONA_NATURAL = "NATURAL", "Persona Natural"
        PERSONA_JURIDICA = "JURIDICA", "Persona Jurídica"

    class IdentificationType(models.TextChoices):
        NIT = "NIT", "NIT"
        CC = "CC", "Cédula de Ciudadanía"
        CE = "CE", "Cédula de Extranjería"
        PASSPORT = "PASAPORTE", "Pasaporte"

    name = models.CharField(max_length=255, verbose_name="Nombre o Razón Social")
    document_type = models.CharField(
        max_length=20, choices=IdentificationType.choices, default=IdentificationType.NIT
    )
    identification_number = models.CharField(max_length=50, unique=True, db_index=True)
    email = models.EmailField(db_index=True)
    phone = models.CharField(max_length=50, blank=True)
    client_type = models.CharField(
        max_length=20, choices=ClientType.choices, default=ClientType.PERSONA_JURIDICA
    )

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["name"]

    def __str__(self):
        return f"{self.identification_number} - {self.name}"


# 2. CONTRATO DE ARRENDAMIENTO / VENTA
class Contract(TimeStampedModel):
    class ContractStatus(models.TextChoices):
        ACTIVE = "ACTIVO", "Activo"
        TERMINATED = "TERMINADO", "Terminado"
        IN_RENEWAL = "EN_RENOVACION", "En Renovación"

    contract_number = models.CharField(max_length=100, unique=True, db_index=True)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="contracts")
    property_address = models.CharField(
        max_length=255, verbose_name="Dirección de la Bodega / Inmueble"
    )
    start_date = models.DateField()
    end_date = models.DateField(db_index=True)
    status = models.CharField(
        max_length=30, choices=ContractStatus.choices, default=ContractStatus.ACTIVE
    )

    class Meta:
        verbose_name = "Contrato"
        verbose_name_plural = "Contratos"
        ordering = ["-start_date", "contract_number"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F("start_date")),
                name="contract_end_date_gte_start_date",
            ),
        ]

    def __str__(self):
        return f"Contrato {self.contract_number} ({self.client.name})"

    @property
    def is_active(self) -> bool:
        return self.status == self.ContractStatus.ACTIVE


# 3. EXPEDIENTE DIGITAL DEL CONTRATO
class DigitalRecord(TimeStampedModel):
    STORAGE_PREFIX = "expedientes"

    contract = models.OneToOneField(
        Contract, on_delete=models.CASCADE, related_name="digital_record"
    )
    storage_path = models.CharField(
        max_length=500, help_text="Prefijo en S3/MinIO para este expediente"
    )

    class Meta:
        verbose_name = "Expediente Digital"
        verbose_name_plural = "Expedientes Digitales"

    def __str__(self):
        return f"Expediente - Contrato {self.contract.contract_number}"

    @classmethod
    def build_storage_path(cls, contract: "Contract") -> str:
        """Prefijo determinístico en el bucket: expedientes/<numero_contrato>/."""
        safe_number = contract.contract_number.strip().replace("/", "-").replace(" ", "_")
        return f"{cls.STORAGE_PREFIX}/{safe_number}/"


# 4. CATÁLOGO DE TIPOS DOCUMENTALES
class DocumentType(TimeStampedModel):
    class Category(models.TextChoices):
        LEGAL = "LEGAL", "Documento Legal / Contractual"
        INSURANCE = "POLIZA", "Pólizas y Seguros"
        UTILITIES = "SERVICIOS", "Servicios Públicos"
        FINANCIAL = "FINANCIERO", "Facturación y Pagos"
        COMMUNICATION = "COMUNICACION", "Comunicaciones y Solicitudes"

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=50, unique=True)  # POLIZA_CUMPLIMIENTO, RUT, FACTURA
    category = models.CharField(
        max_length=30, choices=Category.choices, default=Category.LEGAL
    )
    requires_expiration = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Tipo Documental"
        verbose_name_plural = "Tipos Documentales"
        ordering = ["category", "name"]

    def __str__(self):
        return f"[{self.category}] {self.name}"
