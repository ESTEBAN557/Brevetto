import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0001_filingsequence"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Document",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "filing_number",
                    models.CharField(
                        db_index=True,
                        editable=False,
                        max_length=50,
                        unique=True,
                    ),
                ),
                ("original_filename", models.CharField(max_length=255)),
                ("file_path", models.CharField(max_length=1000)),
                ("file_hash", models.CharField(blank=True, max_length=64)),
                ("file_size_bytes", models.PositiveBigIntegerField()),
                ("mime_type", models.CharField(max_length=100)),
                (
                    "processing_status",
                    models.CharField(
                        choices=[
                            ("RECIBIDO", "Recibido / En cola"),
                            ("PROCESANDO", "Procesando"),
                            ("PROCESADO", "Procesado"),
                            ("FALLIDO", "Fallido"),
                        ],
                        db_index=True,
                        default="RECIBIDO",
                        max_length=30,
                    ),
                ),
                (
                    "registered_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="registered_documents",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Documento",
                "verbose_name_plural": "Documentos",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["processing_status", "-created_at"],
                        name="doc_status_created_idx",
                    )
                ],
            },
        ),
    ]
