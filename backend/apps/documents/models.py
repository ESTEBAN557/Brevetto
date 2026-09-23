"""Modelos mínimos de radicación para US-001."""
import threading

from django.conf import settings
from django.db import connection, models, transaction


class FilingSequence(models.Model):
    _concurrency_lock = threading.RLock()
    """Consecutivo diario protegido contra duplicados concurrentes."""

    date = models.DateField(unique=True, db_index=True)
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Secuencia de Radicación"
        verbose_name_plural = "Secuencias de Radicación"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.date:%Y-%m-%d} -> {self.last_number:06d}"

    @classmethod
    def get_next_number(cls, target_date) -> str:
        if connection.vendor == "sqlite":
            with cls._concurrency_lock:
                with transaction.atomic():
                    sequence, _created = cls.objects.get_or_create(date=target_date)
                    sequence.last_number += 1
                    sequence.save(update_fields=["last_number"])
                    return cls.format_filing_number(target_date, sequence.last_number)

        with transaction.atomic():
            sequence, _created = cls.objects.select_for_update().get_or_create(
                date=target_date
            )
            sequence.last_number += 1
            sequence.save(update_fields=["last_number"])
            return cls.format_filing_number(target_date, sequence.last_number)

    @staticmethod
    def format_filing_number(target_date, sequence: int) -> str:
        prefix = getattr(settings, "FILING_NUMBER_PREFIX", "RAD")
        digits = getattr(settings, "FILING_NUMBER_SEQUENCE_DIGITS", 6)
        return f"{prefix}-{target_date:%Y%m%d}-{sequence:0{digits}d}"
