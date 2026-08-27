# Phase 2.4A — GHSA Source Contract and Workload Spike

_Date started: 2026-08-27_

_Status: COMPLETE_

## Purpose

Validate the authoritative GitHub Security Advisory source contract, temporal semantics, pagination, authentication/rate-limit requirements, advisory/package/range semantics, and realistic workload characteristics before OpsLens creates any GHSA AWS runtime.

This gate intentionally creates no AWS resources.

The invariant remains:

> **Agents reason. Code verifies evidence.**

Package/version applicability is not decided in Phase 2.4. GHSA source ranges and patch evidence are preserved as facts; evaluating whether an installed version is affected belongs to the deterministic Phase 3 Vulnerability Correlation Engine.

## Repository baseline

Phase 2.4A started from:

```text
branch:
phase-2-ghsa-source-contract

base main commit:
91068c4efa7da680918b1ab89c282c9af99712c4

base PR:
#29 — docs(phase-2): reconcile GHSA milestone baseline
```

Phase 2.4-0 was complete before this gate began.

## Selected authoritative runtime source

OpsLens selects the versioned GitHub Global Security Advisories REST API:

```text
GET https://api.github.com/advisories
GET https://api.github.com/advisories/{ghsa_id}
```

Pinned request contract:

```text
Accept: application/vnd.github+json
X-GitHub-Api-Version: 2026-03-10
User-Agent: OpsLens/<runtime>
```

Phase 2.4 scope is:

```text
type=reviewed
```

The public `github/advisory-database` repository remains a useful evidence and sample corpus, but it is not the production runtime contract. GitHub documents it as a mirror of the primary advisory database and warns that repository organization and internal `database_specific` fields may change.

Result:

```text
GHSA_SOURCE_INTERFACE_GATE=PASS
GHSA_API_VERSION_PIN_GATE=PASS
GHSA_RUNTIME_SOURCE_SELECTION_GATE=PASS
GHSA_REVIEWED_SCOPE_GATE=PASS
```

## Authentication and rate-limit decision

GitHub documents public REST limits of:

```text
unauthenticated: 60 requests/hour
authenticated:   5,000 requests/hour
```

The reviewed corpus observed during this spike implied at least 348 pages at `per_page=100` for an unfiltered full traversal. That makes unauthenticated bootstrap an unsuitable production mode.

The live authenticated probes confirmed:

```text
x-ratelimit-limit:    5000
x-ratelimit-resource: core
```

Decision:

```text
production GHSA retrieval must be authenticated
```

The exact credential mechanism remains deferred to the runtime/security design. Phase 2.4A does not create a PAT, GitHub App, Secrets Manager secret, IAM role, or other runtime credential resource.

Result:

```text
GHSA_AUTHENTICATED_RUNTIME_REQUIREMENT_GATE=PASS
GHSA_CREDENTIAL_MECHANISM_GATE=DEFERRED_TO_RUNTIME_SECURITY_DESIGN
```

## Pagination contract

The live source returned cursor pagination through an exact `Link` header:

```text
Link: <...after=<opaque-cursor>...>; rel="next"
```

OpsLens must:

```text
per_page=100
process pages serially by default
follow exact Link rel="next"
never synthesize or guess cursors
capture pagination evidence
use bounded page / byte defenses
```

The live probe traversed 13 pages in one bounded month with 1,278 unique GHSA IDs and no duplicate GHSA IDs across pages.

Result:

```text
GHSA_PAGINATION_DOCUMENTATION_GATE=PASS
GHSA_PAGINATION_LIVE_PROBE_GATE=PASS
```

## Advisory identity and aliases

Primary advisory identity:

```text
GHSA-xxxx-xxxx-xxxx
```

CVE identifiers are optional aliases rather than the GHSA primary key.

Live evidence observed reviewed advisories without CVE identifiers.

Therefore:

```text
ghsa_id = required
cve_id  = optional
```

The future model must not assume one GHSA maps to exactly one CVE.

Result:

```text
GHSA_IDENTITY_GATE=PASS
GHSA_CVE_ALIAS_OPTIONALITY_GATE=PASS
```

## Package and vulnerability-entry cardinality

The REST source exposes vulnerability entries containing package, vulnerable-range, patched-version, and related evidence.

Live observations proved one advisory can contain many vulnerability entries:

```text
initial reviewed page maximum: 12
recent modified-day maximum:    36
```

Therefore advisory identity and vulnerability/package evidence must remain one-to-many in the future Silver contract. A single flattened advisory row cannot preserve the source faithfully.

Package identity remains source-scoped as:

```text
ecosystem
+
package name
```

No cross-ecosystem package identity merging is performed in Phase 2.4.

## Affected ranges and fixed-version evidence

`vulnerable_version_range` is preserved as an exact source expression.

Phase 2.4 does not evaluate:

```text
installed_version ∈ vulnerable_version_range
```

That belongs to Phase 3 and requires deterministic ecosystem-specific version semantics.

`first_patched_version` is structured fixed-version evidence when present and remains nullable. The live probes observed missing patched-version values, so absence must remain unavailable source evidence rather than being inferred from prose.

Result:

```text
GHSA_AFFECTED_RANGE_BOUNDARY_GATE=PASS
GHSA_FIXED_VERSION_EVIDENCE_GATE=PASS
```

## Withdrawal semantics

A withdrawn advisory remains historical evidence.

The live reviewed collection page contained withdrawn advisories, confirming that withdrawal is a source state, not deletion.

Result:

```text
GHSA_WITHDRAWAL_SEMANTICS_GATE=PASS
```

## Bootstrap workload proof

The selected default bootstrap planning unit is one calendar month expressed as an exact closed `published` time range.

This is a planning default, not an assumption that every month will always fit a fixed page count. The actual logical synchronization identity is derived from the exact normalized start/end timestamps.

Two representative monthly windows were measured.

Recent month:

```text
published range: 2026-07-01T00:00:00Z .. 2026-07-31T23:59:59Z
pages:           13
items:           1278
unique GHSA:     1278
payload bytes:   8865112
HTTP time sum:   19.102 s
```

Historical month:

```text
published range: 2020-01-01T00:00:00Z .. 2020-01-31T23:59:59Z
pages:           1
items:           48
unique GHSA:     48
payload bytes:   221273
HTTP time sum:   0.768 s
```

The recent month remained bounded under the probe's 25-page safety cap while covering materially higher volume than the historical sample.

Decision:

```text
default bootstrap unit:
calendar-month published window

actual window identity:
exact normalized closed timestamps

future oversized window:
fail closed against runtime safety limits and subdivide deterministically
```

The exact production page/byte caps and subdivision algorithm belong to the Bronze/runtime contract. Phase 2.4A does not freeze those implementation constants.

Result:

```text
GHSA_BOOTSTRAP_SOURCE_GATE=PASS
GHSA_BOOTSTRAP_WINDOW_SIZE_GATE=PASS
```

## Incremental synchronization workload proof

A representative recent closed modified window was measured twice during the spike.

```text
modified range:
2026-08-26T00:00:00Z .. 2026-08-26T23:59:59Z

pages:         1
items:         36
unique GHSA:   36
payload bytes: 219694
HTTP time:     0.996 s
payload SHA256:
018aafe81dd5b3e681ef3566410ef1b94d0f2c129683688231aca50c2f409c9a
```

The payload SHA-256 matched the earlier probe of the same selected window while the source state remained unchanged during the observation period. This is evidence of repeatability for that observation, not a guarantee that GitHub will never revise the window's advisory content later.

The accepted high-level incremental contract is:

```text
closed modified-time range
        ↓
type=reviewed
sort=published
direction=asc
per_page=100
        ↓
follow exact Link rel="next"
        ↓
complete immutable source observation
```

The exact runtime overlap/delay policy and authoritative watermark mechanics remain explicit later-contract decisions. They must preserve replayability and must not treat source timestamps as content identity.

Result:

```text
GHSA_MODIFIED_WINDOW_LIVE_GATE=PASS
GHSA_LIVE_REQUEST_TIMING_GATE=PASS
GHSA_LIVE_WORKLOAD_GATE=PASS
```

## Source observation identity

Phase 2.4A accepts the architectural separation:

```text
sync_id
    deterministic logical request identity
    = source contract + API version + mode + exact normalized temporal range

attempt_id
    exact physical observation identity
    = ordered page evidence + exact response hashes/sizes + pagination evidence
```

A future advisory-version identity must be based on deterministic canonical advisory content rather than `updated_at` alone.

Exact manifest fields belong to the Bronze contract.

## Failure semantics carried forward

Transient source failures may be retried through a bounded policy:

- network timeout;
- temporary GitHub server failure;
- documented rate limiting.

Rate-limit behavior must honor `Retry-After` and `x-ratelimit-*` semantics.

Deterministic evidence failures fail closed, including candidate cases such as malformed required GHSA identity, malformed JSON, cursor loops/repeated pages, duplicate GHSA identity where the selected request contract requires uniqueness, and configured page/byte-cap overflow.

Additive unknown source fields remain preserved in Bronze and do not fail merely because GitHub evolves the response additively.

OpsLens will not deliberately trigger GitHub throttling as a failure test.

## Final Phase 2.4A gates

```text
GHSA_SOURCE_INTERFACE_GATE=PASS
GHSA_API_VERSION_PIN_GATE=PASS
GHSA_RUNTIME_SOURCE_SELECTION_GATE=PASS
GHSA_REVIEWED_SCOPE_GATE=PASS
GHSA_AUTHENTICATED_RUNTIME_REQUIREMENT_GATE=PASS
GHSA_CREDENTIAL_MECHANISM_GATE=DEFERRED_TO_RUNTIME_SECURITY_DESIGN
GHSA_PAGINATION_DOCUMENTATION_GATE=PASS
GHSA_PAGINATION_LIVE_PROBE_GATE=PASS
GHSA_BOOTSTRAP_SOURCE_GATE=PASS
GHSA_BOOTSTRAP_WINDOW_SIZE_GATE=PASS
GHSA_IDENTITY_GATE=PASS
GHSA_CVE_ALIAS_OPTIONALITY_GATE=PASS
GHSA_AFFECTED_RANGE_BOUNDARY_GATE=PASS
GHSA_FIXED_VERSION_EVIDENCE_GATE=PASS
GHSA_WITHDRAWAL_SEMANTICS_GATE=PASS
GHSA_MODIFIED_WINDOW_LIVE_GATE=PASS
GHSA_LIVE_REQUEST_TIMING_GATE=PASS
GHSA_LIVE_PAYLOAD_SEMANTICS_GATE=PASS
GHSA_LIVE_WORKLOAD_GATE=PASS
GHSA_2_4A_GATE=PASS
```

## Result

Phase 2.4A is complete.

ADR-0005 is accepted from this evidence.

No AWS resource, Terraform change, runtime IAM, secret, S3 object, Glue/Athena object, package-version matching logic, Bedrock capability, RAG path, MCP integration, A2A integration, or agent implementation was introduced by this gate.

The next Phase 2.4 gate must begin from the accepted source/synchronization contract and preserve the deterministic boundary that package-version applicability belongs to Phase 3.

## Official references reviewed

- GitHub REST API — Global security advisories: https://docs.github.com/en/rest/security-advisories/global-advisories
- GitHub REST API versioning: https://docs.github.com/en/rest/about-the-rest-api/api-versions
- GitHub REST API rate limits: https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api
- GitHub REST API pagination: https://docs.github.com/en/rest/using-the-rest-api/using-pagination-in-the-rest-api
- GitHub REST API best practices: https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api
- GitHub Advisory Database: https://github.com/advisories
- GitHub Advisory Database mirror: https://github.com/github/advisory-database
