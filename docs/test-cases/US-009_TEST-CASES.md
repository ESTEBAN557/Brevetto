# US-009 - Process Document Content

## Traceability

| User Story | Acceptance Criteria | Test Cases |
|------------|---------------------|------------|
| US-009 | AC-052 - Process Uploaded Document; AC-053 - Extract Document Information | TC-048 |
| US-009 | AC-054 - Confirm Successful Processing | TC-049 |
| US-009 | AC-055 - Handle Processing Failure | TC-050 |
| US-009 | AC-056 - Preserve Source Document | TC-051 |
| US-009 | AC-057 - Associate Processed Information with Source Document | TC-052 |
| US-009 | AC-058 - Make Processing Status Available | TC-053 |

## Scope Note

Document processing is implemented by the Celery task `documents.process_document_content`. The task reads the stored source file, sends its bytes to the extraction service, applies the classification pipeline, stores extracted information on `Document.ai_extracted_data`, and updates `processing_status`. High-confidence results are archived automatically; low-confidence or unresolved results go to human review. Transient failures are retried and definitive failures are marked as `FALLIDO`.

## Preconditions

- The backend is running with PostgreSQL and MinIO available.
- Celery task execution is available through the eager test configuration.
- The uploaded source document exists in storage.
- External Gemini calls are mocked; tests do not use the network.

## TC-048 - Process a readable uploaded document

| Field | Value |
|-------|-------|
| Acceptance criteria | AC-052, AC-053 |
| Flow type | Happy path |
| Objective | Verify that the task reads the uploaded bytes, extracts information, and applies the classification result. |
| Steps | 1. Store a source document. 2. Mock the extractor with readable-document metadata. 3. Execute the processing task. 4. Inspect the document record. |
| Expected result | The task succeeds, extracted fields are stored, document metadata is classified, and the document reaches `PROCESADO` when confidence and contract resolution are sufficient. |
| Automated evidence | `test_tasks.py::TestProcessDocumentContentTask::test_high_confidence_with_known_contract_is_auto_classified`; `test_tasks.py::TestProcessDocumentContentTask::test_status_is_processing_while_model_runs` |
| Status | Passed |

## TC-049 - Complete processing and make the result available

| Field | Value |
|-------|-------|
| Acceptance criterion | AC-054 |
| Flow type | Happy path |
| Objective | Verify that successful processing returns a completed result for the next workflow stage. |
| Expected result | The task result contains the document ID and `PROCESADO` status; extracted metadata and classification are persisted. |
| Automated evidence | `test_tasks.py::TestProcessDocumentContentTask::test_high_confidence_with_known_contract_is_auto_classified` |
| Status | Passed |

## TC-050 - Handle a processing failure

| Field | Value |
|-------|-------|
| Acceptance criterion | AC-055 |
| Flow type | Alternative flow |
| Objective | Verify that an unrecoverable extraction failure is represented as a failed processing state and recorded for follow-up. |
| Expected result | After the configured retries, the task fails, the document status becomes `FALLIDO`, and the audit entry records the error and retry count. |
| Automated evidence | `test_tasks.py::TestProcessDocumentContentTask::test_persistent_error_marks_document_failed_after_max_retries` |
| Status | Passed |

## TC-051 - Preserve the source document after failure

| Field | Value |
|-------|-------|
| Acceptance criterion | AC-056 |
| Flow type | Alternative flow |
| Objective | Verify that processing failure does not modify or lose the original stored file. |
| Expected result | The source bytes are identical before and after the definitive processing failure. |
| Automated evidence | `test_tasks.py::TestProcessDocumentContentTask::test_persistent_error_marks_document_failed_after_max_retries` |
| Status | Passed |

## TC-052 - Associate processed information with the source document

| Field | Value |
|-------|-------|
| Acceptance criterion | AC-057 |
| Flow type | Happy path |
| Objective | Verify that extracted information and classification remain attached to the document that was processed. |
| Expected result | The processed document stores the extracted data, confidence score, document type, dates, and resolved digital record on the same source record. |
| Automated evidence | `test_tasks.py::TestProcessDocumentContentTask::test_high_confidence_with_known_contract_is_auto_classified`; `test_tasks.py::TestClassificationService::test_apply_classification_keeps_existing_dates_when_ai_has_none` |
| Status | Passed |

## TC-053 - Make processing status available

| Field | Value |
|-------|-------|
| Acceptance criterion | AC-058 |
| Flow type | Happy path |
| Objective | Verify that processing status and extracted information are visible through the document API. |
| Expected result | The detail response exposes `processing_status`, `ai_extracted_data`, and `ai_confidence_score`. |
| Automated evidence | `test_documents_api.py::TestDocumentQueries::test_retrieve_exposes_processing_status_and_extracted_information`; `test_tasks.py::TestProcessDocumentContentTask::test_status_is_processing_while_model_runs` |
| Status | Passed |

## Additional Processing Coverage

The pipeline also covers low-confidence results and unavailable AI configuration by routing the document to `REQUIERE_REVISION`, transient errors through retry, unknown documents as `NOT_FOUND`, and stable Celery task registration.

## Status Definitions

- **Passed:** The acceptance behavior was observed in an executable test.
- **Failed:** The executable test produced an unexpected result and requires a bug report.
- **Blocked:** The criterion depends on a product behavior absent from the current implementation.
