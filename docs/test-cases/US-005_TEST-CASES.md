# US-005 - Capture Document Metadata

## Traceability

| User Story | Acceptance Criteria | Test Cases |
|------------|---------------------|------------|
| US-005 | AC-021 - Enter Document Metadata | TC-019 |
| US-005 | AC-022 - Validate Required Metadata; AC-023 - Handle Missing Metadata | TC-020 |
| US-005 | AC-024 - Validate Metadata Format | TC-021 |
| US-005 | AC-025 - Store Document Metadata; AC-026 - Associate Metadata | TC-022 |
| US-005 | AC-027 - Review Document Metadata | TC-023 |
| US-005 | AC-028 - Modify Metadata Before Confirmation | TC-024 |

## Scope Note

The current API captures `document_date` and `external_sender_name` during `POST /api/v1/documents/upload/`. These fields are optional in the current serializer. Metadata editing is available through `PATCH /api/v1/documents/{id}/metadata/` after a record exists, but there is no draft-registration state for editing before confirmation.

## Preconditions

- The backend is running with PostgreSQL and MinIO available.
- The user is authenticated.
- The registration endpoint is `POST /api/v1/documents/upload/`.
- Metadata dates use ISO format `YYYY-MM-DD`.

## TC-019 - Enter document metadata

| Field | Value |
|-------|-------|
| Acceptance criterion | AC-021 |
| Flow type | Happy path |
| Objective | Verify that the registration request accepts document metadata. |
| Steps | 1. Submit a valid file with `document_date` and `external_sender_name`. 2. Retrieve the created record. |
| Expected result | The metadata is accepted and associated with the uploaded document. |
| Automated evidence | `test_upload_api.py::TestDocumentUpload::test_upload_stores_document_metadata` |
| Status | Passed at API level |

## TC-020 - Complete registration without all required metadata

| Field | Value |
|-------|-------|
| Acceptance criteria | AC-022, AC-023 |
| Flow type | Alternative flow |
| Objective | Verify that missing required metadata prevents registration. |
| Expected result | The system rejects the request and displays validation messages for each missing required metadata field. |
| Automated evidence | No failing test is appropriate because the current serializer marks `document_date` and `external_sender_name` as optional. |
| Status | Blocked by current contract: no metadata field is required beyond the file. |

## TC-021 - Enter invalid metadata format

| Field | Value |
|-------|-------|
| Acceptance criterion | AC-024 |
| Flow type | Alternative flow |
| Objective | Verify that an invalid date format is rejected. |
| Input | `document_date=20/09/2026` |
| Expected result | The endpoint returns `400`, identifies `document_date`, and creates no record. |
| Automated evidence | `test_upload_api.py::TestDocumentUpload::test_rejects_invalid_document_date_format` |
| Status | Passed |

## TC-022 - Store valid metadata with the document

| Field | Value |
|-------|-------|
| Acceptance criteria | AC-025, AC-026 |
| Flow type | Happy path |
| Objective | Verify that valid metadata is persisted and associated with the created record. |
| Expected result | The database record contains the submitted date and sender, linked to the uploaded document. |
| Automated evidence | `test_upload_api.py::TestDocumentUpload::test_upload_stores_document_metadata` |
| Status | Passed |

## TC-023 - Review document metadata

| Field | Value |
|-------|-------|
| Acceptance criterion | AC-027 |
| Flow type | Happy path |
| Objective | Verify that stored metadata is displayed by the document detail endpoint. |
| Expected result | The detail response returns the stored `document_date` and `external_sender_name`. |
| Automated evidence | `test_documents_api.py::TestDocumentQueries::test_retrieve_exposes_full_metadata` |
| Status | Passed |

## TC-024 - Modify metadata before confirmation

| Field | Value |
|-------|-------|
| Acceptance criterion | AC-028 |
| Flow type | Alternative flow |
| Objective | Verify that edits made to a draft are used at final confirmation. |
| Expected result | The final record contains the latest draft values. |
| Automated evidence | No draft-registration test exists. The current API supports metadata changes only after creation through the US-007 metadata endpoint. |
| Status | Blocked: draft editing before confirmation is not implemented. |

## Status Definitions

- **Passed:** The acceptance behavior was observed in an executable test.
- **Failed:** The executable test produced an unexpected result and requires a bug report.
- **Blocked:** The criterion depends on a product behavior absent from the current implementation.
