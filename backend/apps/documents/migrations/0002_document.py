import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("documents", "0001_filingsequence")]

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
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Documento",
                "verbose_name_plural": "Documentos",
                "ordering": ["-created_at"],
            },
        ),
    ]
