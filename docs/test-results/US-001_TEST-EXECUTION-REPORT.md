# US-001 - Test Execution Report

## Execution Summary

| Test Case | Acceptance Criteria | Status | Evidence |
|-----------|---------------------|--------|----------|
| TC-001 - Register a valid document | AC-001 | Passed | `test_filing_sequence.py::TestFilingSequenceFormat::test_first_number_of_day_has_expected_format` |
| TC-002 - Register multiple documents | AC-003 | Passed | Sequential and concurrent filing sequence tests |
| TC-003 - Retrieve a registered document and review its information | AC-002, AC-004 | Passed | Upload persistence and document-detail API tests |

## Environment

| Field | Value |
|-------|-------|
| Execution date | 2026-09-23 |
| Branch | `docs/sprint1-test-cases` |
| Backend | Django 5.2.17 / Python 3.12 |
| Database | PostgreSQL 16 Docker service |
| Test runner | pytest |
| Command | `docker compose exec -T backend pytest apps/documents/tests/test_filing_sequence.py apps/documents/tests/test_upload_api.py apps/documents/tests/test_documents_api.py -q` |

## Execution Output

```text
...............................................                          [100%]
47 passed in 17.17s
```

## Acceptance-Criteria Evidence

### AC-001 - Automatic Registration Number Generation

**Result:** Passed.

The automated test generated `RAD-20260920-000001`, confirming the expected `RAD-YYYYMMDD-XXXXXX` format and automatic sequence generation.

### AC-003 - Registration Number Uniqueness

**Result:** Passed.

The sequential tests confirmed increasing numbers per day. The concurrency test used 10 threads with 5 calls each and confirmed 50 unique numbers, with no gaps in the sequence.

### AC-002 and AC-004 - Association and Display

**Result:** Passed by the existing upload and document-query tests.

The upload test verifies that the filing number returned by registration is persisted on the `Document` record. The document-query tests verify that document information, including the filing number, is exposed through the API.

## Defects

No defects were found in the executed US-001 sequence, upload, persistence, and query tests.
