# US-008 - Create Contract Folder

## Traceability

| User Story | Acceptance Criteria | Test Cases |
|------------|---------------------|------------|
| US-008 | AC-046 - Create Contract Folder | TC-042 |
| US-008 | AC-047 - Store Contract Folder | TC-043 |
| US-008 | AC-048 - Prevent Duplicate Contract Folders | TC-044 |
| US-008 | AC-049 - Access Contract Folder | TC-045 |
| US-008 | AC-050 - Register Documents in Contract Folder | TC-046 |
| US-008 | AC-051 - Associate Folder with Contract | TC-047 |
| US-008 | AC-052 - Confirm Folder Creation | TC-048 |
| US-008 | AC-046, AC-051 | TC-049 |

## Scope Note

The current implementation creates a `DigitalRecord` automatically when a contract is created. Its storage prefix is provisioned in S3/MinIO through a marker object at `expedientes/<contract_number>/.expediente.json`. Documents can be registered directly against the contract and are stored under that prefix. There is no separate folder entity or standalone folder-creation endpoint; the contract creation endpoint is the current folder-creation workflow.

## Preconditions

- The backend is running with PostgreSQL and MinIO available.
- The user is authenticated.
- A valid client exists for the contract.
- Contract dates use ISO format `YYYY-MM-DD`.

## TC-042 - Create a contract folder for a valid contract

| Field | Value |
|-------|-------|
| Acceptance criterion | AC-046 |
| Flow type | Happy path |
| Objective | Verify that creating a valid contract creates its associated digital folder. |
| Steps | 1. Submit a valid contract. 2. Inspect the response and digital record. |
| Expected result | The endpoint returns `201`, creates a `DigitalRecord`, and exposes its storage prefix. |
| Automated evidence | `test_api.py::TestContractsApi::test_create_contract_generates_record_and_storage_folder` |
| Status | Passed |

## TC-043 - Store and expose the contract folder

| Field | Value |
|-------|-------|
| Acceptance criterion | AC-047 |
| Flow type | Happy path |
| Objective | Verify that the newly created folder is persisted and available to the document workflow. |
| Expected result | The digital record is stored, the storage marker exists, and the folder reports zero documents initially. |
| Automated evidence | `test_api.py::TestContractsApi::test_create_contract_generates_record_and_storage_folder`; `test_models.py::TestDigitalRecord::test_digital_record_is_created_automatically_with_contract` |
| Status | Passed |

## TC-044 - Attempt to create a duplicate contract folder

| Field | Value |
|-------|-------|
| Acceptance criterion | AC-048 |
| Flow type | Alternative flow |
| Objective | Verify that a second folder is not created for the same contract. |
| Expected result | The duplicate creation is rejected with `400` and the existing contract/folder remains unchanged. |
| Automated evidence | `test_models.py::TestDigitalRecord::test_only_one_digital_record_per_contract`; `test_api.py::TestContractsApi::test_create_rejects_duplicate_number` |
| Status | Passed at current contract boundary: the one-to-one `DigitalRecord` relationship prevents duplicate folders. The API rejects duplicate contract numbers. |

## TC-045 - Access an existing contract folder

| Field | Value |
|-------|-------|
| Acceptance criterion | AC-049 |
| Flow type | Happy path |
| Objective | Verify that an existing contract exposes its digital folder for management. |
| Expected result | The contract detail response returns the folder storage path and current document count. |
| Automated evidence | `test_api.py::TestContractsApi::test_retrieve_contract_exposes_existing_folder` |
| Status | Passed |

## TC-046 - Register a document in the contract folder

| Field | Value |
|-------|-------|
| Acceptance criterion | AC-050 |
| Flow type | Happy path |
| Objective | Verify that document registration associates the file with the selected contract folder. |
| Expected result | The uploaded document references the contract's `DigitalRecord` and its file path starts with the contract folder prefix. |
| Automated evidence | `test_upload_api.py::TestDocumentUpload::test_upload_with_contract_stores_file_in_record_prefix`; `test_api.py::TestContractsApi::test_contract_documents_returns_expediente_with_filters` |
| Status | Passed |

## TC-047 - Associate the folder with the correct contract

| Field | Value |
|-------|-------|
| Acceptance criterion | AC-051 |
| Flow type | Happy path |
| Objective | Verify that the folder association is relational and points to the intended contract. |
| Expected result | The `DigitalRecord.contract` relationship identifies the original contract and uses its deterministic storage path. |
| Automated evidence | `test_models.py::TestDigitalRecord::test_digital_record_is_created_automatically_with_contract`; `test_api.py::TestContractsApi::test_create_multiple_contracts_provisions_independent_folders` |
| Status | Passed |

## TC-048 - Confirm successful folder creation

| Field | Value |
|-------|-------|
| Acceptance criterion | AC-052 |
| Flow type | Happy path |
| Objective | Verify that the folder creation workflow provides a success confirmation. |
| Expected result | The API returns `201` with the created contract and digital record; the frontend displays a creation alert containing the contract number and folder path. |
| Automated evidence | `test_api.py::TestContractsApi::test_create_contract_generates_record_and_storage_folder`; frontend contract creation flow in `frontend/app/admin/contracts/page.tsx` |
| Status | Passed at API/frontend flow level; the API does not return a dedicated confirmation-message field. |

## TC-049 - Create multiple independent contract folders

| Field | Value |
|-------|-------|
| Acceptance criteria | AC-046, AC-051 |
| Flow type | Happy path |
| Objective | Verify that different contracts receive independent folders. |
| Expected result | Each contract is created successfully, has one digital record, and receives a distinct storage prefix. |
| Automated evidence | `test_api.py::TestContractsApi::test_create_multiple_contracts_provisions_independent_folders` |
| Status | Passed |

## Status Definitions

- **Passed:** The acceptance behavior was observed in an executable test.
- **Failed:** The executable test produced an unexpected result and requires a bug report.
- **Blocked:** The criterion depends on a product behavior absent from the current implementation.
