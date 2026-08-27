# Phase 2.4C — GHSA Bronze Contract

_Date started: 2026-08-27_

_Status: IN PROGRESS_

## Purpose

Define deterministic GitHub Security Advisory Bronze request, response-page, cursor-pagination, physical observation, and persistence evidence contracts before any GHSA AWS runtime resource is created.

Phase 2.4A froze the GitHub source contract. Phase 2.4B froze exact advisory content-version Silver semantics. Phase 2.4C now owns the physical source observation boundary.

The invariant remains:

> **Agents reason. Code verifies evidence.**

No model participates in source-window identity, request construction, pagination continuation, GHSA identity validation, Bronze completion, object provenance, or credential handling.

## Dependency checkpoint

```text
Phase 2.4A — GHSA Source Contract:          COMPLETE
Phase 2.4B — GHSA Advisory/Silver Contract: COMPLETE
Phase 2.4C — GHSA Bronze:                   IN PROGRESS
```

Accepted upstream boundaries:

```text
runtime source: GitHub Global Security Advisories REST API
API version:    2026-03-10
scope:          reviewed only
bootstrap:      bounded published windows
incremental:    bounded modified windows
pagination:     exact Link rel=next continuation
Silver content identity:
                observed_advisory_version_id
```

Phase 2.4B explicitly established:

```text
observed_advisory_version_id != sync_id != attempt_id
```

Bronze must preserve the physical source evidence required to bind later Silver content back to the exact accepted source observation without changing content identity.

## Architecture for this gate

```text
bounded GhsaSyncWindow
        ↓
deterministic first request URL
        ↓
GitHub /advisories
        ↓
exact response bytes + Link header
        ↓
GhsaAdvisoryApiPageParser
        ↓
allowlisted exact rel=next URL
        ↓
GhsaAdvisoryPagination
        ↓
future attempt_id + Bronze page objects + COMPLETE manifest
```

No S3, Lambda, EventBridge, Terraform, IAM, or secret resource is introduced in the first increment.

## Increment 1 — logical window, URL allowlist, and complete cursor chain

The first implementation increment freezes only the deterministic source-navigation boundary.

### Logical synchronization identity

`GhsaSyncWindow` carries:

```text
mode:        published | modified
start_at:    inclusive UTC whole-second boundary
end_at:      inclusive UTC whole-second boundary
API version: 2026-03-10
type:        reviewed
sort:        published
direction:   asc
per_page:    100
```

One logical Bronze unit may span at most 31 days.

The `sync_id` hashes the versioned normalized query contract rather than runtime metadata:

```text
source contract
+ API version
+ mode
+ exact normalized start/end
+ reviewed scope
+ sort/direction
+ per_page
```

Runtime timestamps, Lambda request IDs, credentials, retries, and AWS metadata do not participate in `sync_id`.

### First request URL

The first URL is built deterministically for:

```text
https://api.github.com/advisories
```

with only the frozen query fields.

Authentication is intentionally not placed in the URL. Production authentication remains mandatory from ADR-0005 and will be injected through the outbound HTTP adapter as an Authorization header supplied by a credential port.

Tokens must never appear in:

```text
request URLs
Bronze objects
manifests
logs
exception messages
sync_id
attempt_id
```

The concrete AWS secret-storage mechanism remains a later runtime/security decision and will be evaluated before Terraform is introduced.

### Link header as untrusted navigation input

OpsLens follows GitHub's exact `rel="next"` continuation URL, but does not follow it blindly.

Every continuation URL must satisfy the outbound allowlist:

```text
scheme: https
host:   api.github.com
path:   /advisories
port:   default HTTPS or 443
userinfo: forbidden
fragment: forbidden
```

The URL must preserve exactly:

```text
type=reviewed
published=<same exact range>
  OR
modified=<same exact range>
sort=published
direction=asc
per_page=100
```

Only one opaque `after` or `before` cursor may be added. Unknown parameters, duplicate parameters, mixed published/modified filters, external hosts, alternate paths, and multiple cursors fail closed.

This is an SSRF/outbound-navigation boundary even though GitHub is the selected trusted source.

### Minimum page validation

Each exact response body must:

```text
be non-empty UTF-8 JSON
have a top-level array
remain <= 8 MiB
contain <= 100 advisories
contain unique GHSA IDs within the page
contain type=reviewed for every item
contain required published_at and updated_at UTC timestamps
respect the selected published/modified window
respect sort=published,direction=asc within the page
```

For a `published` window, every advisory must have `published_at` inside the exact closed range.

For a `modified` window, at least one of `published_at` or `updated_at` must be inside the exact closed range, matching the accepted GitHub modified-filter semantics.

The exact response bytes and SHA-256 are preserved in the validated page model.

### Complete pagination proof

A complete `GhsaAdvisoryPagination` must:

```text
start from the deterministic first request URL
follow each exact rel=next URL byte-for-byte as the next request URL
never repeat a request URL
never repeat a GHSA ID across pages
preserve non-decreasing published ordering across page boundaries
end only when the final page has no rel=next
```

Initial safety caps are frozen at:

```text
maximum page body:  8 MiB
maximum pages:      64
maximum total body: 64 MiB
```

The Phase 2.4A live workload measured a recent published month at 13 pages and about 8.9 MB, so these caps leave bounded headroom while still failing closed on unexpected source growth.

An oversized logical range is not permission for an unbounded traversal. A later Bronze increment will define deterministic subdivision/recovery behavior.

## Why NVD is reused by principle, not copied literally

NVD and GHSA share the architectural principle:

```text
logical source window identity
    !=
exact physical source observation identity
```

NVD pagination is numeric and declares `totalResults`; GHSA pagination is cursor-based and completion is evidenced by the absence of a valid `rel=next` continuation.

Therefore GHSA cannot reuse NVD's `startIndex/totalResults` completeness rules directly.

GHSA needs its own exact cursor-chain proof while preserving the same fail-closed evidence philosophy.

## Remaining Phase 2.4C work after Increment 1

After local validation of this first increment, the next Bronze contract increment will freeze:

```text
attempt_id
content-bound ordered page inventory
Bronze S3 key layout
page object metadata
COMPLETE manifest schema
manifest canonical serialization
S3 VersionId provenance
safe HTTP response metadata retention
failure and retry semantics
oversized-window deterministic subdivision
```

Only after those contracts are green should the phase evaluate and introduce the real AWS runtime, IAM, credential storage, scheduling, and observability resources.

## AWS / IAM / cost boundary

Current increment:

```text
AWS resources added:  none
IAM changes:          none
runtime cost added:   none
secret resources:     none
```

Future runtime must use authenticated GitHub retrieval, least-privilege AWS access, bounded HTTP behavior, immutable/versioned S3 evidence, and existing deterministic content-addressed Lambda deployment practices.

## Current gates

```text
GHSA_BRONZE_SYNC_WINDOW_GATE=PASS_PENDING_LOCAL_VALIDATION
GHSA_BRONZE_REQUEST_URL_ALLOWLIST_GATE=PASS_PENDING_LOCAL_VALIDATION
GHSA_BRONZE_PAGE_CONTRACT_GATE=PASS_PENDING_LOCAL_VALIDATION
GHSA_BRONZE_CURSOR_COMPLETION_GATE=PASS_PENDING_LOCAL_VALIDATION
GHSA_BRONZE_ATTEMPT_ID_GATE=PENDING
GHSA_BRONZE_KEY_LAYOUT_GATE=PENDING
GHSA_BRONZE_COMPLETE_MANIFEST_GATE=PENDING
GHSA_BRONZE_CREDENTIAL_RUNTIME_GATE=PENDING
GHSA_2_4C_GATE=IN_PROGRESS
```

## Next step

Run focused unit tests, Ruff, and strict Pyright for the new GHSA ingestion domain contract.

Do not add AWS resources until this source-navigation boundary is green.

## References

- `docs/adr/0005-ghsa-source-and-synchronization-strategy.md`
- `docs/adr/0006-ghsa-silver-content-versioning-and-physical-shape.md`
- `docs/labs/phase-2-ghsa-live-rest-probe.md`
- `docs/labs/phase-2-ghsa-advisory-silver-contract.md`
- GitHub REST API — Global security advisories: https://docs.github.com/en/rest/security-advisories/global-advisories
- GitHub REST API — Pagination: https://docs.github.com/en/rest/using-the-rest-api/using-pagination-in-the-rest-api
