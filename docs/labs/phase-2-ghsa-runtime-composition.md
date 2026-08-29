# Phase 2.4C — GHSA Bronze Runtime Composition

_Date: 2026-08-28_

_Status: COMPLETE_

## Purpose

Compose the previously validated GHSA source, evidence, security, retry, subdivision, and persistence contracts into one bounded application service and prove the composed runtime through the Phase 2.4C manual `dev` execution.

The invariant remains:

> **Agents reason. Code verifies evidence.**

No model participates in source retrieval, cursor traversal, subdivision, persistence, completion, or replay decisions.

## Validated prerequisites

The local combined checkpoint before this increment was green:

```text
46 passed
Ruff: all checks passed
Pyright strict: 0 errors / 0 warnings / 0 informations
```

The later final pre-apply checkpoint increased the focused GHSA validation to:

```text
61 passed
Ruff: All checks passed
Pyright strict: 0 errors / 0 warnings / 0 informations
```

## Runtime composition

`GhsaBronzeRuntimeService` owns one deterministic application flow:

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

The frozen aggregate caps remain:

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

The S3 adapter is conditionally immutable with `If-None-Match: *`.

On replay, exact page and manifest keys may already exist. A 412 is accepted only after `HeadObject` proves the expected deterministic metadata, size, content type, and VersionId.

The runtime itself does not generate a new identity for a replay:

```text
same sync query
+ same exact page bytes
+ same cursor chain
    -> same attempt_id
    -> same deterministic object keys
```

The live manual proof confirmed this behavior. The second invocation of the same bounded source window returned the same `sync_id`, `attempt_id`, page VersionId, manifest VersionId, totals, and object keys. S3 version listing showed exactly one physical version of each deterministic object and no delete markers.

## Deterministic subdivision

Aggregate attempt overflow occurs before persistence of the oversized parent attempt.

When the page or aggregate-byte cap is exceeded, the service asks `GhsaWindowSubdivisionPlanner` for two children:

```text
left  = [start, midpoint]
right = [midpoint + 1 second, end]
```

Children are processed left-to-right and receive independent `sync_id` values.

To prevent unbounded recursive expansion inside one runtime invocation, the composition uses an explicit leaf-window budget:

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

The deployed Lambda therefore uses 1024 MiB memory and a 900-second timeout for the manual proof path. The application-level rate-limit wait budget remains much smaller at 120 seconds per retry.

## Live composition proof

The manual published window `2026-08-27T00:00:00Z` through `2026-08-28T00:00:00Z` completed with:

```text
root_sync_id=1670a1e4730ba3e5a8214b7278d68b43fd8c929a069bae27099abd370cf9193e
attempt_id=e013864e669cc3b4f92766a94e9f487960bd4b3bf40247d523b8415a0d8aaa40
leaf_count=1
page_count=1
total_items=10
total_bytes=48899
manifest_version_id=IHt7S5Uvj21ABxWfPAPsXbnQhQW3ErRH
page_version_id=k1i1ppmalEBvDN9Dzrby5ocbdB.M8y2s
```

The exact page SHA-256 and size matched the COMPLETE manifest, and the replay created no duplicate S3 versions.

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
GHSA_BRONZE_RUNTIME_COMPOSITION_GATE=PASS
GHSA_BRONZE_LAMBDA_INVOCATION_CONTRACT_GATE=PASS
GHSA_BRONZE_TERRAFORM_GATE=PASS
GHSA_BRONZE_MANUAL_DEV_RUNTIME_GATE=PASS
GHSA_2_4C_GATE=PASS
```

## Next step

Proceed to Phase 2.4D — GHSA Silver Runtime. Preserve COMPLETE-manifest authority and exact Bronze provenance when projecting advisory content into Silver.
