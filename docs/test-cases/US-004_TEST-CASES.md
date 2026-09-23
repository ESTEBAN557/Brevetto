# US-004 - Create Document Record

## Traceability

| User Story | Acceptance Criteria | Test Cases |
|------------|---------------------|------------|
| US-004 | AC-015 - Start Document Registration | TC-014 |
| US-004 | AC-016 - Create Document Record; AC-017 - Generate Registration Number; AC-018 - Store Document Record | TC-015, TC-018 |
| US-004 | AC-019 - Validate Required Information | TC-016 |
| US-004 | AC-020 - Cancel Document Registration | TC-017 |

## Scope Note

In the current implementation, the registration form is the multipart payload accepted by `POST /api/v1/documents/upload/`. There is no separate draft-registration screen or cancel-registration endpoint in the current backend.

## Preconditions

- The backend is running with PostgreSQL and MinIO available.
- The user is authenticated.
- The registration endpoint is `POST /api/v1/documents/upload/`.

## TC-014 - Start the document registration process

| Field | Value |
|-------|-------|
| Acceptance criterion | AC-015 |
| Flow type | Happy path |
| Objective | Verify that the registration request accepts the required document input and registration fields. |
| Steps | 1. Open the registration/upload flow. 2. Submit multipart data containing a file. 3. Verify the request is processed by the registration serializer. |
| Expected result | The registration flow accepts the required file and available fields such as source channel, contract, document date, and sender. |
| Automated evidence | `test_upload_api.py::TestDocumentUpload::test_upload_registers_document_and_queues_processing` |
| Status | Passed at API/form contract level. A dedicated browser form test is not included in pytest. |

## TC-015 - Complete the required information and confirm registration

| Field | Value |
|-------|-------|
| Acceptance criteria | AC-016, AC-017, AC-018 |
| Flow type | Happy path |
| Objective | Verify that confirmation creates and stores a document record with a generated filing number. |
| Steps | 1. Submit a valid PDF. 2. Read the response. 3. Retrieve the persisted `Document`. 4. Verify its state and metadata. |
| Expected result | The endpoint returns `201`; a document record is created in `RECIBIDO` state, stored in MinIO, and returned with a filing number. |
| Automated evidence | `test_upload_api.py::TestDocumentUpload::test_upload_registers_document_and_queues_processing` |
| Status | Passed |

## TC-016 - Confirm registration with required information missing

| Field | Value |
|-------|-------|
| Acceptance criterion | AC-019 |
| Flow type | Alternative flow |
| Objective | Verify that registration is rejected when the required file is missing. |
| Steps | 1. Submit the registration form without a file. 2. Inspect the response and database. |
| Expected result | The endpoint returns `400`, identifies the missing `file`, and creates no document record. |
| Automated evidence | `test_upload_api.py::TestDocumentUpload::test_rejects_registration_without_required_file` |
| Status | Passed |

## TC-017 - Cancel registration before confirmation

| Field | Value |
|-------|-------|
| Acceptance criterion | AC-020 |
| Flow type | Alternative flow |
| Objective | Verify that cancelling a started registration creates no record or filing number. |
| Expected result | Cancellation ends the draft flow without persistence or sequence allocation. |
| Automated evidence | None. No draft-registration state or cancellation endpoint exists in the current backend. |
| Status | Blocked: cancellation is not implemented in the current scope. |

## TC-018 - Verify registration number association

| Field | Value |
|-------|-------|
| Acceptance criterion | AC-017 |
| Flow type | Happy path |
| Objective | Verify that the generated filing number is associated with the stored document record. |
| Steps | 1. Complete a valid registration. 2. Read the response filing number. 3. Retrieve the created record. 4. Compare both values. |
| Expected result | The response filing number matches `Document.filing_number`, which is unique and persisted. |
| Automated evidence | `test_upload_api.py::TestDocumentUpload::test_upload_registers_document_and_queues_processing`; `test_models.py::TestDocument::test_filing_number_is_unique` |
| Status | Passed |

## Status Definitions

- **Passed:** The acceptance behavior was observed in an executable test.
- **Failed:** The executable test produced an unexpected result and requires a bug report.
- **Blocked:** The case depends on functionality that is not implemented in the current scope.
