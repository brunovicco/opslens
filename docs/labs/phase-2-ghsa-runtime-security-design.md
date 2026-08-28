# Phase 2.4C — GHSA Runtime Security and Retry Design

_Date started: 2026-08-28_

_Status: IN PROGRESS_

## Purpose

Freeze the authenticated outbound, credential, retry, S3 persistence, and deterministic
subdivision contracts before GHSA Lambda and Terraform resources are introduced.

The preceding Phase 2.4C increments already proved:

```text
bounded source navigation
exact cursor-chain completion
content-bound attempt_id
deterministic Bronze key layout
versioned COMPLETE manifest contract
```

This increment moves from evidence shape toward runtime-capable adapters while still creating
no AWS resources.

## Official-source validation

GitHub documents that authenticated REST requests should send an Authorization header and the
versioned API header. GitHub also recommends serial requests and documents explicit rate-limit
recovery precedence around `Retry-After`, `X-RateLimit-Remaining`, and
`X-RateLimit-Reset`.

AWS documents Secrets Manager as an appropriate location for third-party API credentials used
by Lambda and recommends caching secret retrievals.

The accepted runtime decision is recorded in ADR-0007.

## Credential boundary

Selected provider:

```text
AWS Secrets Manager
secret value: raw GitHub token SecretString
version stage: AWSCURRENT
cache TTL: 300 seconds
```

The future Lambda execution role will receive only:

```text
secretsmanager:GetSecretValue
```

for the exact environment-scoped secret ARN.

The first runtime uses the AWS managed `aws/secretsmanager` KMS key. No custom KMS key or
custom rotation Lambda is introduced.

The GitHub token is never placed in:

```text
request URL
logs
metrics
traces
Bronze object body added by OpsLens
S3 object key
manifest
sync_id
attempt_id
```

## Authenticated GitHub HTTP adapter

The runtime contract sends:

```text
Accept: application/vnd.github+json
Authorization: Bearer <secret>
User-Agent: opslens-ghsa-ingestion/0.1
X-GitHub-Api-Version: 2026-03-10
```

`GhsaAuthenticatedPageSource` validates the URL against the existing GHSA outbound allowlist
before transport execution.

`HttpsGhsaTransport` uses direct HTTPS and does not automatically follow redirects. Redirects
therefore become terminal source-contract events instead of bypassing the outbound allowlist.

The response body remains bounded by the already frozen 8 MiB page cap.

## Rate-limit and transient retry policy

GitHub rate-limit handling is separate from ordinary transient failures.

For HTTP 403/429:

```text
Retry-After
    -> exact delay when <= 120 seconds

else X-RateLimit-Remaining == 0 + X-RateLimit-Reset
    -> exact delay until just after reset when <= 120 seconds

else
    -> 60 seconds minimum
       exponential growth on repeated rate limits
       fail closed when the calculated wait exceeds 120 seconds
```

The 120-second value is a runtime **wait budget**, not permission to retry earlier than GitHub
allows. A server-directed or calculated delay above the budget raises a bounded source failure
immediately. The runtime never clamps a required 121+ second wait down to 120 seconds.

This keeps one GitHub-directed wait well below the Lambda maximum execution time of 900 seconds
and leaves the current invocation available for bounded source work rather than consuming the
entire runtime in `sleep`.

HTTP 401 is terminal.

Transport failures and HTTP 500/502/503/504 use a short separate exponential delay.

Every page request has a finite attempt budget. No retry loop is unbounded.

## Outbound URL parsing boundary

The exact `Link: rel="next"` URL remains untrusted input. URL decomposition, port extraction,
and strict query parsing now share the same malformed-URL exception boundary.

`parse_qsl(..., strict_parsing=True)` failures are therefore converted to
`InvalidGhsaRequestUrlError` rather than leaking a bare `ValueError`. Higher page/pagination
layers can continue wrapping that domain error deterministically.

## Deterministic oversized-window subdivision

The current source window is a closed whole-second range.

If a window cannot satisfy the frozen page/byte caps, the planner may split:

```text
parent = [start, end]

left  = [start, midpoint]
right = [midpoint + 1 second, end]
```

The children do not overlap and leave no represented whole-second gap.

Each child is a new logical synchronization unit with a new `sync_id`.

If the parent is too small to create two valid children, subdivision fails closed rather than
raising the safety caps.

## Versioned S3 adapter

`S3GhsaBronzeRepository` implements the existing persistence port.

Writes use:

```text
PutObject
If-None-Match: *
versioned S3 bucket required
```

A successful create must return `VersionId`.

On HTTP 412, the adapter accepts the existing exact key only when `HeadObject` proves:

```text
expected size
application/json ContentType
expected deterministic metadata
non-empty VersionId
```

Otherwise replay fails closed.

Both response pages and COMPLETE manifests use this conditional immutable-write behavior.

## Cost

The code in this increment creates no AWS resources.

The planned credential service adds one Secrets Manager secret. Current public AWS pricing
lists USD 0.40 per secret per month plus API request charges. A 300-second in-memory cache is
used to keep retrieval calls low.

## Current hardening checkpoint

The original authenticated runtime gates were previously green. The pre-apply hardening changes
now require a fresh focused validation before a new deployment artifact is built:

```text
GHSA_BRONZE_REQUEST_URL_ALLOWLIST_GATE=PASS_PENDING_REVALIDATION
GHSA_BRONZE_RATE_LIMIT_GATE=PASS_PENDING_REVALIDATION
GHSA_BRONZE_PRE_APPLY_HARDENING_GATE=PASS_PENDING_LOCAL_VALIDATION
GHSA_2_4C_GATE=IN_PROGRESS
```

## Next step

Run the focused GHSA ingestion tests, Ruff, and strict Pyright. If green, rebuild the
deterministic Lambda artifact, publish the new content-addressed object, repin Terraform to its
exact SHA-256 + S3 VersionId, and rerun the reviewed plan before apply.

## References

- `docs/adr/0005-ghsa-source-and-synchronization-strategy.md`
- `docs/adr/0006-ghsa-silver-content-versioning-and-physical-shape.md`
- `docs/adr/0007-ghsa-runtime-credential-and-retry-strategy.md`
- GitHub REST authentication:
  https://docs.github.com/en/rest/authentication/authenticating-to-the-rest-api
- GitHub REST best practices:
  https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api
- GitHub REST rate limits:
  https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api
- AWS Lambda timeout:
  https://docs.aws.amazon.com/lambda/latest/dg/configuration-timeout.html
- AWS Lambda and Secrets Manager:
  https://docs.aws.amazon.com/lambda/latest/dg/with-secrets-manager.html
- AWS Secrets Manager best practices:
  https://docs.aws.amazon.com/secretsmanager/latest/userguide/best-practices.html
- AWS Secrets Manager pricing:
  https://aws.amazon.com/secrets-manager/pricing/
