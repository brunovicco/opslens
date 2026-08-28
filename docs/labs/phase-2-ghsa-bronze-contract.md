# Phase 2.4C — GHSA Bronze Contract

_Date started: 2026-08-27_

_Status: IN PROGRESS_

## Purpose

Define deterministic GitHub Security Advisory Bronze request, response-page, cursor-pagination,
physical observation, persistence, and runtime-security contracts before AWS resources are
introduced.

Phase 2.4A froze the GitHub source contract. Phase 2.4B froze advisory content-version Silver
semantics. Phase 2.4C owns the exact physical source observation and Bronze runtime boundary.

> **Agents reason. Code verifies evidence.**

## Dependency checkpoint

```text
Phase 2.4A — GHSA Source Contract:          COMPLETE
Phase 2.4B — GHSA Advisory/Silver Contract: COMPLETE
Phase 2.4C — GHSA Bronze:                   IN PROGRESS
```

The accepted identity separation remains:

```text
observed_advisory_version_id != sync_id != attempt_id
```

## Increment 1 — source navigation and cursor completion

The first increment froze:

```text
bounded published/modified GhsaSyncWindow
deterministic sync_id
reviewed-only source validation
exact response-byte SHA-256
allowlisted Link rel=next navigation
within-page and cross-page published ordering
duplicate GHSA detection
64-page / 64-MiB bounded completion
```

Local evidence:

```text
16 passed
Ruff: all checks passed
Pyright strict: 0 errors / 0 warnings / 0 informations
```

## Increment 2 — physical attempt and COMPLETE evidence

The second increment froze:

```text
content-bound GhsaAttemptIdFactory
deterministic attempt-scoped Bronze keys
exact S3 key + VersionId persistence evidence
canonical COMPLETE manifest
zero-result [] as valid complete source evidence
```

Frozen layout:

```text
bronze/ghsa/advisories/
  mode=<published|modified>/
    sync_id=<logical-query-sha256>/
      attempt_id=<physical-observation-sha256>/
        page=<000001...>/response.json
        manifest.json
```

The first local run after this increment reported:

```text
30 passed
Pyright strict: 0 errors / 0 warnings / 0 informations
```

Ruff reported two style-only findings in the manifest implementation. Both were corrected in
`0c1a987`; the final combined rerun after that style-only correction was not separately
captured in this conversation before the next increment was explicitly requested.

## Increment 3 — authenticated runtime-security adapters

The third increment moves toward the real runtime while still creating no AWS resources.

### Credential strategy

ADR-0007 accepts:

```text
credential store: AWS Secrets Manager
secret value: raw GitHub token SecretString
version stage: AWSCURRENT
warm-runtime cache TTL: 300 seconds
initial KMS key: aws/secretsmanager
```

The future Lambda execution role is intended to receive only
`secretsmanager:GetSecretValue` on the exact GHSA token secret ARN.

No custom token-rotation Lambda is introduced. Rotation remains an explicit operational action
until a stronger ownership model such as GitHub App installation credentials is justified.

### Authenticated source adapter

Every request sends:

```text
Accept: application/vnd.github+json
Authorization: Bearer <secret>
User-Agent: opslens-ghsa-ingestion/0.1
X-GitHub-Api-Version: 2026-03-10
```

The token is not included in URLs, telemetry fields, Bronze evidence, manifests, `sync_id`, or
`attempt_id`.

`HttpsGhsaTransport` performs direct HTTPS requests and does not automatically follow
redirects. This keeps the existing outbound allowlist authoritative instead of allowing a
redirect target to bypass it before validation.

### GitHub rate-limit policy

Requests remain serial and bounded.

For HTTP 403/429:

```text
Retry-After present
    -> wait that many seconds

else X-RateLimit-Remaining == 0 + X-RateLimit-Reset
    -> wait until just after reset

else
    -> wait at least 60 seconds
       exponential growth for repeated secondary limits
       maximum delay 900 seconds
```

HTTP 401 is terminal. Transport failures and HTTP 500/502/503/504 use a separate short
exponential retry path.

### Deterministic subdivision

If a valid logical window cannot satisfy the frozen pagination/byte caps, the subdivision
contract is:

```text
parent = [start, end]
left   = [start, midpoint]
right  = [midpoint + 1 second, end]
```

The children are non-overlapping and gapless at the frozen whole-second source precision. Each
child has a new `sync_id`. If the parent is too small to create two valid children, the runtime
fails closed rather than weakening the safety caps.

### Versioned S3 adapter

`S3GhsaBronzeRepository` implements conditional immutable writes:

```text
PutObject
If-None-Match: *
VersionId required
```

A 412 precondition result is accepted only when `HeadObject` proves the existing exact key has
the expected size, `application/json` content type, deterministic metadata, and non-empty
VersionId.

The same immutable-write rule applies to response pages and COMPLETE manifests.

## AWS / IAM / cost boundary

Increment 3 still creates no AWS resources.

Planned Secrets Manager cost is approximately USD 0.40 per secret per month plus API request
charges at current public pricing. The 300-second process-local cache is intended to keep
secret retrieval calls low.

Not yet created:

```text
Secrets Manager secret
Lambda
IAM role/policies
EventBridge Scheduler
Terraform resources
runtime artifact
real S3 objects
```

## Current gates

```text
GHSA_BRONZE_SYNC_WINDOW_GATE=PASS
GHSA_BRONZE_REQUEST_URL_ALLOWLIST_GATE=PASS
GHSA_BRONZE_PAGE_CONTRACT_GATE=PASS
GHSA_BRONZE_CURSOR_COMPLETION_GATE=PASS

GHSA_BRONZE_ATTEMPT_ID_GATE=PASS_PENDING_FINAL_COMBINED_RERUN
GHSA_BRONZE_KEY_LAYOUT_GATE=PASS_PENDING_FINAL_COMBINED_RERUN
GHSA_BRONZE_COMPLETE_MANIFEST_GATE=PASS_PENDING_FINAL_COMBINED_RERUN

GHSA_BRONZE_AUTHENTICATED_HTTP_GATE=PASS_PENDING_LOCAL_VALIDATION
GHSA_BRONZE_RATE_LIMIT_GATE=PASS_PENDING_LOCAL_VALIDATION
GHSA_BRONZE_SECRET_PROVIDER_GATE=PASS_PENDING_LOCAL_VALIDATION
GHSA_BRONZE_S3_ADAPTER_GATE=PASS_PENDING_LOCAL_VALIDATION
GHSA_BRONZE_SUBDIVISION_GATE=PASS_PENDING_LOCAL_VALIDATION

GHSA_BRONZE_RUNTIME_COMPOSITION_GATE=PENDING
GHSA_BRONZE_TERRAFORM_GATE=PENDING
GHSA_2_4C_GATE=IN_PROGRESS
```

## Next step

Run one combined GHSA ingestion checkpoint covering all three increments:

```text
pytest GHSA ingestion
Ruff GHSA ingestion
Pyright strict
```

If green, the evidence and adapter gates can all move to PASS. The next increment is bounded
runtime composition. Terraform and AWS resource creation remain after that composition is
locally green.

## References

- `docs/adr/0005-ghsa-source-and-synchronization-strategy.md`
- `docs/adr/0006-ghsa-silver-content-versioning-and-physical-shape.md`
- `docs/adr/0007-ghsa-runtime-credential-and-retry-strategy.md`
- `docs/labs/phase-2-ghsa-runtime-security-design.md`
- GitHub REST authentication:
  https://docs.github.com/en/rest/authentication/authenticating-to-the-rest-api
- GitHub REST best practices:
  https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api
- GitHub REST rate limits:
  https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api
- AWS Lambda and Secrets Manager:
  https://docs.aws.amazon.com/lambda/latest/dg/with-secrets-manager.html
- AWS Secrets Manager pricing:
  https://aws.amazon.com/secrets-manager/pricing/
