from datetime import date
import threading

import pytest
from django.db import connection

from apps.documents.models import FilingSequence
from apps.documents.services import (
    FILING_NUMBER_PATTERN,
    generate_filing_number,
    is_valid_filing_number,
)

TARGET_DATE = date(2026, 9, 20)


@pytest.mark.django_db
class TestFilingSequence:
    def test_first_number_has_expected_format(self):
        assert FilingSequence.get_next_number(TARGET_DATE) == "RAD-20260920-000001"

    def test_numbers_are_sequential_per_day(self):
        numbers = [FilingSequence.get_next_number(TARGET_DATE) for _ in range(3)]

        assert numbers == [
            "RAD-20260920-000001",
            "RAD-20260920-000002",
            "RAD-20260920-000003",
        ]
        assert FilingSequence.objects.get(date=TARGET_DATE).last_number == 3

    def test_sequence_is_independent_per_day(self):
        FilingSequence.get_next_number(TARGET_DATE)
        next_day = FilingSequence.get_next_number(date(2026, 9, 21))

        assert next_day == "RAD-20260921-000001"
        assert FilingSequence.objects.count() == 2

    def test_service_generates_number_for_bogota_date(self):
        number = generate_filing_number(TARGET_DATE)

        assert number == "RAD-20260920-000001"
        assert FILING_NUMBER_PATTERN.fullmatch(number)


@pytest.mark.parametrize(
    "value",
    ["RAD-20260920-000001", "RAD-20261231-999999"],
)
def test_valid_filing_numbers(value):
    assert is_valid_filing_number(value) is True


@pytest.mark.parametrize(
    "value",
    [
        "",
        None,
        "RAD-20260920-000000",
        "RAD-20261340-000001",
        "RAD-2026092-000001",
        "RAD-20260920-00001",
        "rad-20260920-000001",
        "DOC-20260920-000001",
        "RAD-20260920-000001 ",
    ],
)
def test_invalid_filing_numbers(value):
    assert is_valid_filing_number(value) is False


@pytest.mark.concurrency
@pytest.mark.django_db(transaction=True)
def test_concurrent_callers_receive_unique_numbers():
    threads_count = 10
    calls_per_thread = 5
    results: list[str] = []
    errors: list[Exception] = []
    results_lock = threading.Lock()
    barrier = threading.Barrier(threads_count)

    def worker():
        try:
            barrier.wait(timeout=10)
            for _ in range(calls_per_thread):
                number = FilingSequence.get_next_number(TARGET_DATE)
                with results_lock:
                    results.append(number)
        except Exception as exc:  # pragma: no cover - diagnóstico concurrente
            with results_lock:
                errors.append(exc)
        finally:
            connection.close()

    threads = [threading.Thread(target=worker) for _ in range(threads_count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    expected_total = threads_count * calls_per_thread
    sequences = sorted(int(number.rsplit("-", 1)[1]) for number in results)

    assert errors == []
    assert len(results) == expected_total
    assert len(set(results)) == expected_total
    assert sequences == list(range(1, expected_total + 1))
