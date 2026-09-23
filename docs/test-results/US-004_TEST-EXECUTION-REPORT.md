# US-004 - Test Execution Report

## Execution Summary

| Test Case | Acceptance Criteria | Status | Evidence |
|-----------|---------------------|--------|----------|
| TC-014 - Start registration process | AC-015 | Passed | Upload serializer/form contract test |
| TC-015 - Create and store document record | AC-016, AC-017, AC-018 | Passed | Valid upload creates persisted record and storage object |
| TC-016 - Missing required information | AC-019 | Passed | Missing-file validation test |
| TC-017 - Cancel registration | AC-020 | Blocked | No cancellation endpoint or draft-registration state exists |
| TC-018 - Associate registration number | AC-017 | Passed | Filing number persistence and uniqueness tests |

## Environment

| Field | Value |
|-------|-------|
| Execution date | 2026-09-23 |
| Branch | `docs/sprint1-test-cases` |
| Backend | Django 5.2.17 / Python 3.12 |
| Database | PostgreSQL 16 Docker service |
| Storage | MinIO Docker service |
| Test runner | pytest |
| Command | `docker compose exec -T backend pytest apps/documents/tests/test_upload_api.py apps/documents/tests/test_models.py apps/documents/tests/test_filing_sequence.py -q` |

## Execution Output

```text
...............................................                          [100%]
47 passed in 11.03s
```

## Acceptance-Criteria Evidence

### AC-015 - Start Document Registration

**Result:** Passed at API/form contract level.

The upload serializer accepts the required file and registration fields. A separate browser-level form test is not part of this execution.

### AC-016 - Create Document Record

**Result:** Passed.

A valid registration returns `201` and creates a `Document` record with the expected filename, size, MIME type, user, and initial `RECIBIDO` status.

### AC-017 - Generate and Associate Registration Number

**Result:** Passed.

The registration response includes a filing number, the persisted document stores it, and the model enforces uniqueness.

### AC-018 - Store Document Record

**Result:** Passed.

The document record is persisted in PostgreSQL and its file is stored in MinIO.

### AC-019 - Validate Required Information

**Result:** Passed.

A registration without the required file returns `400`, identifies the missing field, and creates no document record.

### AC-020 - Cancel Document Registration

**Result:** Blocked.

The current backend has no draft-registration state or cancellation endpoint. This is a product coverage gap, not a failed automated test.

## Defects and Gaps

No defects were found in the executed cases. AC-020 remains blocked until cancellation behavior is implemented and assigned to a story or task.
