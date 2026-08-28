# Phase 2.4C — GHSA Bronze Runtime Composition

_Date: 2026-08-28_

_Status: IN PROGRESS_

## Purpose

Compose the previously validated GHSA source, evidence, security, retry, subdivision, and persistence contracts into one bounded application service before introducing Lambda or Terraform.

The invariant remains:

> **Agents reason. Code verifies evidence.**

No model participates in source retrieval, cursor traversal, subdivision, persistence, completion, or replay decisions.

## Validated prerequisites

The local combined checkpoint before this increment is green:

```text
46 passed
Ruff: all checks passed
Pyright strict: 0 errors / 0 warnings / 0 informations
```

Therefore the following gates are promoted to PASS:

```text
GHSA_BRONZE_ATTEMPT_ID_GATE=PASS
GHSA_BRONZE_KEY_LAYOUT_GATE=PASS
GHSA_BRONZE_COMPLETE_MANIFEST_GATE=PASS
GHSA_BRONZE_AUTHENTICATED_HTTP_GATE=PASS
GHSA_BRONZE_RATE_LIMIT_GATE=PASS
GHSA_BRONZE_SECRET_PROVIDER_GATE=PASS
GHSA_BRONZE_S3_ADAPTER_GATE=PASS
GHSA_BRONZE_SUBDIVISION_GATE=PASS
```

## Runtime composition

`GhsaBronzeRuntimeService` now owns one deterministic application flow:

```text
GhsaSyncWindow
    ↓
deterministic initial GitHub URL
    ↓
authenticated GhsaPageSource
    ↓
exact response bytes + Link header
    ↓
GhsaAdvisoryApiPageParser
    ↓
exact rel=next traversal
    ↓
complete bounded GhsaAdvisoryPagination
    ↓
GhsaAttemptIdFactory
    ↓
deterministic attempt_id
    ↓
page keys
    ↓
GhsaBronzeRepository.create_page(...)
    ↓
exact page VersionIds
    ↓
GhsaCompleteManifestFactory
    ↓
canonical manifest bytes
    ↓
GhsaBronzeRepository.create_manifest(...)
    ↓
COMPLETE manifest VersionId
```

The runtime buffers the complete cursor chain before any attempt-keyed S3 write occurs. This is required because `attempt_id` depends on the complete ordered physical observation.

The already frozen aggregate caps remain:

```text
maximum pages per attempt:      64
maximum response bytes/attempt: 64 MiB
```

A single page remains limited to 8 MiB by the source/page contract.

## COMPLETE remains the authority boundary

Pages may exist without a COMPLETE manifest after a persistence failure. That is valid partial evidence, not a successful synchronization.

The service publishes the manifest only after every exact page write returned a non-empty S3 VersionId and the manifest factory verified the full page inventory.

Therefore:

```text
partial pages without manifest
    !=
complete GHSA Bronze attempt
```

No watermark or downstream Silver authority may advance from page objects alone.

## Replay behavior

The S3 adapter remains conditionally immutable with `If-None-Match: *`.

On replay, exact page and manifest keys may already exist. A 412 is accepted only after `HeadObject` proves the expected deterministic metadata, size, content type, and VersionId.

The runtime itself does not generate a new identity for a replay:

```text
same sync query
+ same exact page bytes
+ same cursor chain
    -> same attempt_id
    -> same deterministic object keys
```

## Deterministic subdivision

Aggregate attempt overflow occurs before persistence of the oversized parent attempt.

When the page or aggregate-byte cap is exceeded, the service asks `GhsaWindowSubdivisionPlanner` for two children:

```text
left  = [start, midpoint]
right = [midpoint + 1 second, end]
```

Children are processed left-to-right and receive independent `sync_id` values.

To prevent unbounded recursive expansion inside one runtime invocation, the composition introduces an explicit leaf-window budget:

```text
DEFAULT_MAX_LEAF_WINDOWS = 64
```

This is a runtime safety budget, not source or business semantics. Exceeding it fails closed with `GhsaSubdivisionBudgetExceededError`.

## Failure boundaries

The runtime does not convert these failures into successful completion:

```text
invalid GitHub page
invalid cursor chain
single-page size overflow
credential failure
rate-limit budget exhaustion
S3 evidence mismatch
missing VersionId
manifest persistence failure
unsplittable window
subdivision leaf-budget exhaustion
```

A failure after some page writes leaves no COMPLETE manifest for that attempt.

## Memory and Lambda implication

Because the complete physical observation must be known before `attempt_id` and page keys can be derived, one logical attempt may buffer up to the frozen 64 MiB source-body cap plus parser/model overhead.

The later Lambda sizing decision must therefore account for this evidence model rather than selecting the minimum memory tier by default.

No Lambda configuration is introduced in this increment.

## Current gates

```text
GHSA_BRONZE_SYNC_WINDOW_GATE=PASS
GHSA_BRONZE_REQUEST_URL_ALLOWLIST_GATE=PASS
GHSA_BRONZE_PAGE_CONTRACT_GATE=PASS
GHSA_BRONZE_CURSOR_COMPLETION_GATE=PASS
GHSA_BRONZE_ATTEMPT_ID_GATE=PASS
GHSA_BRONZE_KEY_LAYOUT_GATE=PASS
GHSA_BRONZE_COMPLETE_MANIFEST_GATE=PASS
GHSA_BRONZE_AUTHENTICATED_HTTP_GATE=PASS
GHSA_BRONZE_RATE_LIMIT_GATE=PASS
GHSA_BRONZE_SECRET_PROVIDER_GATE=PASS
GHSA_BRONZE_S3_ADAPTER_GATE=PASS
GHSA_BRONZE_SUBDIVISION_GATE=PASS

GHSA_BRONZE_RUNTIME_COMPOSITION_GATE=PASS_PENDING_LOCAL_VALIDATION
GHSA_BRONZE_TERRAFORM_GATE=PENDING
GHSA_2_4C_GATE=IN_PROGRESS
```

## Next step

Run the focused GHSA ingestion unit tests, Ruff, and strict Pyright for the composed runtime.

If green, freeze the Lambda/runtime input contract and then introduce the minimum AWS resources required for one real `dev` execution: Secrets Manager secret metadata, Lambda, exact IAM, artifact lifecycle, and invocation wiring. EventBridge scheduling remains separate until the manual runtime path is proven.
