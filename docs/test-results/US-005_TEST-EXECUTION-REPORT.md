# US-005 - Test Execution Report

## Execution Summary

| Test Case | Acceptance Criteria | Status | Evidence |
|-----------|---------------------|--------|----------|
| TC-019 - Enter document metadata | AC-021 | Passed | Metadata capture during upload |
| TC-020 - Missing required metadata | AC-022, AC-023 | Blocked | Current serializer treats metadata fields as optional |
| TC-021 - Invalid metadata format | AC-024 | Passed | Invalid date format validation |
| TC-022 - Store and associate metadata | AC-025, AC-026 | Passed | Metadata persistence test |
| TC-023 - Review document metadata | AC-027 | Passed | Document-detail metadata test |
| TC-024 - Modify metadata before confirmation | AC-028 | Blocked | No draft-registration flow exists |

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
..................................                                       [100%]
34 passed in 11.75s
```

## Acceptance-Criteria Evidence

### AC-021 - Enter Document Metadata

**Result:** Passed at API level.

The upload registration accepts `document_date` and `external_sender_name` and stores them on the document record.

### AC-022 and AC-023 - Validate Required Metadata

**Result:** Blocked by the current contract.

The current serializer marks both metadata fields as optional. Therefore, the product does not currently define a missing-metadata rejection behavior to execute. This is a specification/implementation gap, not a failed test.

### AC-024 - Validate Metadata Format

**Result:** Passed.

An invalid date such as `20/09/2026` returns `400`, identifies `document_date`, and creates no document.

### AC-025 and AC-026 - Store and Associate Metadata

**Result:** Passed.

Valid metadata is persisted on the created `Document` record and remains associated with it.

### AC-027 - Review Document Metadata

**Result:** Passed.

The document detail endpoint returns the stored date and external sender metadata.

### AC-028 - Modify Metadata Before Confirmation

**Result:** Blocked.

The current system has no draft-registration state. Metadata modification exists after record creation through the US-007 endpoint, which is a different flow.

## Defects and Gaps

No defects were found in the executed US-005 tests. The open gaps are:

- Metadata fields are optional although the story describes required metadata.
- Editing metadata before confirmation is not implemented.
