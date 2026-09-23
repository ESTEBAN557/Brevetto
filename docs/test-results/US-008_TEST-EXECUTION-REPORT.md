# US-008 - Test Execution Report

## Execution Summary

| Test Case | Acceptance Criteria | Status | Evidence |
|-----------|---------------------|--------|----------|
| TC-042 - Create folder for valid contract | AC-046 | Passed | Contract creation and digital record assertions |
| TC-043 - Store contract folder | AC-047 | Passed | Database record and storage marker assertions |
| TC-044 - Duplicate folder attempt | AC-048 | Passed at current contract boundary | One-to-one record and duplicate contract validation |
| TC-045 - Access existing folder | AC-049 | Passed | Contract detail exposes digital record |
| TC-046 - Register documents in folder | AC-050 | Passed | Upload association and contract document listing |
| TC-047 - Associate folder with contract | AC-051 | Passed | Digital record relationship and storage path assertions |
| TC-048 - Confirm folder creation | AC-052 | Passed at API/frontend flow level | HTTP 201 response and frontend success alert |
| TC-049 - Multiple independent folders | AC-046, AC-051 | Passed | Distinct records and storage prefixes |

## Environment

| Field | Value |
|-------|-------|
| Execution date | 2026-09-23 |
| Branch | `docs/sprint1-test-cases` |
| Backend | Django 5.2.17 / Python 3.12 |
| Database | PostgreSQL 16 Docker service |
| Storage | MinIO Docker service |
| Test runner | pytest |
| Command | `docker compose exec -T backend pytest apps/core/tests/test_api.py apps/core/tests/test_models.py apps/documents/tests/test_upload_api.py -q` |

## Execution Output

```text
.................................................                        [100%]
49 passed in 16.19s
```

Focused validation after adding explicit access coverage:

```text
................                                                         [100%]
16 passed in 12.72s
```

## Acceptance-Criteria Evidence

### AC-046 - Create Contract Folder

**Result:** Passed.

Creating a valid contract automatically creates its `DigitalRecord` and deterministic storage prefix.

### AC-047 - Store Contract Folder

**Result:** Passed.

The `DigitalRecord` is persisted and the storage marker `.expediente.json` is created under the record prefix.

### AC-048 - Prevent Duplicate Contract Folders

**Result:** Passed at the current contract boundary.

Each contract has one `DigitalRecord` through a database one-to-one relationship. Duplicate contract creation is rejected when the contract number already exists.

### AC-049 - Access Contract Folder

**Result:** Passed.

The authenticated contract detail endpoint exposes the existing digital record, storage path, and document count.

### AC-050 - Register Documents in Contract Folder

**Result:** Passed.

Uploading a document with a contract associates it with the contract's digital record and stores the file under that record's prefix. The contract documents endpoint lists the document.

### AC-051 - Associate Folder with Contract

**Result:** Passed.

The persisted `DigitalRecord.contract` relationship and deterministic prefix preserve the association with the correct contract.

### AC-052 - Confirm Folder Creation

**Result:** Passed at API/frontend flow level.

The API returns HTTP `201` with the created folder data, and the frontend contract creation flow displays a success alert containing the contract number and folder path. There is no dedicated confirmation-message field in the API response.

## Defects and Gaps

No defects were found in the executed US-008 tests.

Implementation boundary:

- The system models a contract folder as a `DigitalRecord` plus a storage prefix; there is no separate folder entity or standalone folder-creation endpoint.
