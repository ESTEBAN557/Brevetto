"""Señales del núcleo: garantizan que todo contrato tenga su expediente digital (US-008)."""
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Contract, DigitalRecord


@receiver(post_save, sender=Contract, dispatch_uid="core.create_digital_record_for_contract")
def create_digital_record_for_contract(sender, instance: Contract, created: bool, **kwargs):
    """Crea el registro DigitalRecord al crear un Contract.

    La creación del prefijo físico en S3/MinIO se realiza en la capa de servicios
    (Fase 3); aquí solo se garantiza la consistencia relacional.
    """
    if not created:
        return
    DigitalRecord.objects.get_or_create(
        contract=instance,
        defaults={"storage_path": DigitalRecord.build_storage_path(instance)},
    )
