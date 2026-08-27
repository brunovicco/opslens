# Phase 2.4A — GHSA Live REST Probe Evidence

_Date: 2026-08-27_

_Status: COMPLETE_

## Purpose

Record bounded live GitHub Global Security Advisories REST evidence for Phase 2.4A.

The probes used authenticated, version-pinned GitHub REST requests and created no AWS resources.

> **Agents reason. Code verifies evidence.**

## Request contract

```text
GET https://api.github.com/advisories
Accept: application/vnd.github+json
Authorization: Bearer <redacted>
X-GitHub-Api-Version: 2026-03-10
User-Agent: OpsLens-Phase-2.4A
```

All source requests in this lab were serial and bounded.

## Probe A — reviewed collection page

Request shape:

```text
type=reviewed
sort=published
direction=asc
per_page=100
```

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

Observed semantics:

```text
CVE missing:                         3
withdrawn advisories:                3
vulnerability entries:             171
first_patched_version missing:       9
max vulnerabilities per advisory:  12
```

This proved live cursor pagination, authenticated primary-rate headers, cache metadata, CVE optionality, withdrawal presence, one-to-many advisory/package evidence, and nullable patched-version evidence.

## Probe B — closed modified day

Request range:

```text
modified=2026-08-26T00:00:00+00:00..2026-08-26T23:59:59+00:00
```

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

Exact payload evidence:

```text
bytes:   219694
sha256:  018aafe81dd5b3e681ef3566410ef1b94d0f2c129683688231aca50c2f409c9a
items:   36
unique:  36 GHSA IDs
```

Observed semantics:

```text
CVE missing:                         3
withdrawn advisories:                0
vulnerability entries:             154
first_patched_version missing:       8
max vulnerabilities per advisory:  36
```

The one-day modified window completed in one page under the observed conditions.

## Probe C — recent published calendar month

Request range:

```text
published=2026-07-01T00:00:00+00:00..2026-07-31T23:59:59+00:00
type=reviewed
sort=published
direction=asc
per_page=100
```

The probe followed each exact GitHub `rel="next"` continuation URL serially.

Observed page evidence:

```text
page=1  items=100 bytes=564128 seconds=1.683 rate_remaining=4982 has_next=True
page=2  items=100 bytes=569493 seconds=0.970 rate_remaining=4981 has_next=True
page=3  items=100 bytes=508930 seconds=1.423 rate_remaining=4980 has_next=True
page=4  items=100 bytes=817591 seconds=1.386 rate_remaining=4979 has_next=True
page=5  items=100 bytes=751427 seconds=1.388 rate_remaining=4978 has_next=True
page=6  items=100 bytes=683282 seconds=1.353 rate_remaining=4977 has_next=True
page=7  items=100 bytes=903629 seconds=1.219 rate_remaining=4976 has_next=True
page=8  items=100 bytes=860209 seconds=1.506 rate_remaining=4975 has_next=True
page=9  items=100 bytes=521333 seconds=1.145 rate_remaining=4974 has_next=True
page=10 items=100 bytes=563039 seconds=1.405 rate_remaining=4973 has_next=True
page=11 items=100 bytes=797007 seconds=1.604 rate_remaining=4972 has_next=True
page=12 items=100 bytes=771608 seconds=2.866 rate_remaining=4971 has_next=True
page=13 items=78  bytes=553436 seconds=1.155 rate_remaining=4970 has_next=False
```

Summary:

```text
pages:       13
items:       1278
unique GHSA: 1278
bytes:       8865112
HTTP time:   19.102 s
rate limit:  5000
remaining:   4970
```

The reported 19.102 seconds is the sum of HTTP request durations measured by the probe. It does not include the deliberate one-second inter-page sleeps.

Every page had a distinct exact payload SHA-256 recorded by the probe. The traversal completed without duplicate GHSA IDs across pages and stayed below the lab's `MAX_PAGES=25` fail-closed safety cap.

Result:

```text
GHSA_PUBLISHED_RECENT_MONTH_GATE=PASS
GHSA_MULTI_PAGE_CURSOR_TRAVERSAL_GATE=PASS
GHSA_MULTI_PAGE_UNIQUENESS_GATE=PASS
```

## Probe D — historical published calendar month

Request range:

```text
published=2020-01-01T00:00:00+00:00..2020-01-31T23:59:59+00:00
type=reviewed
sort=published
direction=asc
per_page=100
```

Observed page:

```text
page=1
items=48
bytes=221273
seconds=0.768
sha256=a02373a47abeb54d63721bd5d33b834186f07d207e96a75d65bf3b8b75ab27a9
etag="22ec541017f8ea7275acff3ffe76082e82794d1b0841c5e547bc45e910e63391"
last_modified=Tue, 21 Jul 2026 15:02:50 GMT
rate_remaining=4969
has_next=False
```

Summary:

```text
pages:       1
items:       48
unique GHSA: 48
bytes:       221273
HTTP time:   0.768 s
```

Result:

```text
GHSA_PUBLISHED_HISTORICAL_MONTH_GATE=PASS
```

## Probe E — repeated modified day with timing

The same closed modified range used in Probe B was requested again.

Observed result:

```text
pages:       1
items:       36
unique GHSA: 36
bytes:       219694
HTTP time:   0.996 s
sha256:      018aafe81dd5b3e681ef3566410ef1b94d0f2c129683688231aca50c2f409c9a
rate limit:  5000
remaining:   4968
```

The exact payload SHA-256 matched the earlier observation of that same closed modified window during the spike.

This proves repeatability for the observed source state, not immutability of GitHub advisory content for all future time.

Result:

```text
GHSA_MODIFIED_WINDOW_LIVE_GATE=PASS
GHSA_LIVE_REQUEST_TIMING_GATE=PASS
```

## Workload decision

The two `published` samples provide materially different source volumes:

```text
2026-07: 1278 advisories / 13 pages / 8.87 MB / 19.102 s HTTP time
2020-01:   48 advisories /  1 page  / 0.22 MB /  0.768 s HTTP time
```

A calendar month is therefore accepted as the default bootstrap planning unit.

It is not treated as an unlimited runtime guarantee. The production source contract must support exact arbitrary closed time ranges and fail closed when configured page/byte defenses are exceeded so an oversized month can be subdivided deterministically.

The exact production caps and split algorithm remain part of the Bronze/runtime design rather than this workload spike.

Result:

```text
GHSA_BOOTSTRAP_WINDOW_SIZE_GATE=PASS
GHSA_LIVE_WORKLOAD_GATE=PASS
```

## Schema consequences

The combined live evidence proves:

```text
ghsa_id: required
cve_id: optional
withdrawn_at: source state, not deletion
advisory -> vulnerability/package entries: one-to-many
first_patched_version: nullable
vulnerable_version_range: source evidence, not Phase 2 applicability logic
```

The future Silver model must preserve advisory identity separately from vulnerability/package entries.

## Observation identity consequence

The source contract must preserve:

```text
logical request identity
    !=
exact physical source observation identity
```

Future Bronze evidence must bind ordered page positions, exact response hashes/sizes, pagination links, retrieval timestamps, and relevant response metadata.

A logical `sync_id` must be derived from the normalized source contract and exact temporal range, while an `attempt_id` must bind the exact physical page observation.

## Final live gates

```text
GHSA_LIVE_HTTP_SUCCESS_GATE=PASS
GHSA_LIVE_CONTENT_TYPE_GATE=PASS
GHSA_LIVE_PAGE_SIZE_GATE=PASS
GHSA_LIVE_UNIQUE_GHSA_GATE=PASS
GHSA_PAGINATION_LIVE_PROBE_GATE=PASS
GHSA_RATE_LIMIT_HEADER_GATE=PASS
GHSA_CACHE_METADATA_GATE=PASS
GHSA_MODIFIED_WINDOW_LIVE_GATE=PASS
GHSA_LIVE_PAYLOAD_SEMANTICS_GATE=PASS
GHSA_LIVE_REQUEST_TIMING_GATE=PASS
GHSA_PUBLISHED_RECENT_MONTH_GATE=PASS
GHSA_PUBLISHED_HISTORICAL_MONTH_GATE=PASS
GHSA_MULTI_PAGE_CURSOR_TRAVERSAL_GATE=PASS
GHSA_MULTI_PAGE_UNIQUENESS_GATE=PASS
GHSA_BOOTSTRAP_WINDOW_SIZE_GATE=PASS
GHSA_LIVE_WORKLOAD_GATE=PASS
```

## Result

The bounded live workload evidence required by Phase 2.4A is complete.

ADR-0005 may be accepted and Phase 2.4A may close.
