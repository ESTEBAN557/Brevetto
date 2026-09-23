# US-001 - Generate Registration Number

## Traceability

| User Story | Acceptance Criteria | Test Cases |
|------------|---------------------|------------|
| US-001 | AC-001 - Automatic Registration Number Generation | TC-001 |
| US-001 | AC-003 - Registration Number Uniqueness | TC-002 |
| US-001 | AC-002 - Registration Number Association; AC-004 - Registration Number Display | TC-003 |

## Preconditions

- The backend is running with PostgreSQL and the `documents` migrations applied.
- The user has permission to register or consult documents.
- The filing number configuration uses the `RAD-YYYYMMDD-XXXXXX` format.

## TC-001 - Register a valid document

| Field | Value |
|-------|-------|
| Acceptance criterion | AC-001 |
| Flow type | Happy path |
| Objective | Verify that a valid registration receives a filing number automatically. |
| Input | A valid document registration with the required file metadata. |
| Steps | 1. Submit a valid document registration. 2. Complete the registration. 3. Read the generated filing number. |
| Expected result | The system generates a non-empty filing number in the format `RAD-YYYYMMDD-XXXXXX` without requiring manual input. |
| Automated evidence | `test_filing_sequence.py::TestFilingSequenceFormat::test_first_number_of_day_has_expected_format` |

## TC-002 - Register multiple documents

| Field | Value |
|-------|-------|
| Acceptance criterion | AC-003 |
| Flow type | Alternative flow |
| Objective | Verify that multiple registrations receive different sequential numbers, including concurrent registrations. |
| Input | Multiple valid registrations on the same date. |
| Steps | 1. Register several documents on the same date. 2. Repeat with concurrent callers. 3. Compare the assigned filing numbers. |
| Expected result | Every document receives a different filing number; concurrent calls do not produce duplicates or gaps. |
| Automated evidence | `test_filing_sequence.py::TestFilingSequenceFormat::test_numbers_are_sequential_within_same_day`; `test_filing_sequence.py::TestFilingSequenceConcurrency::test_ten_concurrent_callers_never_receive_duplicates` |

## TC-003 - Retrieve a registered document and review its information

| Field | Value |
|-------|-------|
| Acceptance criteria | AC-002, AC-004 |
| Flow type | Happy path |
| Objective | Verify that the generated filing number remains associated with the document and is displayed in document details. |
| Input | A previously registered document and its identifier. |
| Steps | 1. Register a valid document. 2. Save the generated filing number. 3. Retrieve the document details. 4. Compare the displayed filing number with the saved value. |
| Expected result | The returned document contains the same filing number generated during registration. |
| Automated evidence | `test_upload_api.py::TestDocumentUpload::test_upload_registers_document_and_queues_processing`; `test_documents_api.py::TestDocumentQueries::test_retrieve_exposes_full_metadata` |
| Current status | Covered. The upload test verifies the response filing number, persisted `Document.filing_number`, and storage path; the query test verifies document-detail retrieval. |

## Execution Status Definitions

- **Passed:** The expected result was observed in an executable test.
- **Failed:** The executable test produced an unexpected result; create or link a bug report.
- **Blocked:** Execution requires an unavailable dependency or endpoint.
- **Pending:** The case is designed but does not yet have a dedicated executable assertion.
