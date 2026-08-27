# Phase 2.4A — GHSA Live REST Probe Evidence

_Date: 2026-08-27_

## Purpose

Record the first bounded live GitHub Global Security Advisories REST evidence for Phase 2.4A.

This evidence was collected against the authenticated versioned REST contract selected by the source-contract spike. It creates no AWS resources and does not change runtime behavior.

The invariant remains:

> **Agents reason. Code verifies evidence.**

## Request contract

The probe used the Phase 2.4A candidate contract:

```text
GET https://api.github.com/advisories
Accept: application/vnd.github+json
Authorization: Bearer <redacted>
X-GitHub-Api-Version: 2026-03-10
User-Agent: OpsLens-Phase-2.4A
```

Two bounded observations were captured:

```text
A. reviewed collection page
   type=reviewed
   sort=published
   direction=asc
   per_page=100

B. recent closed modified window
   type=reviewed
   modified=2026-08-26T00:00:00+00:00..2026-08-26T23:59:59+00:00
   sort=published
   direction=asc
   per_page=100
```

## Observation A — reviewed collection page

Observed headers:

```text
HTTP/2 200
content-type: application/json; charset=utf-8
content-length: 231154
etag: "d76c52f4b0e1828988fca36d62d1940d78aabaccdb41ff447c1eaa50eeba1d2e"
last-modified: Tue, 03 Mar 2026 20:03:29 GMT
link: https://api.github.com/advisories?type=reviewed&sort=published&direction=asc&per_page=100&after=Y3Vyc29yOnYyOpK0MjAxNy0xMC0yNFQxODozMzozN1py; rel="next"
x-ratelimit-limit: 5000
x-ratelimit-remaining: 4990
x-ratelimit-reset: 1787837773
x-ratelimit-used: 10
x-ratelimit-resource: core
```

Exact payload evidence:

```text
bytes:   231154
sha256:  4fabf15a6fb156b20fd6657c723d66cce2b7d113213b42910054e13fa6aa327a
items:   100
unique:  100 GHSA IDs
```

Observed advisory semantics inside this page:

```text
CVE missing:                         3
withdrawn advisories:                3
vulnerability entries:             171
first_patched_version missing:       9
max vulnerabilities per advisory:  12
```

Result:

```text
GHSA_LIVE_HTTP_SUCCESS_GATE=PASS
GHSA_LIVE_CONTENT_TYPE_GATE=PASS
GHSA_LIVE_PAGE_SIZE_GATE=PASS
GHSA_LIVE_UNIQUE_GHSA_GATE=PASS
GHSA_PAGINATION_LIVE_PROBE_GATE=PASS
GHSA_RATE_LIMIT_HEADER_GATE=PASS
GHSA_CACHE_METADATA_GATE=PASS
```

The live response proves that the endpoint currently returns cursor pagination through an exact `Link` continuation URL. OpsLens must follow the returned URL as source evidence and must not synthesize the `after` cursor independently.

The authenticated request also proves the expected primary rate-limit budget in the live environment:

```text
x-ratelimit-limit: 5000
x-ratelimit-resource: core
```

## Observation B — closed modified window

Observed headers:

```text
HTTP/2 200
content-type: application/json; charset=utf-8
content-length: 219694
etag: "4f000804d96d52292b01d4c0193c0bde4b2ead512907d8e7d3bcb756cc9f8c36"
last-modified: Wed, 26 Aug 2026 20:48:48 GMT
x-ratelimit-limit: 5000
x-ratelimit-remaining: 4989
x-ratelimit-reset: 1787837773
x-ratelimit-used: 11
x-ratelimit-resource: core
```

No `Link` header was present in the captured selected headers for this request.

Exact payload evidence:

```text
bytes:   219694
sha256:  018aafe81dd5b3e681ef3566410ef1b94d0f2c129683688231aca50c2f409c9a
items:   36
unique:  36 GHSA IDs
```

Observed advisory semantics inside this window:

```text
CVE missing:                         3
withdrawn advisories:                0
vulnerability entries:             154
first_patched_version missing:       8
max vulnerabilities per advisory:  36
```

Because the response contained only 36 items with `per_page=100` and no continuation link was observed, this one-day modified window completed in one page under the measured conditions.

Result:

```text
GHSA_MODIFIED_WINDOW_LIVE_GATE=PASS
GHSA_MODIFIED_WINDOW_SINGLE_PAGE_OBSERVED=PASS
```

## Schema consequences proven by the live payloads

The live REST observations materially strengthen the Phase 2.4 contract.

### CVE remains optional

Both probes contained reviewed advisories without a CVE identifier.

Therefore:

```text
ghsa_id = required source advisory identity
cve_id  = optional alias evidence
```

A schema that requires one CVE per GHSA is invalid.

### Advisory-to-vulnerability is one-to-many

Observed maximum vulnerability-entry counts were:

```text
reviewed collection page: 12
recent modified window:   36
```

Therefore one advisory row cannot safely flatten package/range/fix evidence without loss or duplication.

The Silver contract should preserve advisory identity separately from one-or-more vulnerability/package entries.

### Patched version remains nullable

The live probes observed missing `first_patched_version` values:

```text
9 of 171 vulnerability entries
8 of 154 vulnerability entries
```

Absence must remain `null` / unavailable source evidence. OpsLens must not infer a fixed version from prose.

### Withdrawal remains historical state

The reviewed collection page included three withdrawn advisories.

Withdrawal therefore remains a normal source-state value that must be preserved rather than interpreted as deletion.

## Pagination and observation identity consequence

The first live response confirms this source boundary:

```text
logical request contract
    !=
exact physical source observation
```

The physical observation must bind at least:

```text
request contract
ordered page position
exact response bytes
response SHA-256
response size
ETag / Last-Modified when present
exact Link continuation evidence
retrieval timestamp
```

A future GHSA `attempt_id` may deterministically bind the ordered page hashes/sizes and pagination evidence, while the logical `sync_id` remains derived from the normalized source contract and temporal range.

## What this probe closes

The evidence closes the previously pending live pagination and recent modified-window portions of Phase 2.4A:

```text
GHSA_PAGINATION_LIVE_PROBE_GATE=PASS
GHSA_MODIFIED_WINDOW_LIVE_GATE=PASS
GHSA_LIVE_PAYLOAD_SEMANTICS_GATE=PASS
GHSA_RATE_LIMIT_HEADER_GATE=PASS
GHSA_CACHE_METADATA_GATE=PASS
```

## Remaining Phase 2.4A evidence

The Phase 2.4A exit criteria are not yet fully satisfied because two empirical items requested by the source-contract lab were not included in this probe output:

1. request duration was not measured;
2. no bounded historical `published=<range>` bootstrap window was measured.

The unfiltered reviewed page proves pagination mechanics, but it does not establish the workload size of the proposed bounded published-time bootstrap unit.

Therefore these gates remain open:

```text
GHSA_LIVE_REQUEST_TIMING_GATE=PENDING
GHSA_BOOTSTRAP_WINDOW_SIZE_GATE=PENDING_LIVE_PROBE
GHSA_LIVE_WORKLOAD_GATE=IN_PROGRESS
GHSA_2_4A_GATE=IN_PROGRESS
```

ADR-0005 remains **Proposed** until these remaining measurements are recorded or explicitly deferred.

No GHSA AWS runtime should be created before the Phase 2.4A exit gate closes.
