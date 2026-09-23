# US-006 - Test Execution Report

## Execution Summary

| Test Case | Acceptance Criteria | Status | Evidence |
|-----------|---------------------|--------|----------|
| TC-025 - Authenticated registration | AC-029, AC-030 | Passed | Upload persistence and audit assertions |
| TC-026 - Associated registration information | AC-031, AC-032 | Passed | Document and audit record assertions |
| TC-027 - Display registration information | AC-033 | Passed | Document list/detail API assertions |
| TC-028 - Preserve registration information | AC-034 | Passed | Protected registration fields assertion |
| TC-029 - Unauthorized modification attempt | AC-035 | Passed | Metadata update protection assertion |
| TC-030 - Multiple independent registrations | AC-029, AC-030, AC-031 | Passed | Batch registration assertions |

## Environment

| Field | Value |
|-------|-------|
| Execution date | 2026-09-23 |
| Branch | `docs/sprint1-test-cases` |
| Backend | Django 5.2.17 / Python 3.12 |
| Database | PostgreSQL 16 Docker service |
| Storage | MinIO Docker service |
| Test runner | pytest |
| Command | `docker compose exec -T backend pytest apps/documents/tests/test_upload_api.py apps/documents/tests/test_documents_api.py -q` |

## Execution Output

```text
...................................                                      [100%]
35 passed in 14.72s
```

## Acceptance-Criteria Evidence

### AC-029 - Record Authenticated User

**Result:** Passed.

The upload flow associates the authenticated user with `Document.registered_by` and the `CARGA` audit event.

### AC-030 - Record Registration Date and Time

**Result:** Passed.

The document receives a populated `created_at` timestamp, and the audit event records its own timestamp.

### AC-031 and AC-032 - Associate and Store Registration Information

**Result:** Passed.

The registration fields are persisted on the document record, and the upload audit event is associated with that same document.

### AC-033 - Display Registration Information

**Result:** Passed.

The document API exposes the registered username and creation timestamp in its serialized representation.

### AC-034 - Preserve Registration Information

**Result:** Passed.

Allowed metadata updates do not overwrite `registered_by` or `created_at`.

### AC-035 - Prevent Unauthorized Modification

**Result:** Passed.

The metadata update endpoint does not accept registration fields as writable fields. A request attempting to change them leaves the original values intact while allowing the permitted metadata update.

## Defects

No defects were found in the executed US-006 tests.
