"""
Pruebas de US-001 — Generar Número de Radicado Único.

Cubre formato `RAD-YYYYMMDD-XXXXXX`, consecutivo por fecha y unicidad bajo
concurrencia real (10 hilos con conexiones independientes a PostgreSQL).
"""
import threading
from datetime import date

import pytest
from django.db import connection

from apps.documents.models import FilingSequence
from apps.documents.services import (
    FILING_NUMBER_PATTERN,
    generate_filing_number,
    is_valid_filing_number,
    today_in_bogota,
)

TARGET_DATE = date(2026, 9, 20)


@pytest.mark.django_db
class TestFilingSequenceFormat:
    def test_first_number_of_day_has_expected_format(self):
        number = FilingSequence.get_next_number(TARGET_DATE)

        assert number == "RAD-20260920-000001"
        assert FILING_NUMBER_PATTERN.match(number)

    def test_numbers_are_sequential_within_same_day(self):
        numbers = [FilingSequence.get_next_number(TARGET_DATE) for _ in range(3)]

        assert numbers == [
            "RAD-20260920-000001",
            "RAD-20260920-000002",
            "RAD-20260920-000003",
        ]
        assert FilingSequence.objects.get(date=TARGET_DATE).last_number == 3

    def test_sequence_is_independent_per_day(self):
        FilingSequence.get_next_number(TARGET_DATE)
        FilingSequence.get_next_number(TARGET_DATE)
        next_day = FilingSequence.get_next_number(date(2026, 9, 21))

        assert next_day == "RAD-20260921-000001"
        assert FilingSequence.objects.count() == 2

    def test_sequence_is_zero_padded_to_six_digits(self):
        seq = FilingSequence.objects.create(date=TARGET_DATE, last_number=41)

        assert FilingSequence.get_next_number(TARGET_DATE) == "RAD-20260920-000042"
        seq.refresh_from_db()
        assert seq.last_number == 42

    def test_service_defaults_to_bogota_local_date(self):
        number = generate_filing_number()

        expected_date = today_in_bogota().strftime("%Y%m%d")
        assert number == f"RAD-{expected_date}-000001"


class TestFilingNumberValidation:
    @pytest.mark.parametrize(
        "value",
        ["RAD-20260920-000001", "RAD-20261231-999999"],
    )
    def test_valid_numbers(self, value):
        assert is_valid_filing_number(value) is True

    @pytest.mark.parametrize(
        "value",
        [
            "",
            None,
            "RAD-20260920-000000",   # el consecutivo empieza en 1
            "RAD-20261340-000001",   # mes inválido
            "RAD-2026092-000001",    # fecha corta
            "RAD-20260920-00001",    # consecutivo corto
            "rad-20260920-000001",   # prefijo en minúscula
            "DOC-20260920-000001",   # prefijo incorrecto
            "RAD-20260920-000001 ",  # espacio final
        ],
    )
    def test_invalid_numbers(self, value):
        assert is_valid_filing_number(value) is False


@pytest.mark.concurrency
@pytest.mark.django_db(transaction=True)
class TestFilingSequenceConcurrency:
    """Cada hilo abre su propia conexión, por lo que el bloqueo de fila de PostgreSQL es real."""

    THREADS = 10
    CALLS_PER_THREAD = 5

    def test_ten_concurrent_callers_never_receive_duplicates(self):
        results: list[str] = []
        errors: list[Exception] = []
        lock = threading.Lock()
        barrier = threading.Barrier(self.THREADS)

        def worker():
            try:
                barrier.wait(timeout=10)  # todos los hilos disparan al mismo tiempo
                for _ in range(self.CALLS_PER_THREAD):
                    number = FilingSequence.get_next_number(TARGET_DATE)
                    with lock:
                        results.append(number)
            except Exception as exc:  # pragma: no cover - solo para diagnóstico
                with lock:
                    errors.append(exc)
            finally:
                connection.close()

        threads = [threading.Thread(target=worker, name=f"radicador-{i}") for i in range(self.THREADS)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=60)

        expected_total = self.THREADS * self.CALLS_PER_THREAD

        assert errors == []
        assert len(results) == expected_total
        assert len(set(results)) == expected_total, "Se generaron radicados duplicados"
        assert all(FILING_NUMBER_PATTERN.match(number) for number in results)

        sequences = sorted(int(number.rsplit("-", 1)[1]) for number in results)
        assert sequences == list(range(1, expected_total + 1)), "Hay huecos en el consecutivo"
        assert FilingSequence.objects.get(date=TARGET_DATE).last_number == expected_total
