# ADR-0005: GitHub Security Advisory Source and Synchronization Strategy

- Status: Proposed
- Date: 2026-08-27

## Context

OpsLens Phase 2.4 introduces GitHub Security Advisories (GHSA) after the deterministic FIRST EPSS, CISA KEV, and NVD/CVE paths.

The Phase 2.4 requirement is to add structured advisory/package evidence without prematurely implementing package-version applicability.

The source must support, at minimum:

- stable advisory identity;
- CVE aliases when present;
- package ecosystem and package identity;
- vulnerable version-range evidence;
- structured first-patched-version evidence when available;
- publication/update/withdrawal state;
- deterministic replay and historical observations;
- bounded retrieval and recoverable pagination.

The project invariant remains:

> **Agents reason. Code verifies evidence.**

No model may infer advisory identity, CVE equivalence, package applicability, vulnerable-version membership, patched-version values, synchronization completion, or authority state.

## Evidence from Phase 2.4A so far

GitHub documents a versioned Global Security Advisories REST endpoint:

```text
GET /advisories
GET /advisories/{ghsa_id}
```

The selected API contract pins:

```text
Accept: application/vnd.github+json
X-GitHub-Api-Version: 2026-03-10
```

The list endpoint supports reviewed/unreviewed/malware advisory classes, date/date-time filtering over `published`, `updated`, and `modified`, cursor pagination, sorting, and a maximum `per_page` of 100.

GitHub's public Advisory Database reported 34,792 reviewed advisories on 2026-08-27. At 100 records per page, an unfiltered bootstrap requires at least 348 list requests.

GitHub documents a primary limit of 60 requests/hour for unauthenticated public access and 5,000 requests/hour for authenticated user/token requests. The source endpoint itself does not require advisory-specific fine-grained token permissions.

Real reviewed advisory evidence inspected from GitHub's public advisory-database mirror proved that:

- a GHSA may have a CVE alias;
- a GHSA may have no CVE alias;
- an advisory may be withdrawn while remaining valid historical source evidence;
- an affected package carries ecosystem/name and structured affected-range evidence;
- a structured fixed/first-patched version may be available;
- fixed-version evidence is not universal and must remain nullable.

The mirror repository is useful for source inspection, but GitHub documents it as a mirror of its primary advisory database and warns that repository organization and internal `database_specific` fields may change. It is therefore not selected as the production runtime interface.

## Proposed decision

### Authoritative runtime interface

Use the versioned GitHub REST Global Security Advisories API as the OpsLens GHSA runtime source.

```text
source:
GET https://api.github.com/advisories

API version:
2026-03-10

advisory class:
reviewed
```

Do not use a Git clone of `github/advisory-database` as the runtime ingestion contract.

The mirror may continue to be used as public evidence for tests, examples, and source-semantic research when read as data only.

### Advisory class

Ingest only:

```text
type=reviewed
```

Do not union `unreviewed` or `malware` into the same Phase 2.4 dataset.

`unreviewed` advisories substantially overlap NVD-derived evidence already present in OpsLens. Malware advisories represent a different security-intelligence category rather than standard vulnerability advisories.

### Authentication

Production GHSA retrieval must be authenticated.

The current full-bootstrap page count is already too large to treat the unauthenticated 60 requests/hour budget as a reasonable bounded production mode.

The exact credential mechanism is intentionally deferred until the runtime/security design evaluates:

- least privilege;
- rotation;
- storage;
- ownership;
- operational recovery.

Phase 2.4A creates no secret resource.

### Pagination

Use:

```text
per_page=100
serial requests
exact Link rel="next" continuation URL
```

Do not synthesize or guess pagination cursors.

Rate-limit responses must honor GitHub's documented `Retry-After` and `x-ratelimit-*` semantics with bounded retry behavior.

### Bootstrap

Use the same REST source for bootstrap and ongoing updates.

Candidate bootstrap algorithm:

```text
establish T0
 ↓
reviewed advisories by bounded published-time windows
 ↓
complete each window independently
 ↓
catch up modified advisories T0 -> T1
 ↓
ongoing modified windows
```

The initial workload-spike candidate is calendar-month historical windows. The exact window size remains open until the live REST workload probe measures representative page counts and response sizes.

### Incremental synchronization

Use closed `modified` date-time windows because GitHub defines `modified` as advisories that were published or updated within the requested range.

Candidate query shape:

```text
type=reviewed
modified=<closed ISO-8601 range>
sort=published
direction=asc
per_page=100
```

Do not use an unbounded `sort=updated` traversal as the synchronization authority because mutable ordering can move records between pages while a traversal is in progress.

The exact safety-overlap and watermark policy remain open until the live probe validates real date-time filtering and cursor behavior.

### Advisory identity

Use GHSA ID as the source advisory identity.

```text
GHSA-xxxx-xxxx-xxxx
```

CVE identifiers are aliases, not the GHSA primary key.

The model must support zero-or-more aliases and must not assume every GHSA maps to exactly one CVE.

### Package identity

Preserve source package identity as:

```text
ecosystem
+
package name
```

No cross-ecosystem package identity merging is introduced in Phase 2.4.

### Vulnerable ranges

Preserve `vulnerable_version_range` as the exact structured source expression.

Do not evaluate installed-version membership during ingestion or normalization.

That operation belongs to Phase 3 and requires deterministic ecosystem-specific version semantics.

### Fixed versions

Preserve `first_patched_version` as structured source evidence when present.

The value is nullable.

Do not extract an authoritative fixed version from advisory prose when the structured field is absent.

### Withdrawal

Preserve `withdrawn_at` as a source state.

A withdrawn advisory is historical evidence and must not be deleted or treated as if the GHSA never existed.

### Observation identity

Separate logical synchronization identity from exact physical source observation identity.

Candidate model:

```text
sync_id
    source contract + API version + mode + normalized temporal range

attempt_id
    exact ordered page bytes / hashes / sizes + pagination evidence
```

Do not use `updated_at` as the sole content identity for an advisory version.

The deterministic advisory-content identity and exact Bronze manifest schema will be finalized in later Phase 2.4 contract gates.

## Why this ADR remains Proposed

The authoritative interface, reviewed scope, authentication requirement, package/range boundary, fixed-version semantics, and high-level synchronization model are supported by current official documentation and real public advisory examples.

However, Phase 2.4A is a workload spike as well as a documentation review.

Before this ADR becomes Accepted, OpsLens must perform a bounded live request against `GET /advisories` and record:

- exact response bytes and timing;
- `Link` cursor behavior;
- rate-limit headers;
- response/header cache metadata when present;
- item count and uniqueness;
- representative `published` and `modified` range behavior;
- representative window page counts/sizes.

No AWS runtime should be implemented from this proposed ADR before that live evidence gate passes.

## Alternatives considered

### Advisory-database Git repository as the production source

Not selected.

The repository is a useful open evidence mirror but is not the versioned service contract. GitHub explicitly warns that repository organization and internal database-specific values may change.

### Include unreviewed advisories

Not selected for Phase 2.4.

They are automatically published from NVD and would create substantial overlap with the NVD path already implemented by OpsLens without adding the curated package-advisory boundary that motivates GHSA.

### Include malware advisories

Not selected for Phase 2.4.

Malware is a distinct threat-intelligence category and should not be silently merged with standard vulnerability advisories.

### Unauthenticated production ingestion

Not selected.

The currently observed reviewed-advisory cardinality implies at least 348 unfiltered pages, while GitHub allows only 60 unauthenticated public REST requests per hour.

### One unbounded full-database poll

Not selected.

Bounded temporal windows provide clearer completion, replay, recovery, cost, and evidence semantics.

### Evaluate version ranges during GHSA normalization

Rejected.

Source normalization must preserve affected-range evidence without deciding applicability. Ecosystem-specific package/version matching is Phase 3 deterministic correlation work.

### Derive fixed versions from prose

Rejected.

A structured `first_patched_version` is stronger source evidence. Free-text extraction would introduce an interpretation policy and is not authoritative normalization.

## Consequences

### Positive

- uses a versioned GitHub-supported API contract;
- focuses Phase 2.4 on curated package advisory evidence;
- avoids duplicating the existing NVD source class unnecessarily;
- preserves GHSA identity independently from optional CVE aliases;
- preserves source version-range expressions without premature interpretation;
- preserves structured first-patched-version evidence;
- retains withdrawn advisory history;
- provides bounded synchronization/recovery units;
- keeps source observation identity separate from logical synchronization state;
- avoids creating AWS or secret resources before the workload evidence is complete.

### Trade-offs

- authenticated production retrieval introduces a future credential lifecycle requirement;
- bootstrap requires multiple bounded temporal windows;
- current source changes can cause multiple historical observations of one GHSA;
- consumers cannot treat every GHSA as CVE-backed;
- range applicability remains unavailable until Phase 3;
- the exact bootstrap window size and incremental safety overlap remain unresolved until the live probe completes.

## Proposed operational rule

Until this ADR is accepted or superseded:

```text
runtime source:
GitHub Global Security Advisories REST API

API version:
2026-03-10

scope:
reviewed only

authentication:
required for production; mechanism deferred

bootstrap:
bounded published-time windows + modified catch-up

incremental:
closed modified-time windows

pagination:
per_page=100 + exact Link continuation

identity:
GHSA primary; CVE aliases optional

ranges:
preserve exact source expression

fixed version:
preserve structured first_patched_version when present

withdrawal:
preserve as historical source state

package-version applicability:
Phase 3 only
```

## References

- https://docs.github.com/en/rest/security-advisories/global-advisories
- https://docs.github.com/en/rest/about-the-rest-api/api-versions
- https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api
- https://docs.github.com/en/rest/using-the-rest-api/using-pagination-in-the-rest-api
- https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api
- https://github.com/advisories
- https://github.com/github/advisory-database
