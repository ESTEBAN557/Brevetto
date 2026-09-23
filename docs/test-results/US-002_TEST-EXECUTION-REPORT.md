# US-002 - Test Execution Report

## Execution Summary

| Test Case | Acceptance Criteria | Status | Evidence |
|-----------|---------------------|--------|----------|
| TC-004 - Upload a valid digital document | AC-005, AC-006, AC-009 | Passed | Valid upload, persistence, storage, and `201` response test |
| TC-005 - Upload an unsupported format | AC-007 | Passed | Extension validation test |
| TC-006 - Upload an oversized file | AC-008 | Passed | Maximum-size validation test |
| TC-007 - Valid upload after failed attempt | AC-005, AC-006, AC-009 | Passed | Explicit recovery-flow test |
| TC-008 - Verify uploaded document from its record | AC-006 | Passed | Persisted `Document` and storage assertions |

## Environment

| Field | Value |
|-------|-------|
| Execution date | 2026-09-23 |
| Branch | `docs/sprint1-test-cases` |
| Backend | Django 5.2.17 / Python 3.12 |
| Database | PostgreSQL 16 Docker service |
| Storage | MinIO Docker service |
| Test runner | pytest |
| Command | `docker compose exec -T backend pytest apps/documents/tests/test_upload_api.py -q` |

## Execution Output

```text
................                                                         [100%]
16 passed in 8.43s
```

## Acceptance-Criteria Evidence

### AC-005 - Upload Supported Digital Document

**Result:** Passed.

Valid PDF, PNG, and JPEG uploads are accepted. The main PDF flow returns `201` and creates a document record.

### AC-006 - Associate Uploaded Document

**Result:** Passed.

The upload response returns the document ID. The test retrieves the persisted record and verifies filename, size, MIME type, checksum, storage path, and stored object.

### AC-007 - Reject Unsupported File Format

**Result:** Passed.

An `.exe` upload returns `400`, reports a file validation error, creates no document, and does not queue processing.

### AC-008 - Reject File Exceeding Maximum Size

**Result:** Passed.

An oversized upload returns `400`, includes an informative size validation message, and creates no document.

### AC-009 - Confirm Successful Upload

**Result:** Passed at API level.

Successful uploads return HTTP `201` and a response payload containing the registered document information. The exact visual confirmation message in the frontend was not tested by this pytest suite.

## Defects

No defects were found in the executed US-002 upload tests.
