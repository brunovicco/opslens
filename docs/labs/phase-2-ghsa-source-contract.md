# Phase 2.4A — GHSA Source Contract and Workload Spike

_Date started: 2026-08-27_

_Status: IN PROGRESS_

## Purpose

Validate the authoritative GitHub Security Advisory source contract, temporal semantics, pagination, authentication/rate-limit requirements, advisory/package/range semantics, and realistic workload characteristics before OpsLens creates any GHSA AWS runtime.

This gate intentionally creates no AWS resources.

The invariant remains:

> **Agents reason. Code verifies evidence.**

Package/version applicability is not decided in Phase 2.4. GHSA source ranges and patch evidence are preserved as facts; evaluating whether an installed version is affected belongs to the deterministic Phase 3 Vulnerability Correlation Engine.

## Repository baseline

Phase 2.4A starts from:

```text
branch:
phase-2-ghsa-source-contract

base main commit:
91068c4efa7da680918b1ab89c282c9af99712c4

base PR:
#29 — docs(phase-2): reconcile GHSA milestone baseline
```

Phase 2.4-0 is complete.

## Scope

This spike validates:

```text
GitHub Global Security Advisories REST API
        ↓
versioned public source contract
        ↓
reviewed-advisory scope
        ↓
pagination + rate-limit model
        ↓
real advisory semantics
        ↓
bootstrap / incremental synchronization model
        ↓
source identity + replay model
        ↓
Phase 2.4 Bronze / Silver design inputs
```

Out of scope:

- Lambda implementation;
- Terraform changes;
- EventBridge Scheduler;
- IAM or secret resources;
- S3 Bronze objects;
- Silver Parquet;
- Glue or Athena;
- package/version applicability evaluation;
- repository dependency discovery;
- Bedrock;
- RAG;
- MCP;
- A2A;
- agents.

## Official source interface

The selected runtime source interface is the GitHub REST API endpoint:

```text
GET https://api.github.com/advisories
```

The contract pins the current GitHub REST API version explicitly:

```text
Accept: application/vnd.github+json
X-GitHub-Api-Version: 2026-03-10
User-Agent: OpsLens/<runtime>
```

The API supports exact GHSA retrieval through:

```text
GET https://api.github.com/advisories/{ghsa_id}
```

The list endpoint supports, among other filters:

```text
type
published
updated
modified
ecosystem
severity
is_withdrawn
before
after
direction
per_page
sort
```

`per_page` is bounded to a maximum of 100.

`modified` means advisories that were either published or updated within the requested date/date-time expression. GitHub search date syntax supports ISO-8601 dates and optional time components, as well as comparison and range expressions.

Result so far:

```text
GHSA_SOURCE_INTERFACE_GATE=PASS
GHSA_API_VERSION_PIN_GATE=PASS
```

## Why the advisory-database repository is not the runtime interface

GitHub also publishes `github/advisory-database`, where advisories are represented as OSV JSON files.

That repository is valuable as public evidence and as a corpus for inspecting real advisory semantics, but it is not selected as the OpsLens runtime source contract because GitHub documents that:

- the repository is a mirror of its primary advisory database;
- repository organization may change incompatibly;
- GitHub-specific `database_specific` values are primarily internal and may change without notice;
- consuming systems should not rely on those internal values for vulnerability processing.

OpsLens therefore separates:

```text
runtime source contract
    -> versioned GitHub REST API

public sample/evidence corpus
    -> github/advisory-database mirror
```

Result:

```text
GHSA_RUNTIME_SOURCE_SELECTION_GATE=PASS
```

## Advisory scope

GitHub divides global advisories into:

```text
reviewed
unreviewed
malware
```

Phase 2.4 selects:

```text
type=reviewed
```

Reasons:

- reviewed advisories are curated by GitHub and mapped to supported package ecosystems;
- unreviewed advisories are automatically published from NVD and would substantially overlap the NVD source OpsLens already ingests;
- malware advisories represent a different problem category and are not standard vulnerability advisories.

Phase 2.4 does not silently union these three source classes.

Result:

```text
GHSA_REVIEWED_SCOPE_GATE=PASS
```

## Authentication and rate-limit evidence

The global advisory endpoint can read public resources without authentication, and GitHub documents that fine-grained tokens require no endpoint-specific permissions.

Current REST primary limits documented by GitHub are:

```text
unauthenticated public requests: 60 requests/hour
authenticated user/token:        5,000 requests/hour
GitHub App installation:         at least 5,000 requests/hour
```

Secondary limits also apply. GitHub recommends authenticated requests, serial request behavior, pagination through the returned `Link` header, and bounded handling of `403` / `429` responses using `Retry-After` and rate-limit headers.

On 2026-08-27, the public GitHub Advisory Database UI reported:

```text
GitHub-reviewed advisories: 34,792
```

At `per_page=100`, an unfiltered reviewed bootstrap therefore requires at least:

```text
ceil(34,792 / 100) = 348 list pages
```

At the unauthenticated primary budget of 60 requests/hour, the theoretical primary-rate floor alone is:

```text
348 / 60 = 5.8 hours
```

This is not a runtime estimate; it excludes response latency, safety pacing, retries, secondary limits, and any additional verification calls. It is enough to reject unauthenticated full bootstrap as the intended production mode.

Decision:

```text
production GHSA retrieval must be authenticated
```

The exact credential mechanism — for example a fine-grained token versus GitHub App installation authentication — is intentionally deferred until the AWS runtime/security gate evaluates least privilege, rotation, secret storage, and operational ownership.

No secret resource is created in Phase 2.4A.

Result:

```text
GHSA_AUTHENTICATED_RUNTIME_REQUIREMENT_GATE=PASS
GHSA_CREDENTIAL_MECHANISM_GATE=DEFERRED_TO_RUNTIME_SECURITY_DESIGN
```

## Pagination contract

GitHub REST pagination exposes continuation URLs in the HTTP `Link` header. OpsLens must follow the exact returned `rel="next"` URL rather than construct cursor values independently.

Initial production contract:

```text
per_page=100
requests processed serially
follow exact Link rel="next"
no speculative concurrency
bounded page count / response-size defenses
rate-limit headers captured as operational evidence
```

GitHub documents that pagination parameters can vary by endpoint, including cursor-based `before` / `after` forms. The GHSA endpoint exposes those cursors directly.

A live REST response-header probe is still required before this gate closes to record the exact cursor/link behavior observed from `/advisories`.

Result:

```text
GHSA_PAGINATION_DOCUMENTATION_GATE=PASS
GHSA_PAGINATION_LIVE_PROBE_GATE=PENDING
```

## Sorting and mutable pagination

GitHub recommends stable pagination and warns generally against workflows where updated data can move between pages while a paginated traversal is in progress.

OpsLens therefore does not choose an unbounded `sort=updated` traversal as its synchronization primitive.

The synchronization model is based on bounded temporal filters and a deterministic sort inside each closed range.

Candidate request shape:

```text
type=reviewed
modified=<closed ISO-8601 range>
sort=published
direction=asc
per_page=100
```

The exact range granularity and any safety overlap remain subject to the live workload probe before the strategy is accepted.

## Bootstrap strategy

The selected candidate bootstrap shape uses the same authoritative REST source as ongoing synchronization.

It does not switch to Git clone for bulk population.

Candidate flow:

```text
T0
 ↓
historical reviewed advisories
published-time windows
 ↓
complete each bounded window
 ↓
catch up modifications T0 -> T1
 ↓
ongoing closed modified windows
```

Historical windows prevent one giant unbounded traversal and provide natural replay/recovery units.

Calendar-month windows are the initial spike candidate, not yet a frozen production constant. The live probe must measure page counts and response sizes for representative quiet and busy intervals before window size is accepted.

Result:

```text
GHSA_BOOTSTRAP_SOURCE_GATE=PASS
GHSA_BOOTSTRAP_WINDOW_SIZE_GATE=PENDING_LIVE_PROBE
```

## Incremental synchronization semantics

The REST API exposes:

```text
published_at
updated_at
```

and a `modified` query filter that selects advisories published or updated within a requested range.

Candidate incremental model:

```text
closed modified-time window
    ↓
reviewed advisories only
    ↓
complete pagination
    ↓
immutable Bronze observation
    ↓
deterministic Silver
    ↓
authoritative synchronization boundary
```

A source timestamp is metadata, not a content identity. If the same GHSA is observed with changed content, OpsLens must preserve the new observation rather than overwrite the previous one.

The exact safety-overlap policy and watermark boundary are intentionally not frozen until the live REST probe validates date-time filtering and page stability with real responses.

## Advisory identity and aliases

The primary logical advisory identity is:

```text
GHSA-xxxx-xxxx-xxxx
```

CVE identity is an alias/equivalence relation, not the primary GHSA identity.

Real public evidence proves that a reviewed GHSA may have:

```text
one CVE alias
zero CVE aliases
```

Examples inspected from the official GitHub advisory-database mirror:

```text
GHSA-fm7p-gw32-828p
aliases: CVE-2026-54705

GHSA-pmwx-rm49-xv39
aliases: []
```

The Phase 2.4 contract must therefore support zero-or-more identifiers and must not assume `GHSA -> exactly one CVE`.

Result:

```text
GHSA_IDENTITY_GATE=PASS
GHSA_CVE_ALIAS_OPTIONALITY_GATE=PASS
```

## Package and ecosystem semantics

The REST response exposes advisory vulnerability entries containing:

```text
package.ecosystem
package.name
vulnerable_version_range
first_patched_version
vulnerable_functions
```

One advisory may contain multiple vulnerability entries and therefore potentially multiple affected package identities.

Phase 2.4 preserves source package identity as:

```text
ecosystem
+
package name
```

No cross-ecosystem normalization or installed-version matching is performed here.

## Affected ranges

`vulnerable_version_range` is structured source evidence but remains an opaque source expression in Phase 2.

Phase 2.4 must preserve the exact expression and provenance.

It must not evaluate whether:

```text
installed_version ∈ vulnerable_version_range
```

That evaluation belongs to Phase 3 and requires ecosystem-specific deterministic version semantics.

Result:

```text
GHSA_AFFECTED_RANGE_BOUNDARY_GATE=PASS
```

## Fixed-version evidence

`first_patched_version` is structured GitHub REST evidence when present.

It is nullable.

Real OSV mirror samples demonstrate advisories with explicit fixed events, including:

```text
GHSA-fm7p-gw32-828p
package: npm / mathlive
fixed:   0.110.0

GHSA-pmwx-rm49-xv39
package: RubyGems / activerecord-tenanted
fixed:   0.7.0
```

Phase 2.4 may normalize a structured patched-version value while preserving its source vulnerability-entry provenance.

Absence of `first_patched_version` means structured fixed-version evidence is unavailable from that REST observation. OpsLens must not derive an authoritative fixed version from advisory prose.

Result:

```text
GHSA_FIXED_VERSION_EVIDENCE_GATE=PASS
```

## Withdrawal semantics

A withdrawn advisory remains source evidence and must not be deleted from historical state.

Real reviewed evidence:

```text
GHSA-9jx5-6pgf-crrp
CVE-2023-25399
withdrawn: 2024-05-14T20:15:44Z
```

The deterministic interpretation is:

```text
advisory exists in persisted source evidence: true
withdrawn state: true
```

Withdrawal is therefore a temporal source state, not absence.

Result:

```text
GHSA_WITHDRAWAL_SEMANTICS_GATE=PASS
```

## Source observation identity

The NVD implementation already proves a useful distinction:

```text
logical synchronization identity
!=
exact physical source observation identity
```

GHSA should preserve the same architectural distinction without copying NVD-specific fields blindly.

Candidate GHSA identities:

```text
sync_id
    deterministic identity of source type + API version + synchronization mode
    + normalized closed temporal range + stable request contract

attempt_id
    deterministic identity bound to exact ordered response pages
    + page SHA-256 values + sizes + pagination order
```

Individual advisory observation identity will be based on deterministic canonical advisory content in the Silver-contract gate, not solely on `updated_at`.

The exact manifest shape belongs to the Bronze contract after Phase 2.4A closes.

## Failure semantics to carry forward

Transient source failures may be retried within a bounded policy:

- network timeout;
- temporary GitHub server failure;
- documented rate limiting.

Rate-limit behavior must honor:

```text
Retry-After
x-ratelimit-remaining
x-ratelimit-reset
```

Deterministic evidence failures fail closed, including candidate cases such as:

- malformed required GHSA identifier;
- malformed JSON;
- duplicate GHSA identifier within one complete source observation where duplication violates the selected request contract;
- pagination cursor loop or repeated page;
- response beyond the configured byte cap;
- malformed known vulnerability/package structure.

Additive unknown fields remain preserved in Bronze and do not fail merely because the source schema evolves additively.

OpsLens will not deliberately trigger public GitHub throttling as a failure test.

## Live REST workload probe — required to close Phase 2.4A

The current research establishes the API contract and source semantics, but Phase 2.4A remains open until a real `/advisories` response is measured from a normal network environment.

The probe must record at minimum:

```text
HTTP status
content type
exact response bytes
ETag / Last-Modified when present
Link header
x-ratelimit-* headers
page item count
unique GHSA count
request duration
```

It must also inspect representative returned advisories for:

```text
CVE present / absent
withdrawn_at present / absent
number of vulnerabilities per advisory
first_patched_version present / absent
multiple package vulnerability entries
vulnerable_version_range values
```

Representative temporal requests must validate:

```text
published=<bounded historical range>
modified=<closed recent range>
per_page=100
sort=published
direction=asc
```

Only a small, respectful number of requests is required. The probe must not crawl all 34k+ advisories merely to close this contract gate.

## Current Phase 2.4A gates

```text
GHSA_SOURCE_INTERFACE_GATE=PASS
GHSA_API_VERSION_PIN_GATE=PASS
GHSA_RUNTIME_SOURCE_SELECTION_GATE=PASS
GHSA_REVIEWED_SCOPE_GATE=PASS
GHSA_AUTHENTICATED_RUNTIME_REQUIREMENT_GATE=PASS
GHSA_CREDENTIAL_MECHANISM_GATE=DEFERRED_TO_RUNTIME_SECURITY_DESIGN
GHSA_PAGINATION_DOCUMENTATION_GATE=PASS
GHSA_PAGINATION_LIVE_PROBE_GATE=PENDING
GHSA_BOOTSTRAP_SOURCE_GATE=PASS
GHSA_BOOTSTRAP_WINDOW_SIZE_GATE=PENDING_LIVE_PROBE
GHSA_IDENTITY_GATE=PASS
GHSA_CVE_ALIAS_OPTIONALITY_GATE=PASS
GHSA_AFFECTED_RANGE_BOUNDARY_GATE=PASS
GHSA_FIXED_VERSION_EVIDENCE_GATE=PASS
GHSA_WITHDRAWAL_SEMANTICS_GATE=PASS
GHSA_LIVE_WORKLOAD_GATE=PENDING
GHSA_2_4A_GATE=IN_PROGRESS
```

## Next step

Run the bounded live REST workload probe and commit its measured evidence before accepting ADR-0005 and closing Phase 2.4A.

No AWS runtime should be created before that evidence gate passes.

## Official references reviewed

- GitHub REST API — Global security advisories: https://docs.github.com/en/rest/security-advisories/global-advisories
- GitHub REST API versioning: https://docs.github.com/en/rest/about-the-rest-api/api-versions
- GitHub REST API rate limits: https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api
- GitHub REST API pagination: https://docs.github.com/en/rest/using-the-rest-api/using-pagination-in-the-rest-api
- GitHub REST API best practices: https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api
- GitHub Advisory Database: https://github.com/advisories
- GitHub Advisory Database mirror: https://github.com/github/advisory-database
