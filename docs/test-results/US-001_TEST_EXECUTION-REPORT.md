# US-001 - Test Execution

## Purpose

This page records the execution results for the test cases associated with US-001, Generate Registration Number.

The report separates implemented behavior from behavior that depends on the document record and document API planned for subsequent stories.

## Execution Summary

| Test Case | User Story | Acceptance Criterion | Execution Status | Result | Evidence | Bug |
|-----------|------------|-----------------------|------------------|--------|----------|-----|
| TC-001 | US-001 | AC-001 | Passed | Registration number generated in the expected format | `TestFilingSequence.test_first_number_has_expected_format` | None |
| TC-002 | US-001 | AC-002 | Blocked | Document model association is not part of this commit | No document record/API exists yet | Dependency: US-004 |
| TC-003 | US-001 | AC-003 | Passed | Sequential registrations receive different numbers | `TestFilingSequence.test_numbers_are_sequential_per_day` | None |
| TC-004 | US-001 | AC-004 | Blocked | Document detail endpoint/UI is not part of this commit | No document detail endpoint exists yet | Dependency: US-004 |
| TC-005 | US-001 | AC-003 | Passed | 50 concurrent calls received unique, consecutive numbers | `test_concurrent_callers_receive_unique_numbers` | None |

## Execution Environment

| Field | Value |
|-------|-------|
| **Execution Date** | 2026-09-22 |
| **Executed By** | Esteban Alvarez Garcia |
| **Repository** | Brevetto |
| **Branch** | `feature/US-001-generate-registration-number` |
| **Backend** | Django 5 / Python 3.12 container |
| **Database** | PostgreSQL 16 container |
| **Test Runner** | pytest |
| **Command** | `docker compose run --rm --entrypoint pytest backend apps/documents/tests/test_filing_sequence.py -q --junitxml=/tmp/us001-junit.xml` |

## Execution Results

### TC-001 - Generate Registration Number for a New Document

| Field | Value |
|-------|-------|
| **Test Case** | TC-001 |
| **User Story** | US-001 |
| **Acceptance Criterion** | AC-001 |
| **Execution Date** | 2026-09-22 |
| **Status** | Passed |
| **Expected Result** | A valid registration produces a number in the format `RAD-YYYYMMDD-XXXXXX`. |
| **Observed Result** | `RAD-20260920-000001` was generated. |
| **Evidence** | `backend/apps/documents/tests/test_filing_sequence.py::TestFilingSequence::test_first_number_has_expected_format` |
| **Bug** | None |

### TC-002 - Preserve Registration Number After Registration

| Field | Value |
|-------|-------|
| **Test Case** | TC-002 |
| **User Story** | US-001 |
| **Acceptance Criterion** | AC-002 |
| **Execution Date** | 2026-09-22 |
| **Status** | Blocked |
| **Expected Result** | The generated number remains associated with the registered document. |
| **Observed Result** | Cannot execute: the `Document` model and document registration endpoint are scheduled for US-004. |
| **Evidence** | Blocker recorded; no document persistence contract exists in this commit. |
| **Bug** | None; pending dependency US-004 |

### TC-003 - Generate Different Numbers for Multiple Documents

| Field | Value |
|-------|-------|
| **Test Case** | TC-003 |
| **User Story** | US-001 |
| **Acceptance Criterion** | AC-003 |
| **Execution Date** | 2026-09-22 |
| **Status** | Passed |
| **Expected Result** | Each registration on the same day receives a different sequential number. |
| **Observed Result** | Three calls returned `RAD-20260920-000001`, `RAD-20260920-000002`, and `RAD-20260920-000003`. |
| **Evidence** | `backend/apps/documents/tests/test_filing_sequence.py::TestFilingSequence::test_numbers_are_sequential_per_day` |
| **Bug** | None |

### TC-004 - Display Registration Number in Document Information

| Field | Value |
|-------|-------|
| **Test Case** | TC-004 |
| **User Story** | US-001 |
| **Acceptance Criterion** | AC-004 |
| **Execution Date** | 2026-09-22 |
| **Status** | Blocked |
| **Expected Result** | The document information view displays the assigned registration number. |
| **Observed Result** | Cannot execute: the document detail endpoint and frontend document view are not implemented yet. |
| **Evidence** | Blocker recorded; no document detail contract exists in this commit. |
| **Bug** | None; pending dependency US-004 |

### TC-005 - Concurrent Document Registration

| Field | Value |
|-------|-------|
| **Test Case** | TC-005 |
| **User Story** | US-001 |
| **Acceptance Criterion** | AC-003 |
| **Execution Date** | 2026-09-22 |
| **Status** | Passed |
| **Expected Result** | Concurrent registrations never receive duplicate numbers or gaps. |
| **Observed Result** | 10 threads made 5 calls each. All 50 numbers were unique and the sequence contained every value from 1 through 50. |
| **Evidence** | `backend/apps/documents/tests/test_filing_sequence.py::test_concurrent_callers_receive_unique_numbers` |
| **Bug** | None |

## Test Execution Output

```text
................                                                         [100%]
------------------- generated xml file: /tmp/us001-junit.xml -------------------
16 passed in 4.19s
```

## Detailed Automated Evidence

The focused pytest run collected 16 tests and reported all of them as passed:

| Automated Test | Result |
|----------------|--------|
| `TestFilingSequence::test_first_number_has_expected_format` | Passed |
| `TestFilingSequence::test_numbers_are_sequential_per_day` | Passed |
| `TestFilingSequence::test_sequence_is_independent_per_day` | Passed |
| `TestFilingSequence::test_service_generates_number_for_bogota_date` | Passed |
| `test_concurrent_callers_receive_unique_numbers` | Passed |
| `test_valid_filing_numbers[RAD-20260920-000001]` | Passed |
| `test_valid_filing_numbers[RAD-20261231-999999]` | Passed |
| `test_invalid_filing_numbers[]` | Passed |
| `test_invalid_filing_numbers[None]` | Passed |
| `test_invalid_filing_numbers[RAD-20260920-000000]` | Passed |
| `test_invalid_filing_numbers[RAD-20261340-000001]` | Passed |
| `test_invalid_filing_numbers[RAD-2026092-000001]` | Passed |
| `test_invalid_filing_numbers[RAD-20260920-00001]` | Passed |
| `test_invalid_filing_numbers[rad-20260920-000001]` | Passed |
| `test_invalid_filing_numbers[DOC-20260920-000001]` | Passed |
| `test_invalid_filing_numbers[RAD-20260920-000001 ]` | Passed |

The complete JUnit report was generated at `/tmp/us001-junit.xml` inside the test container.

## Test Coverage Mapping

| Acceptance Criterion | Covered By | Status |
|-----------------------|-------------|--------|
| AC-001 - Automatic Registration Number Generation | TC-001 and format validation tests | Passed |
| AC-002 - Registration Number Association | TC-002 | Blocked until US-004 |
| AC-003 - Registration Number Uniqueness | TC-003 and TC-005 | Passed |
| AC-004 - Registration Number Display | TC-004 | Blocked until document detail/API work |

## Execution Status Definitions

| Status | Meaning |
|--------|---------|
| **Passed** | The observed result matches the expected result. |
| **Failed** | The observed result does not match the expected result. |
| **Blocked** | The test cannot execute because a required product dependency is not implemented yet. |
| **Not Executed** | The test has not been run. |
