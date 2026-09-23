from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="FilingSequence",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("date", models.DateField(db_index=True, unique=True)),
                ("last_number", models.PositiveIntegerField(default=0)),
            ],
            options={
                "verbose_name": "Secuencia de Radicación",
                "verbose_name_plural": "Secuencias de Radicación",
                "ordering": ["-date"],
            },
        ),
    ]
