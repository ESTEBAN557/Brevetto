# US-007 - Test Execution Report

## Execution Summary

| Test Case | Acceptance Criteria | Status | Evidence |
|-----------|---------------------|--------|----------|
| TC-031 - Edit one editable metadata field | AC-036 | Passed | Single-field PATCH and persistence |
| TC-032 - Save valid modified metadata | AC-037, AC-039 | Passed | Valid metadata response and persistence |
| TC-033 - Incomplete required metadata | AC-038 | Blocked | No required metadata field in current contract |
| TC-034 - Update multiple metadata fields | AC-039 | Passed | Multi-field PATCH and audit change set |
| TC-035 - Confirm successful update | AC-040 | Passed at API level | HTTP 200 and updated document response |
| TC-036 - Display updated metadata | AC-041 | Passed | Subsequent document detail response |
| TC-037 - Preserve document record information | AC-042 | Passed | Filing and file information unchanged |
| TC-038 - Record metadata update | AC-043 | Passed | Immutable metadata-update audit event |
| TC-039 - Cancel metadata update | AC-044 | Blocked | No cancellation endpoint or draft state |

## Environment

| Field | Value |
|-------|-------|
| Execution date | 2026-09-23 |
| Branch | `docs/sprint1-test-cases` |
| Backend | Django 5.2.17 / Python 3.12 |
| Database | PostgreSQL 16 Docker service |
| Storage | MinIO Docker service |
| Test runner | pytest |
| Command | `docker compose exec -T backend pytest apps/documents/tests/test_documents_api.py -q` |

## Execution Output

```text
.....................                                                    [100%]
21 passed in 11.81s
```

## Acceptance-Criteria Evidence

### AC-036 - Edit Document Metadata

**Result:** Passed.

The metadata endpoint accepts the editable fields and persists a single-field update.

### AC-037 and AC-039 - Validate and Update Metadata

**Result:** Passed.

Valid metadata is validated by the serializer, saved to the corresponding `Document`, and returned by the endpoint.

### AC-038 - Validate Required Metadata

**Result:** Blocked by the current contract.

The current serializer makes all metadata-update fields optional. Invalid date format is rejected, but there is no required metadata field whose absence can be tested as a failure.

### AC-040 - Confirm Successful Update

**Result:** Passed at API level.

A successful update returns HTTP `200` and the updated document representation. The endpoint does not currently return a dedicated confirmation message.

### AC-041 - Display Updated Metadata

**Result:** Passed.

A subsequent document detail request returns the updated date and external sender values.

### AC-042 - Maintain Document Record Integrity

**Result:** Passed.

Filing number, original filename, storage path, file hash, file size, processing status, registration user, and creation timestamp remain unchanged by metadata updates.

### AC-043 - Record Metadata Update

**Result:** Passed.

Each successful metadata update creates an immutable `ACTUALIZACION_METADATOS` audit event with the changed fields and before/after values.

### AC-044 - Cancel Metadata Update

**Result:** Blocked.

The current backend has no draft-edit state or cancellation endpoint, so unsaved changes cannot be exercised through an API test.

## Defects and Gaps

No defects were found in the executed US-007 tests.

Open product gaps:

- Required metadata validation is not defined by the current serializer because all editable fields are optional.
- Cancellation of an unsaved metadata edit is not implemented.
- The API confirms success through HTTP status and returned data, but does not provide a dedicated confirmation message.
