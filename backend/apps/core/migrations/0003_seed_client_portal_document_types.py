"""Tipos documentales que Coltebienes emite hacia el cliente y se publican en Mi Portal."""
from django.db import migrations

SEED = [
    # code, name, category, requires_expiration, description
    ("ESTADO_CUENTA", "Estado de Cuenta", "FINANCIERO", False, "Estado de cuenta mensual emitido al cliente."),
    (
        "CERTIFICADO_RETENCION",
        "Certificado de Retención",
        "FINANCIERO",
        False,
        "Certificado anual de retenciones practicadas.",
    ),
]


def seed(apps, schema_editor):
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


def unseed(apps, schema_editor):
    DocumentType = apps.get_model("core", "DocumentType")
    DocumentType.objects.filter(code__in=[row[0] for row in SEED]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_seed_document_types"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
