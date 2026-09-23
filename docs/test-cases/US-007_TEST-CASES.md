# US-007 - Update Document Metadata

## Traceability

| User Story | Acceptance Criteria | Test Cases |
|------------|---------------------|------------|
| US-007 | AC-036 - Edit Document Metadata | TC-031 |
| US-007 | AC-037 - Validate Updated Metadata; AC-039 - Update Document Record | TC-032 |
| US-007 | AC-038 - Validate Required Metadata | TC-033 |
| US-007 | AC-039 - Update Document Record | TC-034 |
| US-007 | AC-040 - Confirm Successful Update | TC-035 |
| US-007 | AC-041 - Display Updated Metadata | TC-036 |
| US-007 | AC-042 - Maintain Document Record Integrity | TC-037 |
| US-007 | AC-043 - Record Metadata Update | TC-038 |
| US-007 | AC-044 - Cancel Metadata Update | TC-039 |

## Scope Note

Metadata editing is implemented through `PATCH /api/v1/documents/{id}/metadata/`. The editable fields are `document_type`, `expiration_date`, `document_date`, and `external_sender_name`. The endpoint returns the updated document representation and creates an immutable `ACTUALIZACION_METADATOS` audit event. There is no separate draft state, required metadata field, or cancellation endpoint in the current backend contract.

## Preconditions

- The backend is running with PostgreSQL and MinIO available.
- The user is authenticated.
- A document record already exists.
- Metadata dates use ISO format `YYYY-MM-DD`.

## TC-031 - Edit one editable metadata field

| Field | Value |
|-------|-------|
| Acceptance criterion | AC-036 |
| Flow type | Happy path |
| Objective | Verify that an authorized user can edit an allowed metadata field. |
| Steps | 1. Send a metadata PATCH with a new external sender. 2. Reload the document. |
| Expected result | The request returns `200` and the editable field contains the new value. |
| Automated evidence | `test_documents_api.py::TestMetadataUpdate::test_patch_updates_one_editable_field` |
| Status | Passed |

## TC-032 - Save modified metadata with valid values

| Field | Value |
|-------|-------|
| Acceptance criteria | AC-037, AC-039 |
| Flow type | Happy path |
| Objective | Verify validation and persistence when valid metadata is submitted. |
| Expected result | The endpoint returns `200`, returns the updated metadata, and persists the values in the document record. |
| Automated evidence | `test_documents_api.py::TestMetadataUpdate::test_patch_logs_previous_and_new_values` |
| Status | Passed |

## TC-033 - Attempt to save incomplete required metadata

| Field | Value |
|-------|-------|
| Acceptance criterion | AC-038 |
| Flow type | Alternative flow |
| Objective | Verify that empty required metadata is rejected with a validation message. |
| Expected result | The update returns `400`, identifies the invalid field, and does not change the document. |
| Automated evidence | `test_documents_api.py::TestMetadataUpdate::test_patch_rejects_invalid_date_format_without_saving` validates malformed metadata; no required metadata field is currently configured. |
| Status | Blocked by current contract: all metadata fields are optional and nullable/blank where applicable. |

## TC-034 - Update multiple metadata fields in one operation

| Field | Value |
|-------|-------|
| Acceptance criterion | AC-039 |
| Flow type | Happy path |
| Objective | Verify that several editable fields can be saved atomically in one PATCH. |
| Expected result | The response and persisted document contain the new document type and expiration date, and the audit change set contains both fields. |
| Automated evidence | `test_documents_api.py::TestMetadataUpdate::test_patch_logs_previous_and_new_values` |
| Status | Passed |

## TC-035 - Confirm successful metadata update

| Field | Value |
|-------|-------|
| Acceptance criterion | AC-040 |
| Flow type | Happy path |
| Objective | Verify the successful-update confirmation returned by the API. |
| Expected result | The endpoint returns `200` and the response contains the updated metadata representation. |
| Automated evidence | `test_documents_api.py::TestMetadataUpdate::test_patch_returns_updated_metadata_as_confirmation` |
| Status | Passed at API level; no user-facing confirmation text is returned by the current endpoint. |

## TC-036 - View the document after updating metadata

| Field | Value |
|-------|-------|
| Acceptance criterion | AC-041 |
| Flow type | Happy path |
| Objective | Verify that the document detail view exposes the saved metadata. |
| Expected result | A subsequent document detail request returns the updated date and external sender. |
| Automated evidence | `test_documents_api.py::TestMetadataUpdate::test_detail_displays_updated_metadata` |
| Status | Passed |

## TC-037 - Preserve existing document information

| Field | Value |
|-------|-------|
| Acceptance criterion | AC-042 |
| Flow type | Happy path |
| Objective | Verify that updating metadata does not alter the filing or file information. |
| Expected result | Filing number, filename, storage path, hash, file size, and processing status remain unchanged. |
| Automated evidence | `test_documents_api.py::TestMetadataUpdate::test_patch_preserves_existing_document_information`; `test_documents_api.py::TestMetadataUpdate::test_metadata_update_cannot_change_registration_information` |
| Status | Passed |

## TC-038 - Record the metadata update for audit

| Field | Value |
|-------|-------|
| Acceptance criterion | AC-043 |
| Flow type | Happy path |
| Objective | Verify that each successful update creates an audit record with previous and new values. |
| Expected result | An immutable `ACTUALIZACION_METADATOS` event is linked to the document and lists the changed fields and values. |
| Automated evidence | `test_documents_api.py::TestMetadataUpdate::test_patch_logs_previous_and_new_values` |
| Status | Passed |

## TC-039 - Cancel metadata update before saving

| Field | Value |
|-------|-------|
| Acceptance criterion | AC-044 |
| Flow type | Alternative flow |
| Objective | Verify that cancelling an edit discards unsaved changes. |
| Expected result | The previously stored metadata remains unchanged and no update audit event is created. |
| Automated evidence | None. The current backend has no cancellation endpoint or draft-edit state. |
| Status | Blocked: cancellation is not implemented in the current scope. |

## Status Definitions

- **Passed:** The acceptance behavior was observed in an executable test.
- **Failed:** The executable test produced an unexpected result and requires a bug report.
- **Blocked:** The criterion depends on a product behavior absent from the current implementation.
