# Modelos de Base de Datos (Django ORM) — Brevetto

A continuación se define el esquema de datos relacional para PostgreSQL que Fable 5.1 debe implementar en las aplicaciones de Django (`apps.core` y `apps.documents`).

```python
import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class TimeStampedModel(models.Model):
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

    name = models.CharField(max_length=255, verbose_name="Nombre o Razón Social")
    document_type = models.CharField(max_length=20, default="NIT")  # NIT, CC, CE
    identification_number = models.CharField(max_length=50, unique=True, db_index=True)
    email = models.EmailField(db_index=True)
    phone = models.CharField(max_length=50, blank=True)
    client_type = models.CharField(max_length=20, choices=ClientType.choices, default=ClientType.PERSONA_JURIDICA)

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
    property_address = models.CharField(max_length=255, verbose_name="Dirección de la Bodega / Inmueble")
    start_date = models.DateField()
    end_date = models.DateField(db_index=True)
    status = models.CharField(max_length=30, choices=ContractStatus.choices, default=ContractStatus.ACTIVE)

    def __str__(self):
        return f"Contrato {self.contract_number} ({self.client.name})"


# 3. EXPEDIENTE DIGITAL DEL CONTRATO
class DigitalRecord(TimeStampedModel):
    contract = models.OneToOneField(Contract, on_delete=models.CASCADE, related_name="digital_record")
    storage_path = models.CharField(max_length=500, help_text="Prefijo en S3/MinIO para este expediente")

    def __str__(self):
        return f"Expediente - Contrato {self.contract.contract_number}"


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
    category = models.CharField(max_length=30, choices=Category.choices, default=Category.LEGAL)
    requires_expiration = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"[{self.category}] {self.name}"


# 5. SECUENCIA ATÓMICA DE RADICACIÓN (US-001)
class FilingSequence(models.Model):
    date = models.DateField(unique=True, db_index=True)
    last_number = models.PositiveIntegerField(default=0)

    @classmethod
    def get_next_number(cls, target_date):
        """Genera el siguiente consecutivo de forma atómica para evitar colisiones."""
        from django.db import transaction
        with transaction.atomic():
            seq, created = cls.objects.select_for_update().get_or_create(date=target_date)
            seq.last_number += 1
            seq.save()
            return f"RAD-{target_date.strftime('%Y%m%d')}-{seq.last_number:06d}"


# 6. DOCUMENTO RADICADO
class Document(TimeStampedModel):
    class ProcessingStatus(models.TextChoices):
        RECEIVED = "RECIBIDO", "Recibido / En cola"
        PROCESSING = "PROCESANDO", "Procesando en Celery"
        NEEDS_REVIEW = "REQUIERE_REVISION", "Requiere Validación Humana (HITL)"
        PROCESSED = "PROCESADO", "Clasificado y Archivado"
        FAILED = "FALLIDO", "Error de Procesamiento"

    class SourceChannel(models.TextChoices):
        PHYSICAL = "FISICO_ESCANEADO", "Documento Físico Escaneado"
        DIGITAL_INTERNAL = "DIGITAL_INTERNO", "Digital Cargado por Personal"
        WEB_PORTAL = "PORTAL_WEB", "Radicado por Cliente en Portal Web"
        EMAIL = "CORREO", "Ingreso por Correo Electrónico"

    filing_number = models.CharField(max_length=50, unique=True, db_index=True, verbose_name="Número de Radicado")
    digital_record = models.ForeignKey(DigitalRecord, on_delete=models.SET_NULL, null=True, blank=True, related_name="documents")
    document_type = models.ForeignKey(DocumentType, on_delete=models.SET_NULL, null=True, blank=True)
    
    file_path = models.CharField(max_length=1000, help_text="URI del objeto en S3 / MinIO")
    original_filename = models.CharField(max_length=255)
    file_hash = models.CharField(max_length=64, help_text="Checksum SHA-256")
    file_size_bytes = models.BigIntegerField()
    mime_type = models.CharField(max_length=100, default="application/pdf")
    
    source_channel = models.CharField(max_length=30, choices=SourceChannel.choices, default=SourceChannel.DIGITAL_INTERNAL)
    processing_status = models.CharField(max_length=30, choices=ProcessingStatus.choices, default=ProcessingStatus.RECEIVED, db_index=True)
    
    # Metadatos extraídos por IA
    ai_extracted_data = models.JSONField(default=dict, blank=True)
    ai_confidence_score = models.FloatField(null=True, blank=True)
    expiration_date = models.DateField(null=True, blank=True, db_index=True)
    document_date = models.DateField(null=True, blank=True)
    
    # Auditoría de usuario
    registered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="registered_documents")
    external_sender_name = models.CharField(max_length=255, blank=True, help_text="Nombre del remitente externo si vino del portal")

    def __str__(self):
        return f"{self.filing_number} - {self.original_filename}"


# 7. LOG DE AUDITORÍA INMUTABLE (US-023, US-024, US-025)
class AuditLog(models.Model):
    class Action(models.TextChoices):
        UPLOAD = "CARGA", "Carga y Radicación"
        AI_CLASSIFY = "CLASIFICACION_IA", "Clasificación con IA"
        HUMAN_VALIDATE = "VALIDACION_HUMANA", "Aprobación o Ajuste Manual"
        METADATA_UPDATE = "ACTUALIZACION_METADATOS", "Edición de Metadatos"
        VIEW = "CONSULTA_VISUAL", "Visualización en Visor Web"
        DOWNLOAD = "DESCARGA", "Descarga de Archivo"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="audit_logs")
    action = models.CharField(max_length=30, choices=Action.choices, db_index=True)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-timestamp"]
```
