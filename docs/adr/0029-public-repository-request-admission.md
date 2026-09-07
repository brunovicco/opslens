# ADR 0029 — Admit Public Repository Requests as Validated Coordinates, Not Fetch URLs

- Status: Accepted
- Date: 2026-09-06
- Phase: 9 — Public Analyze Your Repository
- Gate: 9.1

## Context

Phase 9 introduces an untrusted public input boundary before OpsLens has any public HTTP compute.

The future public experience needs to accept a repository reference from a user while preserving the Phase 4 rule:

> **READ, NEVER EXECUTE third-party repository code.**

A raw URL is not source authority. Carrying arbitrary user-controlled URLs into acquisition code would unnecessarily create host, scheme, port, path, redirect, query, and credential ambiguity and would enlarge the SSRF/security surface.

OpsLens already owns a deterministic GitHub repository coordinate/ref contract in Repository Intelligence and an immutable snapshot resolver that verifies repository metadata, rejects private repositories, resolves moving/default refs, and projects exact commit/tree SHAs.

Phase 9 should reuse that authority rather than create a second repository identity model.

## Decision

Freeze:

```text
public-analysis-request:v1
```

The public v1 operation is fixed to “analyze one GitHub repository.” It accepts only:

```json
{
  "repository_url": "https://github.com/<owner>/<repository>",
  "requested_ref": "optional clean GitHub ref or null"
}
```

`requested_ref` is optional. Missing/null means “use the repository default branch during later source resolution.” OpsLens does not invent `main`.

### Raw request bounds

The provider-independent admission function accepts UTF-8 JSON bytes with a hard maximum of:

```text
2048 bytes
```

It rejects:

- empty or invalid UTF-8 input;
- invalid/non-object JSON;
- duplicate JSON keys;
- missing required fields;
- unknown fields;
- wrong field types.

### URL admission

`repository_url` is parsed locally and discarded as a transport target.

Only validated coordinates survive:

```text
owner
repository name
optional requested ref
```

The URL must:

- use HTTPS;
- target `github.com`;
- contain no userinfo;
- contain no explicit port;
- contain no query string;
- contain no fragment;
- identify exactly one owner/repository path;
- fit the public character bound;
- pass the existing Phase 4 GitHub coordinate validation.

One optional trailing slash and case-insensitive GitHub hostname spelling are normalized into the same internal semantics.

The implementation does **not** forward the user URL to an HTTP client.

### Ref authority

An explicit ref is validated through the existing Phase 4 GitHub ref semantics. Null remains null until the source metadata determines the default branch.

The public boundary does not claim that a repository is public. Later immutable snapshot resolution still must fetch GitHub repository metadata and reject private repositories through the existing deterministic projection.

### Request identity

Normalized admitted semantics are content-addressed:

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

The raw body has a separate SHA-256 and byte count as content-free admission provenance. JSON whitespace/key order may change the raw-body hash while preserving the same normalized request identity.

## Authority boundary

```text
untrusted public JSON
 -> strict local parser
 -> GitHub URL reduced to owner/name coordinates
 -> Phase 4 coordinate/ref validators
 -> content-addressed PublicAnalysisRequest
 -> STOP
```

Gate 9.1 performs no network/provider/AWS operations.

A later gate may pass only the validated coordinates/ref into the existing read-only GitHub snapshot resolver.

## Security consequences

This decision prevents arbitrary public URLs from becoming acquisition authority and reduces future SSRF risk before HTTP infrastructure exists.

It also prevents public users from selecting:

- provider;
- model;
- tools;
- SQL;
- arbitrary natural-language analysis behavior.

The v1 public operation is intentionally narrower than internal OpsLens capabilities.

Error messages remain bounded and do not echo the untrusted repository URL, making them safer candidates for future telemetry.

## Alternatives rejected

### Forward the supplied URL to an HTTP client

Rejected. It unnecessarily turns parsing ambiguity into network authority and expands the SSRF/redirect/credential surface.

### Accept arbitrary GitHub URLs and normalize every path variant

Rejected for v1. Repository root URLs are enough for the public operation and are easier to reason about and test.

### Accept arbitrary natural-language questions in Gate 9.1

Rejected. Phase 9 first needs a bounded public repository operation; arbitrary questions would broaden prompt, route, cost, abuse, and output authority before the public transport exists.

### Default missing refs to `main`

Rejected. GitHub repositories have authoritative default-branch metadata. Inventing `main` would be source-semantics drift.

### Create a new repository identity contract for Phase 9

Rejected. Phase 4 already owns GitHub owner/name/ref validation and immutable snapshot identity.

## Operational consequences

Gate 9.1 introduces:

```text
AWS calls:          0
GitHub calls:       0
model calls:        0
new AWS resources:  0
new IAM changes:    0
```

Rate limiting, authentication/session design, public runtime compute, API Gateway/CloudFront/WAF decisions, source acquisition, analysis orchestration, and public output shape remain later Phase 9 gates.

## AIP-C01 learning

The useful architecture lesson is broader than URL validation:

> Treat untrusted user inputs as proposals. Reduce them to the smallest deterministic internal authority token before allowing external actions.

In GenAI systems this same pattern applies to tool calls, retrieval filters, SQL plans, model routing, and agent actions.
