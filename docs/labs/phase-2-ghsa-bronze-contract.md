# Phase 2.4C — GHSA Bronze Contract

_Date started: 2026-08-27_

_Status: IN PROGRESS_

## Purpose

Define deterministic GitHub Security Advisory Bronze request, response-page, cursor-pagination, physical observation, and persistence evidence contracts before any GHSA AWS runtime resource is created.

Phase 2.4A froze the GitHub source contract. Phase 2.4B froze exact advisory content-version Silver semantics. Phase 2.4C owns the physical source observation boundary.

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

Bronze preserves the physical source evidence required to bind later Silver content back to one exact accepted source observation without redefining advisory content identity.

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
GhsaAttemptIdFactory
        ↓
content-bound attempt_id
        ↓
deterministic Bronze page keys
        ↓
versioned persistence results
        ↓
GhsaCompleteManifest
```

No S3, Lambda, EventBridge, Terraform, IAM, or secret resource is introduced by the contract increments.

## Increment 1 — logical window, URL allowlist, and complete cursor chain

The first implementation increment froze the deterministic source-navigation boundary.

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

### Link header as untrusted navigation input

OpsLens follows GitHub's exact `rel="next"` continuation URL, but every continuation remains inside the outbound allowlist:

```text
scheme: https
host:   api.github.com
path:   /advisories
port:   default HTTPS or 443
userinfo: forbidden
fragment: forbidden
```

The URL must preserve exactly the selected synchronization filter, `type=reviewed`, `sort=published`, `direction=asc`, and `per_page=100`. Only one opaque `after` or `before` cursor may be added.

This is an SSRF/outbound-navigation boundary even though GitHub is the selected trusted source.

### Minimum page and pagination validation

Each exact response body must be non-empty UTF-8 JSON, top-level array, at most 8 MiB, at most 100 advisories, reviewed-only, within the selected source window, unique by GHSA within the page, and sorted by `published_at` ascending.

A complete pagination must start from the deterministic initial URL, follow each exact `rel=next` URL, avoid repeated request URLs and GHSA IDs, preserve cross-page published ordering, and end only when the final page has no `rel=next`.

Safety caps:

```text
maximum page body:  8 MiB
maximum pages:      64
maximum total body: 64 MiB
```

Local validation for Increment 1:

```text
16 passed
Ruff: all checks passed
Pyright strict: 0 errors / 0 warnings / 0 informations
```

## Increment 2 — physical attempt identity and COMPLETE persistence evidence

The second increment introduces no AWS resources. It freezes the deterministic shape that a future runtime must satisfy after it retrieves and persists a complete page sequence.

### Physical attempt identity

`GhsaAttemptIdFactory` binds the exact ordered observation:

```text
attempt_version
sync_id
page_count
total_items
total_bytes
ordered pages[]:
  request_url
  next_url
  sha256
  size_bytes
  item_count
```

The `attempt_id` is SHA-256 over canonical JSON for that document.

Consequences:

```text
same logical sync + same exact pages + same cursor chain
    -> same attempt_id

same logical sync + changed response bytes
    -> different attempt_id

same logical sync + changed cursor navigation evidence
    -> different attempt_id
```

`attempt_id` is not a runtime invocation ID and contains no timestamp, credential, Lambda request ID, S3 VersionId, retry counter, or AWS metadata.

### Bronze key layout

The frozen contract layout is:

```text
bronze/ghsa/advisories/
  mode=<published|modified>/
    sync_id=<logical-query-sha256>/
      attempt_id=<physical-observation-sha256>/
        page=<000001...>/response.json
        manifest.json
```

The opaque GitHub cursor is intentionally not used as an S3 key component. Cursor evidence remains inside the attempt identity and manifest.

This preserves the same architectural principle already proven in NVD:

```text
logical synchronization identity
    !=
exact physical observation identity
```

while adapting the page coordinate to cursor-based GitHub pagination.

### Versioned persistence proof

`GhsaBronzeWriteResult` requires both:

```text
exact object key
exact S3 VersionId
```

The COMPLETE manifest factory refuses completion when:

```text
page write count != validated page count
persisted page key != deterministic Bronze key
pagination belongs to another sync_id
page inventory is incomplete
```

This means a future S3 adapter cannot report only a successful `PutObject`; it must return the exact VersionId created for the exact key.

### COMPLETE manifest

One manifest describes one exact physical attempt and preserves:

```text
source:            github-ghsa
source_interface:  global-security-advisories-rest
api_version:       2026-03-10
advisory_type:     reviewed
mode
sync_id
attempt_id
closed window start/end
page_count
total_items
total_bytes
```

Each stored page records:

```text
page_ordinal
key
version_id
size_bytes
sha256
item_count
request_url
next_url
first_ghsa_id
last_ghsa_id
```

The manifest serializer uses deterministic canonical JSON ordering and a trailing newline.

Authorization headers and tokens are not represented in the manifest, keys, `sync_id`, or `attempt_id`.

### Empty windows

A valid zero-result synchronization remains evidence:

```text
one exact response page containing []
no rel=next
total_items = 0
COMPLETE manifest with one persisted page
```

An empty logical window is therefore not confused with a failed or missing ingestion attempt.

## Provenance boundary with Silver

Phase 2.4B freezes:

```text
observed_advisory_version_id
    = exact canonical advisory content identity
```

Phase 2.4C now freezes:

```text
sync_id
    = logical source-query identity

attempt_id
    = exact complete physical page/cursor observation identity
```

Later Bronze-to-Silver verification must be able to prove:

```text
Silver advisory content
    came from
exact page bytes
    at exact S3 VersionId
    inside exact COMPLETE attempt manifest
```

Repeated physical observations of identical advisory content may therefore have different `attempt_id` values while still producing the same `observed_advisory_version_id`.

## Remaining Phase 2.4C work

After local validation of Increment 2, the remaining Bronze/runtime gate must decide and prove:

```text
safe authenticated GitHub HTTP adapter
credential source and rotation ownership
bounded retry / Retry-After behavior
safe response metadata retention
S3 versioned page + manifest adapters
failure/replay semantics
oversized-window deterministic subdivision
runtime composition
Lambda artifact build
least-privilege IAM
Terraform
real dev execution evidence
```

No watermark or Silver authority may advance from a partial attempt.

## AWS / IAM / cost boundary

Current contract work:

```text
AWS resources added:  none
IAM changes:          none
runtime cost added:   none
secret resources:     none
```

The future runtime must use authenticated GitHub retrieval, least-privilege AWS access, bounded HTTP behavior, immutable/versioned S3 evidence, and the existing deterministic content-addressed Lambda deployment lifecycle.

## Current gates

```text
GHSA_BRONZE_SYNC_WINDOW_GATE=PASS
GHSA_BRONZE_REQUEST_URL_ALLOWLIST_GATE=PASS
GHSA_BRONZE_PAGE_CONTRACT_GATE=PASS
GHSA_BRONZE_CURSOR_COMPLETION_GATE=PASS
GHSA_BRONZE_ATTEMPT_ID_GATE=PASS_PENDING_LOCAL_VALIDATION
GHSA_BRONZE_KEY_LAYOUT_GATE=PASS_PENDING_LOCAL_VALIDATION
GHSA_BRONZE_COMPLETE_MANIFEST_GATE=PASS_PENDING_LOCAL_VALIDATION
GHSA_BRONZE_CREDENTIAL_RUNTIME_GATE=PENDING
GHSA_BRONZE_RUNTIME_GATE=PENDING
GHSA_2_4C_GATE=IN_PROGRESS
```

## Next step

Run focused unit tests, Ruff, and strict Pyright for the new attempt/key/manifest increment.

Do not introduce AWS resources until this physical evidence contract is green.

## References

- `docs/adr/0005-ghsa-source-and-synchronization-strategy.md`
- `docs/adr/0006-ghsa-silver-content-versioning-and-physical-shape.md`
- `docs/labs/phase-2-ghsa-live-rest-probe.md`
- `docs/labs/phase-2-ghsa-advisory-silver-contract.md`
- GitHub REST API — Global security advisories: https://docs.github.com/en/rest/security-advisories/global-advisories
- GitHub REST API — Pagination: https://docs.github.com/en/rest/using-the-rest-api/using-pagination-in-the-rest-api
