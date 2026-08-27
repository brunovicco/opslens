# ADR-0005: GitHub Security Advisory Source and Synchronization Strategy

- Status: Accepted
- Date: 2026-08-27

## Context

OpsLens Phase 2.4 introduces GitHub Security Advisories (GHSA) after the deterministic FIRST EPSS, CISA KEV, and NVD/CVE paths.

The requirement is to add curated advisory/package evidence without prematurely implementing installed package-version applicability.

The source contract must support:

- stable advisory identity;
- optional CVE aliases;
- package ecosystem and package identity;
- vulnerable version-range evidence;
- structured first-patched-version evidence when available;
- publication/update/withdrawal state;
- bounded pagination and replay;
- historical source observations.

The project invariant remains:

> **Agents reason. Code verifies evidence.**

No model may infer advisory identity, CVE equivalence, package applicability, vulnerable-version membership, patched-version values, synchronization completion, or authority state.

## Evidence from Phase 2.4A

GitHub provides a versioned Global Security Advisories REST interface:

```text
GET /advisories
GET /advisories/{ghsa_id}
```

OpsLens pins:

```text
Accept: application/vnd.github+json
X-GitHub-Api-Version: 2026-03-10
```

Phase 2.4 uses:

```text
type=reviewed
```

The public `github/advisory-database` repository remains useful for evidence and sample inspection, but GitHub documents it as a mirror of its primary advisory database and warns that repository organization and internal `database_specific` values may change.

The live authenticated probes confirmed:

```text
x-ratelimit-limit:    5000
x-ratelimit-resource: core
```

They also confirmed exact cursor pagination through `Link: ...; rel="next"`.

Representative live workload evidence:

```text
recent published month — 2026-07
pages:       13
items:       1278
unique GHSA: 1278
bytes:       8865112
HTTP time:   19.102 s

historical published month — 2020-01
pages:       1
items:       48
unique GHSA: 48
bytes:       221273
HTTP time:   0.768 s

recent modified day — 2026-08-26
pages:       1
items:       36
unique GHSA: 36
bytes:       219694
HTTP time:   0.996 s
```

Live payloads also proved:

- reviewed GHSAs can omit CVE identifiers;
- withdrawn advisories remain present as source evidence;
- one advisory can contain many vulnerability/package entries;
- `first_patched_version` is not universal and must remain nullable.

## Decision

### Authoritative runtime interface

Use the GitHub Global Security Advisories REST API as the OpsLens GHSA runtime source.

```text
source:
GET https://api.github.com/advisories

API version:
2026-03-10

advisory class:
reviewed
```

Do not use a Git clone of `github/advisory-database` as the production ingestion contract.

### Authentication

Production GHSA retrieval must be authenticated.

The reviewed corpus size implies hundreds of pages for a full traversal, while GitHub's unauthenticated REST budget is too small for a reasonable production bootstrap.

The exact credential mechanism is deferred to the runtime/security design and must be evaluated for least privilege, rotation, storage, ownership, and recovery.

### Pagination

Use:

```text
per_page=100
serial requests by default
exact Link rel="next" continuation URL
```

Do not synthesize or guess pagination cursors.

Runtime handling must honor documented rate-limit behavior including `Retry-After` and `x-ratelimit-*` headers.

### Bootstrap

Use the same versioned REST source for bootstrap and ongoing updates.

Default bootstrap planning unit:

```text
one calendar-month published window
```

The actual logical identity is the exact normalized closed start/end range, not the word `month`.

Accepted bootstrap shape:

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

A calendar month is a default planning unit, not an unlimited size guarantee. Runtime page/byte caps must fail closed, and an oversized month must be subdividable deterministically into smaller exact ranges.

The exact production caps and subdivision algorithm belong to the Bronze/runtime contract.

### Incremental synchronization

Use bounded closed `modified` time ranges.

Accepted request shape:

```text
type=reviewed
modified=<closed ISO-8601 range>
sort=published
direction=asc
per_page=100
```

Do not use one unbounded mutable traversal as synchronization authority.

The exact safety-overlap/delay policy and authoritative watermark mechanics remain later runtime-contract decisions. They must preserve replayability and must not treat source timestamps as content identity.

### Advisory identity

Use GHSA ID as the source advisory identity:

```text
GHSA-xxxx-xxxx-xxxx
```

CVE identifiers are optional aliases rather than the GHSA primary key.

The model must not assume every GHSA maps to exactly one CVE.

### Package identity and cardinality

Preserve source package identity as:

```text
ecosystem
+
package name
```

One advisory can carry multiple vulnerability/package entries. Advisory-level facts and vulnerability/package facts must therefore remain separate in the future Silver model.

No cross-ecosystem package identity merging is introduced in Phase 2.4.

### Vulnerable ranges

Preserve `vulnerable_version_range` as the exact structured source expression.

Do not evaluate installed-version membership during ingestion or normalization.

That operation belongs to Phase 3 and requires deterministic ecosystem-specific version semantics.

### Fixed versions

Preserve `first_patched_version` as structured source evidence when present.

The value is nullable.

Do not derive an authoritative fixed version from advisory prose when the structured field is absent.

### Withdrawal

Preserve `withdrawn_at` as a source state.

A withdrawn advisory remains historical source evidence and must not be deleted or treated as if the GHSA never existed.

### Observation identity

Separate logical synchronization identity from exact physical source observation identity.

```text
sync_id
    source contract + API version + mode + exact normalized temporal range

attempt_id
    exact ordered page evidence + response hashes/sizes + pagination evidence
```

Do not use `updated_at` as the sole content identity for an advisory version.

The exact Bronze manifest and deterministic canonical advisory-version identity are later Phase 2.4 contract decisions.

## Alternatives considered

### Advisory-database Git repository as production source

Not selected. It is a useful public mirror, but not the selected versioned service contract.

### Include unreviewed advisories

Not selected for Phase 2.4. They substantially overlap NVD-derived evidence already present in OpsLens.

### Include malware advisories

Not selected for Phase 2.4. Malware is a distinct threat-intelligence category and should not be silently merged into the standard advisory dataset.

### Unauthenticated production ingestion

Not selected. The measured and observed corpus size makes the 60 requests/hour unauthenticated budget unsuitable for bounded production bootstrap.

### One unbounded full-database poll

Not selected. Bounded temporal ranges provide clearer completion, replay, recovery, and evidence semantics.

### Evaluate vulnerable ranges during GHSA normalization

Rejected. Source normalization preserves evidence; package/version applicability is deterministic Phase 3 work.

### Derive fixed versions from prose

Rejected. Structured `first_patched_version` is stronger source evidence, while prose extraction would introduce an interpretation policy.

## Consequences

### Positive

- uses a versioned GitHub-supported API contract;
- focuses Phase 2.4 on curated reviewed advisory/package evidence;
- avoids unnecessarily duplicating the NVD source class;
- preserves GHSA identity independently from optional CVE aliases;
- preserves one-to-many package/range/fix evidence;
- preserves vulnerable-range expressions without premature interpretation;
- preserves nullable structured first-patched-version evidence;
- retains withdrawn advisory history;
- provides bounded bootstrap and incremental synchronization units;
- separates logical synchronization identity from exact physical source observation identity;
- avoids creating AWS resources before the source workload is understood.

### Trade-offs

- authenticated production retrieval introduces a credential lifecycle requirement;
- bootstrap spans multiple bounded temporal windows;
- advisory updates can create multiple historical observations for one GHSA;
- consumers cannot assume every GHSA is CVE-backed;
- package/version applicability remains unavailable until Phase 3;
- exact runtime page/byte caps, window subdivision, overlap, and watermark mechanics still require later deterministic contracts.

## Operational rule

Until superseded by another ADR:

```text
runtime source:
GitHub Global Security Advisories REST API

API version:
2026-03-10

scope:
reviewed only

authentication:
required for production; mechanism decided later

bootstrap default:
calendar-month published windows

bootstrap identity:
exact normalized closed start/end range

incremental:
bounded closed modified-time ranges

pagination:
per_page=100 + exact Link continuation

identity:
GHSA primary; CVE aliases optional

package evidence:
one-to-many vulnerability/package entries

ranges:
preserve exact source expression

fixed version:
preserve structured first_patched_version when present

withdrawal:
preserve as historical source state

source observation:
logical sync_id != exact physical attempt_id

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
