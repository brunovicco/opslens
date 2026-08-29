# Phase 2.4C — GHSA Runtime Security and Retry Design

_Date started: 2026-08-28_

_Status: COMPLETE_

## Purpose

Freeze and prove the authenticated outbound, credential, retry, S3 persistence, and deterministic subdivision contracts used by the GHSA Bronze Lambda runtime.

The preceding Phase 2.4C increments proved:

```text
bounded source navigation
exact cursor-chain completion
content-bound attempt_id
deterministic Bronze key layout
versioned COMPLETE manifest contract
```

This increment then carried those boundaries into the live manual `dev` runtime.

## Official-source validation

GitHub documents that authenticated REST requests should send an Authorization header and the versioned API header. GitHub also recommends serial requests and documents explicit rate-limit recovery precedence around `Retry-After`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset`.

AWS documents Secrets Manager as an appropriate location for third-party API credentials used by Lambda and recommends caching secret retrievals.

The accepted runtime decision is recorded in ADR-0007.

## Credential boundary

Selected provider:

```text
AWS Secrets Manager
secret value: raw GitHub token SecretString
version stage: AWSCURRENT
cache TTL: 300 seconds
```

The Lambda execution role receives only:

```text
secretsmanager:GetSecretValue
```

for the exact environment-scoped secret ARN.

The runtime uses the AWS managed `aws/secretsmanager` KMS key. No custom KMS key or custom rotation Lambda is introduced.

Automatic Secrets Manager rotation is intentionally deferred for this dev-only external GitHub credential. The Terraform resource carries an explicit Checkov `CKV2_AWS_57` suppression explaining that GitHub credential rotation would require external GitHub lifecycle logic rather than an AWS-only secret-value rotation. The fine-grained GitHub token is provisioned out of band with bounded GitHub-side expiration.

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
Terraform configuration
Terraform state
```

## Authenticated GitHub HTTP adapter

The runtime contract sends:

```text
Accept: application/vnd.github+json
Authorization: Bearer <secret>
User-Agent: opslens-ghsa-ingestion/0.1
X-GitHub-Api-Version: 2026-03-10
```

`GhsaAuthenticatedPageSource` validates the URL against the existing GHSA outbound allowlist before transport execution.

`HttpsGhsaTransport` uses direct HTTPS and does not automatically follow redirects. Redirects therefore become terminal source-contract events instead of bypassing the outbound allowlist.

The response body remains bounded by the frozen 8 MiB page cap.

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

The 120-second value is a runtime **wait budget**, not permission to retry earlier than GitHub allows. A server-directed or calculated delay above the budget raises a bounded source failure immediately. The runtime never clamps a required 121+ second wait down to 120 seconds.

This keeps one GitHub-directed wait well below the Lambda maximum execution time of 900 seconds and leaves the current invocation available for bounded source work rather than consuming the entire runtime in `sleep`.

HTTP 401 is terminal.

Transport failures and HTTP 500/502/503/504 use a short separate exponential delay.

Every page request has a finite attempt budget. No retry loop is unbounded.

## Outbound URL parsing boundary

The exact `Link: rel="next"` URL remains untrusted input. URL decomposition, port extraction, and strict query parsing share the same malformed-URL exception boundary.

`parse_qsl(..., strict_parsing=True)` failures are converted to `InvalidGhsaRequestUrlError` rather than leaking a bare `ValueError`. Higher page/pagination layers can continue wrapping that domain error deterministically.

## Deterministic oversized-window subdivision

The source window is a closed whole-second range.

If a window cannot satisfy the frozen page/byte caps, the planner may split:

```text
parent = [start, end]

left  = [start, midpoint]
right = [midpoint + 1 second, end]
```

The children do not overlap and leave no represented whole-second gap.

Each child is a new logical synchronization unit with a new `sync_id`.

If the remaining parent is too small to produce two valid children, subdivision fails closed rather than raising the safety caps.

## Versioned S3 adapter

`S3GhsaBronzeRepository` implements the persistence port.

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

## Validated hardening checkpoint

The final pre-apply hardening checkpoint supplied locally on 2026-08-28 was:

```text
61 passed
Ruff: All checks passed
Pyright strict: 0 errors / 0 warnings / 0 informations
```

The subsequent Terraform CI run passed both static checks and the Checkov security scan.

## Live security proof

The deployed Lambda configuration was verified with the expected Python 3.13/x86_64 runtime, 1024 MiB memory, 900-second timeout, active X-Ray, JSON/INFO logging, exact content-addressed deployment hash, least-privilege execution role, and only non-secret environment configuration.

The Secrets Manager container existed before the token value was populated. The token was inserted out of band and became `AWSCURRENT`; the local temporary token material was then explicitly removed.

The first manual GHSA invocation completed without exposing credentials in the Lambda response. The resulting COMPLETE manifest and page evidence contained only the expected safe source/runtime metadata.

The replay of the same bounded source window returned the same deterministic identities and exact S3 VersionIds. S3 version listing proved that conditional persistence did not create duplicate page or manifest versions.

## Cost

The live runtime adds one Secrets Manager secret, one Lambda function, one CloudWatch log group, and the associated IAM role/policy. The workload remains manual-only in this increment, so no EventBridge Scheduler execution cost or autonomous request cadence is introduced.

The 300-second in-memory secret cache keeps Secrets Manager retrieval calls low during warm execution.

## Current gates

```text
GHSA_BRONZE_REQUEST_URL_ALLOWLIST_GATE=PASS
GHSA_BRONZE_AUTHENTICATED_HTTP_GATE=PASS
GHSA_BRONZE_RATE_LIMIT_GATE=PASS
GHSA_BRONZE_SECRET_PROVIDER_GATE=PASS
GHSA_BRONZE_S3_ADAPTER_GATE=PASS
GHSA_BRONZE_SUBDIVISION_GATE=PASS
GHSA_BRONZE_PRE_APPLY_HARDENING_GATE=PASS
GHSA_BRONZE_TERRAFORM_GATE=PASS
GHSA_BRONZE_MANUAL_DEV_RUNTIME_GATE=PASS
GHSA_2_4C_GATE=PASS
```

## Next step

Proceed to Phase 2.4D — GHSA Silver Runtime while preserving the frozen credential, outbound, rate-limit, immutable-evidence, and COMPLETE-manifest authority boundaries.

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
