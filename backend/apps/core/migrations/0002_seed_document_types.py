"""Catálogo inicial de tipos documentales de Coltebienes (alineado con docs/06 y docs/01)."""
from django.db import migrations

SEED = [
    # code, name, category, requires_expiration, description
    ("CONTRATO", "Contrato de Arrendamiento / Venta", "LEGAL", False, "Contrato firmado y sus otrosíes."),
    ("RUT", "RUT", "LEGAL", False, "Registro Único Tributario del cliente."),
    ("CAMARA_COMERCIO", "Certificado de Cámara de Comercio", "LEGAL", True, "Vigencia de 30 días."),
    ("ACTA_ENTREGA", "Acta de Entrega / Recibo del Inmueble", "LEGAL", False, ""),
    ("POLIZA_CUMPLIMIENTO", "Póliza de Cumplimiento", "POLIZA", True, "Póliza de arrendamiento o cumplimiento."),
    ("POLIZA_TODO_RIESGO", "Póliza Todo Riesgo", "POLIZA", True, ""),
    ("SERVICIO_PUBLICO", "Factura de Servicio Público", "SERVICIOS", False, "Energía, agua, gas, aseo."),
    ("FACTURA", "Factura", "FINANCIERO", False, "Facturas y cuentas de cobro."),
    ("CUENTA_COBRO", "Cuenta de Cobro", "FINANCIERO", False, ""),
    ("CARTA_SOLICITUD", "Carta / Solicitud", "COMUNICACION", False, "Comunicaciones del arrendatario o terceros."),
    ("NOTIFICACION", "Notificación / Requerimiento", "COMUNICACION", False, "Requerimientos de entidades."),
    ("OTRO", "Otro Documento", "COMUNICACION", False, "Documentos sin tipificación específica."),
]


def seed_document_types(apps, schema_editor):
    DocumentType = apps.get_model("core", "DocumentType")
    for code, name, category, requires_expiration, description in SEED:
        DocumentType.objects.get_or_create(
            code=code,
            defaults={
                "name": name,
                "category": category,
                "requires_expiration": requires_expiration,
                "description": description,
            },
        )


def unseed_document_types(apps, schema_editor):
    DocumentType = apps.get_model("core", "DocumentType")
    DocumentType.objects.filter(code__in=[row[0] for row in SEED]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_document_types, unseed_document_types),
    ]
