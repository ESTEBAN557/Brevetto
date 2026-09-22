from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "Brevetto — Núcleo (Clientes, Contratos, Expedientes)"

    def ready(self):
        # Registra las señales (creación automática del expediente digital, US-008).
        from . import signals  # noqa: F401
