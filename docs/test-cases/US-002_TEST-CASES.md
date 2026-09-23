# US-002 - Upload Digital Document

## Traceability

| User Story | Acceptance Criteria | Test Cases |
|------------|---------------------|------------|
| US-002 | AC-005 - Upload Supported Digital Document; AC-006 - Associate Uploaded Document; AC-009 - Confirm Successful Upload | TC-004, TC-007, TC-008 |
| US-002 | AC-007 - Reject Unsupported File Format | TC-005 |
| US-002 | AC-008 - Reject File Exceeding Maximum Size | TC-006 |

## Preconditions

- The backend is running with PostgreSQL and MinIO available.
- The authenticated user can upload documents.
- The upload endpoint is `POST /api/v1/documents/upload/`.
- Supported formats are PDF, PNG, and JPEG.
- The configured maximum size is 25 MB unless overridden by the test.

## TC-004 - Upload a valid digital document

| Field | Value |
|-------|-------|
| Acceptance criteria | AC-005, AC-006, AC-009 |
| Flow type | Happy path |
| Objective | Verify that a valid file is uploaded, persisted, associated with a document record, and acknowledged successfully. |
| Input | A valid PDF document uploaded as multipart form data. |
| Steps | 1. Send a valid PDF to the upload endpoint. 2. Read the response. 3. Retrieve the created `Document`. 4. Verify the object exists in storage. |
| Expected result | The endpoint returns `201`, a document record is created, the file is stored, metadata is persisted, and the response contains the upload result. |
| Automated evidence | `test_upload_api.py::TestDocumentUpload::test_upload_registers_document_and_queues_processing` |

## TC-005 - Upload a file with an unsupported format

| Field | Value |
|-------|-------|
| Acceptance criterion | AC-007 |
| Flow type | Alternative flow |
| Objective | Verify that unsupported extensions are rejected without creating a document. |
| Input | `malware.exe` with an unsupported MIME type. |
| Steps | 1. Send the unsupported file to the upload endpoint. 2. Inspect the response and database. |
| Expected result | The endpoint returns `400`, includes a file validation error, creates no document, and does not queue processing. |
| Automated evidence | `test_upload_api.py::TestDocumentUpload::test_rejects_disallowed_extension` |

## TC-006 - Upload a file exceeding the maximum allowed size

| Field | Value |
|-------|-------|
| Acceptance criterion | AC-008 |
| Flow type | Alternative flow |
| Objective | Verify that oversized files are rejected with an informative validation error. |
| Input | A PDF larger than the configured test limit. |
| Steps | 1. Configure the test limit to 1 KB. 2. Send a 2 KB PDF. 3. Inspect the response and database. |
| Expected result | The endpoint returns `400`, states that the file exceeds the limit, and creates no document. |
| Automated evidence | `test_upload_api.py::TestDocumentUpload::test_rejects_file_over_size_limit` |

## TC-007 - Upload a valid document after a previous failed attempt

| Field | Value |
|-------|-------|
| Acceptance criteria | AC-005, AC-006, AC-009 |
| Flow type | Alternative flow |
| Objective | Verify that a rejected upload does not prevent a later valid upload. |
| Input | First an unsupported executable, then a valid PDF. |
| Steps | 1. Submit the unsupported file and verify rejection. 2. Submit a valid PDF. 3. Verify the response and document count. |
| Expected result | The first request returns `400`; the second returns `201` and creates exactly one valid document. |
| Automated evidence | `test_upload_api.py::TestDocumentUpload::test_valid_upload_succeeds_after_rejected_attempt` |

## TC-008 - Verify the uploaded document from its record

| Field | Value |
|-------|-------|
| Acceptance criterion | AC-006 |
| Flow type | Happy path |
| Objective | Verify that the uploaded file remains associated with its document record. |
| Input | A valid uploaded PDF. |
| Steps | 1. Upload the file. 2. Read the returned document ID. 3. Retrieve the document record. 4. Compare filename, hash, size, and storage path. |
| Expected result | The document record contains the uploaded file metadata and its storage object exists. |
| Automated evidence | `test_upload_api.py::TestDocumentUpload::test_upload_registers_document_and_queues_processing` |

## Notes on AC-009

The automated evidence validates a successful API response (`201`) and its confirmation payload. A separate browser test would be needed to verify the exact visual confirmation message in the frontend.
