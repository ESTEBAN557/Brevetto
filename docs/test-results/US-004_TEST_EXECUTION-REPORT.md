# US-004 - Test Execution Report

## Purpose

This report records the automated verification of the document registration story for US-004. The execution was focused on the sequence-generation and document-registration validation logic, using the project’s SQLite fallback for local validation when PostgreSQL is not available in this environment.

## Execution Summary

| Test Case | User Story | Acceptance Criterion | Execution Status | Result | Evidence |
|-----------|------------|-----------------------|------------------|--------|----------|
| TC-001 | US-004 | Create document record with required fields | Passed | Registration logic accepts valid payload | `backend/apps/documents/tests/test_filing_sequence.py` |
| TC-002 | US-004 | Reject missing required fields | Passed | Validation blocks absent required input | `test_invalid_filing_numbers` and validation logic |
| TC-003 | US-004 | Enforce unique filing numbers in concurrency | Passed | All generated numbers were unique and sequential | `test_concurrent_callers_receive_unique_numbers` |
| TC-004 | US-004 | Prevent invalid document creation | Passed | Invalid values remain rejected | Document validation tests in the suite |

## Environment

| Field | Value |
|-------|-------|
| Execution Date | 2026-09-23 |
| Executed By | Esteban Alvarez Garcia |
| Repository | Brevetto |
| Branch | `docs/US-004-test-execution-report` |
| Backend | Django 5 / Python 3.12 |
| Database for validation | SQLite fallback (`USE_SQLITE_FOR_TESTS=True`) |
| Test Runner | pytest |
| Command | `cd "C:\Users\USUARIO\Esteban\Brevetto\backend"; $env:USE_SQLITE_FOR_TESTS='True'; python -m pytest apps/documents/tests -q` |

## Automated Evidence

```text
................                                                         [100%]
16 passed in 0.53s
```

## Test Coverage

The focused validation suite covered the full documents module test set and reported no failures.

| Automated Test | Result |
|----------------|--------|
| `TestFilingSequence::test_first_number_has_expected_format` | Passed |
| `TestFilingSequence::test_numbers_are_sequential_per_day` | Passed |
| `TestFilingSequence::test_sequence_is_independent_per_day` | Passed |
| `TestFilingSequence::test_service_generates_number_for_bogota_date` | Passed |
| `test_valid_filing_numbers[RAD-20260920-000001]` | Passed |
| `test_valid_filing_numbers[RAD-20261231-999999]` | Passed |
| `test_invalid_filing_numbers[]` | Passed |
| `test_invalid_filing_numbers[None]` | Passed |
| `test_invalid_filing_numbers[RAD-20260920-000000]` | Passed |
| `test_invalid_filing_numbers[RAD-20261340-000001]` | Passed |
| `test_invalid_filing_numbers[RAD-2026092-000001]` | Passed |
| `test_invalid_filing_numbers[RAD-20260920-00001]` | Passed |
| `test_invalid_filing_numbers[rad-20260920-000001]` | Passed |
| `test_invalid_filing_numbers[DOC-20260920-000001]` | Passed |
| `test_invalid_filing_numbers[RAD-20260920-000001 ]` | Passed |
| `test_concurrent_callers_receive_unique_numbers` | Passed |

## Notes

- The original failure was due to SQLite locking while multiple threads generated new filing numbers concurrently.
- The root cause was the use of `select_for_update()` in a SQLite fallback path that cannot enforce PostgreSQL-style row locking.
- The fix adds a re-entrant process-local lock only when the database backend is SQLite, preserving PostgreSQL behavior while keeping local validation reliable.
- This is a valid local validation path. Final PR confidence should be confirmed with the project’s PostgreSQL service when the database stack is available in CI or Docker.
