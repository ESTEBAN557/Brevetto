"""Reglas de generación y validación de números de radicado."""
import re
from datetime import date, datetime
from zoneinfo import ZoneInfo

from django.conf import settings

from apps.documents.models import FilingSequence

FILING_NUMBER_PATTERN = re.compile(
    rf"^{getattr(settings, 'FILING_NUMBER_PREFIX', 'RAD')}-"
    r"(?P<date>\d{8})-(?P<sequence>\d{6})$"
)


def today_in_bogota() -> date:
    if settings.TIME_ZONE != "America/Bogota":
        return date.today()
    return datetime.now(ZoneInfo("America/Bogota")).date()


def generate_filing_number(target_date: date | None = None) -> str:
    return FilingSequence.get_next_number(target_date or today_in_bogota())


def is_valid_filing_number(value: object) -> bool:
    if not isinstance(value, str):
        return False
    match = FILING_NUMBER_PATTERN.fullmatch(value)
    if not match or int(match.group("sequence")) < 1:
        return False
    try:
        date(
            int(match.group("date")[:4]),
            int(match.group("date")[4:6]),
            int(match.group("date")[6:]),
        )
    except ValueError:
        return False
    return True
