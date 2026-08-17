# Phase 2 — CISA KEV Asynchronous Failure Recovery

## Objective

Validate the complete asynchronous failure-recovery path for the CISA KEV ingestion Lambda.

## Architecture under test

```text
asynchronous invocation
        |
        v
KEV Ingestion Lambda
        |
        v
CISA source request
        |
        +--> failure
        |
        v
Lambda asynchronous retry queue
        |
        +--> retry
        +--> retry
        |
        v
RetriesExhausted
        |
        v
SQS OnFailure
opslens-dev-kev-ingestion-failures
```

Configuration:

```text
maximum event age: 3600 seconds
maximum retries:   2
OnFailure:         SQS Standard
```

## Failure injection

The CISA source URL was temporarily changed through Terraform to a nonexistent same-origin path. No runtime test backdoor was added.

An asynchronous Lambda invocation returned `StatusCode = 202`.

## Observed Lambda executions

```text
attempt 1: 2026-08-17T04:40:52.645Z
attempt 2: 2026-08-17T04:42:00.589Z
attempt 3: 2026-08-17T04:43:56.216Z
```

Approximate retry gaps:

```text
attempt 1 -> 2: 67.944 seconds
attempt 2 -> 3: 115.627 seconds
```

All attempts reported the same Lambda request identifier:

```text
3607a578-4038-4cab-beee-5bff0811f844
```

Each attempt observed `HTTP 404`, `KevSourceUnavailableError`, and failure metrics.

## Lambda platform evidence

```text
attempt 1: billed 1683 ms, max memory 98 MB
attempt 2: billed  477 ms, max memory 113 MB
attempt 3: billed  646 ms, max memory 125 MB
```

Total failure-lab compute: `1.403 GB-s`.

A key operational lesson is that Lambda platform reports can show platform-level success while the application invocation contains an unhandled error. Application success must not be inferred from platform report status alone.

## SQS OnFailure evidence

Observed destination record:

```text
condition:              RetriesExhausted
approximateInvokeCount: 3
functionError:          Unhandled
errorType:              KevSourceUnavailableError
messageId:              ad04aa6c-e690-4d47-bfb8-475972a361f8
```

The record preserved the original invocation payload, Lambda request context, error information, retry count, and correlation data.

## Recovery

The canonical CISA source URL was restored through Terraform.

A healthy invocation after restoration returned:

```text
status:       already_exists
snapshot:     2026-08-17
catalog:      2026.08.14
record_count: 1665
```

The SQS failure record was consumed and deleted as controlled lab cleanup. A later long poll returned no visible message.

## Infrastructure convergence

```text
No changes. Your infrastructure matches the configuration.
```

## Result

```text
SOURCE_FAILURE_OBSERVED=PASS
LAMBDA_ASYNC_RETRY_GATE=PASS
RETRY_BOUND_GATE=PASS
SQS_ONFAILURE_DELIVERY_GATE=PASS
FAILURE_CONTEXT_GATE=PASS
RESTORE_GATE=PASS
TERRAFORM_CONVERGENCE_GATE=PASS
```
