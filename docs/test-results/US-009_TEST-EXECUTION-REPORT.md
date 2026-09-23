# US-009 - Test Execution Report

## Execution Summary

| Test Case | Acceptance Criteria | Status | Evidence |
|-----------|---------------------|--------|----------|
| TC-048 - Process readable uploaded document | AC-052, AC-053 | Passed | Extraction, classification, and processing-state assertions |
| TC-049 - Complete processing successfully | AC-054 | Passed | Successful task result and persisted output |
| TC-050 - Handle processing failure | AC-055 | Passed | Retry exhaustion, failed status, and audit error |
| TC-051 - Preserve source document after failure | AC-056 | Passed | Source bytes unchanged after failure |
| TC-052 - Associate result with source document | AC-057 | Passed | Extracted data and classification linked to same document |
| TC-053 - Expose processing status | AC-058 | Passed | Document detail API exposes status and extracted data |

## Environment

| Field | Value |
|-------|-------|
| Execution date | 2026-09-23 |
| Branch | `docs/sprint1-test-cases` |
| Backend | Django 5.2.17 / Python 3.12 |
| Database | PostgreSQL 16 Docker service |
| Storage | MinIO-compatible test storage |
| Test runner | pytest |
| Command | `docker compose exec -T backend pytest apps/documents/tests/test_tasks.py apps/documents/tests/test_documents_api.py -q` |

## Execution Output

Focused validation after the test additions:

```text
.................                                                        [100%]
17 passed in 11.67s
```

Full US-009-related execution:

```text
...............................................                          [100%]
47 passed in 18.00s
```

## Acceptance-Criteria Evidence

### AC-052 and AC-053 - Process and Extract Document Information

**Result:** Passed.

The Celery task reads the source file from storage, passes its bytes to the extraction service, stores the extracted payload, and applies classification when the result is sufficiently confident and resolvable.

### AC-054 - Confirm Successful Processing

**Result:** Passed.

Successful processing returns a task result with the document ID and `PROCESADO` status, while the extracted information and classification are persisted for the next stage.

### AC-055 - Handle Processing Failure

**Result:** Passed.

Transient extraction failures are retried. After the maximum retry count, the document is marked `FALLIDO` and an audit event records the error and retry count.

### AC-056 - Preserve Source Document

**Result:** Passed.

The source file bytes remain identical after a definitive processing failure.

### AC-057 - Associate Processed Information with Source Document

**Result:** Passed.

Extracted metadata, confidence, classification, dates, and the resolved digital record are stored on the corresponding `Document` record.

### AC-058 - Make Processing Status Available

**Result:** Passed.

The document detail API exposes the processing status, extracted data, and confidence score. The task also exposes the intermediate `PROCESANDO` state while extraction is running.

## Additional Coverage

The suite also verifies low-confidence and unavailable-AI flows route to human review, transient failures retry successfully, unknown document IDs are discarded safely, and the task has a stable Celery name and retry configuration.

## Defects and Gaps

No defects were found in the executed US-009 tests.
