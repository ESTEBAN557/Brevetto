"""
Servicio de generación de números de radicado (US-001).

Encapsula la regla de negocio del formato `RAD-YYYYMMDD-XXXXXX` y delega la
atomicidad al modelo `FilingSequence` (transacción + bloqueo de fila).
"""
import re
from datetime import date
from zoneinfo import ZoneInfo

from django.utils import timezone

from apps.documents.models import FilingSequence

FILING_NUMBER_PATTERN = re.compile(r"^RAD-(?P<date>\d{8})-(?P<sequence>\d{6})$")

_BOGOTA_TZ = ZoneInfo("America/Bogota")


def today_in_bogota() -> date:
    """Fecha calendario de Colombia. El radicado usa la fecha local, no la UTC."""
    return timezone.now().astimezone(_BOGOTA_TZ).date()


def generate_filing_number(target_date: date | None = None) -> str:
    """Devuelve el siguiente radicado único para la fecha indicada (hoy por defecto).

    Seguro bajo concurrencia: ver `FilingSequence.get_next_number`.
    """
    return FilingSequence.get_next_number(target_date or today_in_bogota())


def is_valid_filing_number(value: str) -> bool:
    """Valida el formato RAD-YYYYMMDD-XXXXXX y que la fecha embebida sea real."""
    match = FILING_NUMBER_PATTERN.match(value or "")
    if not match:
        return False
    raw = match.group("date")
    try:
        date(int(raw[:4]), int(raw[4:6]), int(raw[6:8]))
    except ValueError:
        return False
    return int(match.group("sequence")) >= 1
