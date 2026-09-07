# Phase 9 — Gate 9.1: Public Repository Request Admission

_Date: 2026-09-07_

## Status

**COMPLETE / MERGED.**

Starting point:

```text
main:   db10ef80b22067b742eddadf3a43c4514c33d074
issue:  #122
branch: feat/phase9-public-request-admission
```

Final validation and merge:

```text
PR:                 #123
validated head:     26f0d2b5275284d891ee99a7f8276d41cc4f0753
Python CI:          #346 / run 34079446683
merge SHA:          5540d7b508c71aa65d826786618690b7ddc9d433
issue #122:         CLOSED / COMPLETED
```

## Goal

Freeze the untrusted public request boundary before OpsLens exposes any public HTTP runtime, AWS compute, IAM role, GitHub acquisition call, or model invocation.

The v1 public operation is intentionally fixed:

```text
analyze one public GitHub repository
```

It does not accept arbitrary natural-language questions, provider/model selection, tools, SQL, or execution policy from the caller.

## Contract

```text
public-analysis-request:v1
```

Accepted public body shape:

```json
{
  "repository_url": "https://github.com/<owner>/<repository>",
  "requested_ref": "optional ref or null"
}
```

`requested_ref = null` or an omitted field means that the existing Repository Intelligence snapshot resolver will later obtain the repository's authoritative default branch. Gate 9.1 does not invent `main`.

## Admission pipeline

```text
untrusted bytes
 -> <= 2048 byte hard bound
 -> strict UTF-8
 -> JSON object only
 -> duplicate-key rejection
 -> exact known-field admission
 -> local URL decomposition
 -> exact https://github.com authority boundary
 -> owner/name projection
 -> Phase 4 owner/name/ref validators
 -> content-addressed PublicAnalysisRequest
 -> STOP
```

No raw user-controlled URL is preserved as acquisition authority.

The only semantics that survive into the domain request are:

```text
provider = github
owner
repository name
optional requested ref
```

A canonical GitHub web URL may be reconstructed from validated coordinates for human-readable provenance, but the original user URL is never passed to a network transport.

## Request bounds

Frozen v1 limits:

```text
raw request body:   2048 bytes maximum
repository URL:      256 characters maximum
```

The admission layer rejects:

```text
empty body
invalid UTF-8
invalid or excessively nested JSON
non-object JSON
duplicate keys
missing repository_url
unknown fields
wrong field types
non-HTTPS scheme
non-github.com host
userinfo
explicit ports
query strings
fragments
control characters
percent-encoded path data
extra path segments
malformed URL authority syntax
malformed owner/name
invalid requested ref
```

Errors remain bounded and do not echo the untrusted repository URL.

## Why coordinates instead of a fetch URL?

A public URL is user input, not source authority.

If an arbitrary URL crossed the application boundary, future source acquisition would inherit ambiguity around:

```text
scheme
host
port
userinfo
redirects
path normalization
percent encoding
query parameters
fragments
```

Gate 9.1 removes those dimensions before any network capability exists.

Later source resolution receives only already-validated GitHub coordinates and an optional validated ref. The existing Phase 4 source adapter still owns the actual GET-only GitHub transport and immutable snapshot projection.

This preserves:

> **READ, NEVER EXECUTE third-party repository code.**

## Public admission is not repository visibility authority

Gate 9.1 does not prove that the repository is public.

That remains a later deterministic source-evidence decision:

```text
validated owner/name/ref
 -> GitHub metadata acquisition
 -> repository metadata projection
 -> reject private repository
 -> resolve moving/default ref
 -> exact commit SHA + tree SHA
```

Therefore:

```text
public request admitted
 != repository proven public
 != repository snapshot resolved
 != repository analyzed
```

## Deterministic identity

Normalized request semantics are hashed independently from raw transport bytes:

```text
contract_version
provider=github
repository_owner
repository_name
requested_ref
 -> canonical JSON
 -> SHA-256
 -> public-analysis-request:v1:<sha256>
```

Raw request provenance separately records:

```text
raw_body_sha256
raw_body_bytes
```

Consequences:

- JSON whitespace and field ordering may change raw-body provenance;
- equivalent normalized semantics keep the same request identity;
- an explicit ref changes normalized request identity;
- callers cannot forge the normalized digest/request ID without failing validation.

## Security regressions

The Gate 9.1 tests cover representative public-input abuse and parser ambiguity, including:

```text
http://github.com/...
gitlab.com
api.github.com
github.com.evil.example
embedded next=https://github.com/...
userinfo @ host confusion
credentials in URL
explicit :443
query / fragment
/tree/main extra path
percent-encoded owner/path
control characters inside host
backslash / authority ambiguity
malformed bracketed authority
leading whitespace
duplicate JSON keys
unknown fields
wrong types
invalid refs
oversized body
forged request identity
untrusted error-text leakage
```

The purpose is not to implement a general URL sanitizer. The contract instead accepts one small known-safe URL grammar and rejects everything else.

## Architecture dependency direction

```text
public_analysis domain/application
 -> reuses repository_intelligence domain validators

public_analysis
 -X-> GitHub adapter/network transport
 -X-> Bedrock
 -X-> Athena
 -X-> AWS SDK
```

Gate 9.1 therefore remains offline and provider-independent.

## AWS / external-call budget

```text
real AWS calls:        0
GitHub runtime calls:  0
Bedrock model calls:   0
new AWS resources:     0
new IAM roles:         0
new IAM permissions:   0
```

The GitHub connector was used only for repository development operations and is not part of the OpsLens Gate 9.1 runtime path.

## CI evidence

Exact executable head:

```text
26f0d2b5275284d891ee99a7f8276d41cc4f0753
```

Python CI #346 / run `34079446683` passed all seven repository slice jobs.

Public Analysis quality gate:

```text
uv lock --check  PASS
Ruff             PASS
Pyright strict   PASS — 0 errors, 0 warnings, 0 informations
pytest           PASS — 33 passed
```

An earlier run exposed only strict-Pyright `reportUnnecessaryIsInstance` diagnostics on defensive checks over statically typed dataclass fields. The implementation corrected those checks without `type: ignore`, suppression, or weaker typing, then passed the exact-head run above.

## Phase 9 sequencing

Gate 9.1 freezes only request admission.

Gate 9.2 must separately define the orchestration boundary from:

```text
PublicAnalysisRequest
 -> immutable repository snapshot resolution
 -> bounded repository evidence acquisition
 -> deterministic analysis
 -> risk/hybrid evidence composition
 -> public response projection
```

The next gate should remain dependency-injected and testable with fake source ports before public HTTP compute exists. A later real-source validation can then prove that validated coordinates, rather than arbitrary URLs, reach the existing GET-only GitHub transport.

Before public deployment, Phase 9 must also explicitly bound:

```text
request concurrency
rate limiting / abuse controls
timeouts
external-call budgets
model-call budgets
cost pressure
response size
failure disclosure
observability
public runtime IAM
```

## AIP-C01 learning notes

Gate 9.1 reinforces a production GenAI pattern:

> Convert untrusted user intent into the smallest deterministic internal authority token before any external action is possible.

The same pattern applies to:

```text
tool-call arguments
retrieval filters
SQL plans
agent actions
model routing
repository acquisition
```

Validation is not merely input hygiene. In an AI system it is part of the authorization boundary.

## Exit checklist

```text
[x] public-analysis-request:v1 frozen
[x] exact raw-body bounds
[x] duplicate/unknown-field rejection
[x] URL -> validated coordinates only
[x] Phase 4 coordinate/ref validators reused
[x] content-addressed normalized request identity
[x] raw-body provenance separated
[x] SSRF/parser ambiguity regressions
[x] dedicated Python CI slice
[x] ADR 0029
[x] no network/AWS/model dependency
[x] exact-head PR CI green
[x] protected squash merge
[x] issue #122 closed / completed
[x] authoritative state synchronized to Gate 9.2 NEXT
```
