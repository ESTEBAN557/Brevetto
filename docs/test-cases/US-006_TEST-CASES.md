# US-006 - Record Registration Information

## Traceability

| User Story | Acceptance Criteria | Test Cases |
|------------|---------------------|------------|
| US-006 | AC-029 - Record Authenticated User; AC-030 - Record Registration Date and Time | TC-025, TC-030 |
| US-006 | AC-031 - Associate Registration Information; AC-032 - Store Registration Information | TC-026 |
| US-006 | AC-033 - Display Registration Information | TC-027 |
| US-006 | AC-034 - Preserve Registration Information | TC-028 |
| US-006 | AC-035 - Prevent Unauthorized Modification | TC-029 |

## Scope Note

Registration information is stored on `Document` through `registered_by` and `created_at`. The upload audit event also stores the actor and timestamp. Registration fields are read-only in the document serializer; metadata updates are handled separately through `PATCH /api/v1/documents/{id}/metadata/`.

## Preconditions

- The backend is running with PostgreSQL and MinIO available.
- The user is authenticated for registration and document detail requests.
- The registration endpoint is `POST /api/v1/documents/upload/`.

## TC-025 - Register a document while authenticated

| Field | Value |
|-------|-------|
| Acceptance criteria | AC-029, AC-030 |
| Flow type | Happy path |
| Objective | Verify that the authenticated actor and registration timestamp are captured automatically. |
| Steps | 1. Upload a valid document as an authenticated user. 2. Read the created `Document` and upload audit event. |
| Expected result | `registered_by` references the authenticated user, `created_at` is populated, and the audit event identifies the same actor. |
| Automated evidence | `test_upload_api.py::TestDocumentUpload::test_upload_registers_document_and_queues_processing` |
| Status | Passed |

## TC-026 - Associate and store registration information

| Field | Value |
|-------|-------|
| Acceptance criteria | AC-031, AC-032 |
| Flow type | Happy path |
| Objective | Verify that registration information belongs to the created document record and is persisted. |
| Steps | 1. Register a document. 2. Retrieve it from PostgreSQL. 3. Inspect its registration fields and upload audit entry. |
| Expected result | The document stores `registered_by` and `created_at`; the audit entry is linked to the same document. |
| Automated evidence | `test_upload_api.py::TestDocumentUpload::test_upload_registers_document_and_queues_processing`; `test_documents_api.py::TestDocumentQueries::test_list_is_paginated_and_newest_first` |
| Status | Passed |

## TC-027 - View a successfully registered document

| Field | Value |
|-------|-------|
| Acceptance criterion | AC-033 |
| Flow type | Happy path |
| Objective | Verify that the document detail/list response displays the registration user and timestamp. |
| Expected result | The API returns the registered username and non-null `created_at`. |
| Automated evidence | `test_documents_api.py::TestDocumentQueries::test_list_is_paginated_and_newest_first`; `test_documents_api.py::TestDocumentQueries::test_retrieve_exposes_full_metadata` |
| Status | Passed |

## TC-028 - Preserve original registration information

| Field | Value |
|-------|-------|
| Acceptance criterion | AC-034 |
| Flow type | Happy path |
| Objective | Verify that retrieving or updating allowed metadata does not overwrite the original registration data. |
| Expected result | The original `registered_by` and `created_at` remain unchanged after retrieval and metadata updates. |
| Automated evidence | `test_documents_api.py::TestMetadataUpdate::test_metadata_update_cannot_change_registration_information` |
| Status | Passed |

## TC-029 - Attempt unauthorized modification

| Field | Value |
|-------|-------|
| Acceptance criterion | AC-035 |
| Flow type | Alternative flow |
| Objective | Verify that registration information cannot be changed through the metadata update endpoint. |
| Steps | 1. Send `registered_by` and `created_at` in a metadata PATCH request. 2. Reload the document. 3. Compare the original values. |
| Expected result | The endpoint does not modify registration information; allowed metadata may still be updated. |
| Automated evidence | `test_documents_api.py::TestMetadataUpdate::test_metadata_update_cannot_change_registration_information` |
| Status | Passed |

## TC-030 - Register multiple documents independently

| Field | Value |
|-------|-------|
| Acceptance criteria | AC-029, AC-030, AC-031 |
| Flow type | Happy path |
| Objective | Verify that each document retains its own registration information. |
| Expected result | Each document has its own filing record, actor association, and creation timestamp. |
| Automated evidence | `test_upload_api.py::TestBatchUpload::test_batch_upload_registers_every_file` |
| Status | Passed at record-isolation level; batch test verifies independent document records and filing numbers. |
