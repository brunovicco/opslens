# ADR-0007 — GHSA runtime credential and retry strategy

- **Status:** Accepted
- **Date:** 2026-08-28
- **Decision scope:** Phase 2.4C — GHSA Bronze runtime boundary

## Context

Phase 2.4A selected the GitHub Global Security Advisories REST API as the GHSA runtime
source. Phase 2.4B separated advisory content identity from synchronization identity and
physical observation identity. Phase 2.4C now needs an authenticated, bounded runtime
boundary before Lambda and Terraform are introduced.

The runtime must satisfy four constraints simultaneously:

1. GitHub production access is authenticated but credentials must never enter URLs, Bronze
   objects, manifests, logs, `sync_id`, or `attempt_id`.
2. GitHub documents distinct primary and secondary rate-limit recovery behavior.
3. Exact GitHub `Link: rel="next"` URLs are untrusted outbound navigation input.
4. One unexpectedly large logical window must subdivide deterministically rather than become
   an unbounded traversal.

## Decision

### Credential storage

OpsLens will store one dedicated GitHub API token in **AWS Secrets Manager**.

The first runtime will use a fine-grained GitHub token with no repository permissions because
the selected global-advisory endpoint does not require repository access. The token is stored
as the raw `SecretString` of one environment-scoped secret and is read from `AWSCURRENT`.

The Lambda execution role will receive only `secretsmanager:GetSecretValue` for that exact
secret ARN.

The initial secret will use the AWS managed `aws/secretsmanager` KMS key. A customer-managed
KMS key is not introduced because there is no cross-account secret access or custom key-policy
requirement in the current architecture.

Credential retrieval is cached in memory for 300 seconds. The cache is an optimization only;
the source of truth remains Secrets Manager.

GitHub-token rotation remains an explicit operational action in this phase. OpsLens will not
add a custom rotation Lambda merely to automate rotation of an external token. A later move to
GitHub App installation tokens can replace the provider behind the same credential port if the
workload or ownership model justifies it.

### Authenticated request contract

Every GitHub advisory request sends:

```text
Accept: application/vnd.github+json
Authorization: Bearer <secret>
User-Agent: opslens-ghsa-ingestion/0.1
X-GitHub-Api-Version: 2026-03-10
```

The Authorization value is never emitted to telemetry or persisted evidence.

The transport does not automatically follow HTTP redirects. The source contract already fixes
`https://api.github.com/advisories`; silently following a redirect would bypass the outbound
URL allowlist before the redirect target could be validated.

### Rate-limit recovery

Requests are serial.

For HTTP 403/429, retry timing follows GitHub's documented precedence:

```text
Retry-After present
    -> wait that many seconds

else X-RateLimit-Remaining == 0 and X-RateLimit-Reset present
    -> wait until just after the reset epoch

else
    -> wait at least 60 seconds
       and exponentially increase repeated secondary-limit delays
```

The runtime has a **120-second per-retry wait budget**. This budget does not override GitHub's
minimum retry timing. If `Retry-After`, the primary-limit reset delay, or the calculated
secondary-limit backoff requires more than 120 seconds, OpsLens does **not** clamp the delay to
120 seconds and retry early. It fails the current source fetch immediately so a later bounded
invocation can resume after the required wait.

This is intentionally separate from the Lambda function timeout. Lambda can run for at most
900 seconds, so one GitHub-directed wait must not be allowed to consume the entire invocation
budget.

The page request still has a bounded attempt count. HTTP 401 is terminal and is not retried.

HTTP 500/502/503/504 and transport failures use a separate short bounded exponential retry
budget. Rate-limit backoff and ordinary transient-source retries are not conflated.

### Deterministic oversized-window subdivision

If one valid logical window cannot complete within the frozen page/byte safety caps, the
runtime may split it into two closed whole-second child windows.

For a parent `[start, end]`, the children are deterministic, non-overlapping, and gapless at
whole-second resolution:

```text
left  = [start, midpoint]
right = [midpoint + 1 second, end]
```

Each child receives its own `sync_id`; no parent `attempt_id` is promoted as COMPLETE when the
parent exceeded the safety contract.

If the remaining parent is too small to produce two valid children, the runtime fails closed
instead of weakening the safety caps.

### S3 evidence adapter

Bronze page and manifest writes use conditional `PutObject` with `If-None-Match: *`.

A successful write must expose an S3 `VersionId`.

A precondition failure is acceptable only when `HeadObject` proves that the existing exact key
has the expected size, content type, and deterministic metadata. Otherwise the run fails
closed.

## Consequences

### Positive

- Secrets stay outside source identity and persistence evidence.
- The GitHub token can rotate without changing `sync_id` or `attempt_id`.
- Rate-limit behavior follows GitHub's documented recovery requirements without retrying earlier
  than GitHub permits.
- A single long GitHub-directed wait cannot consume the complete Lambda timeout budget.
- Redirects cannot silently escape the selected outbound host/path boundary.
- S3 replay is idempotent while still requiring versioned evidence.
- Source growth causes deterministic subdivision rather than unbounded pagination.

### Trade-offs

- Secrets Manager adds a small recurring service cost.
- A long-lived fine-grained token still has external credential lifecycle work.
- A rate-limit delay above the 120-second runtime budget ends the current fetch and requires a
  later invocation rather than waiting in place.
- Disabling redirects is stricter than GitHub's generic REST best-practice guidance; a future
  legitimate endpoint migration must update the source contract explicitly.
- Window subdivision creates multiple child synchronization identities and therefore requires
  explicit orchestration/completion semantics in the runtime gate.

## Cost

At current public pricing, one Secrets Manager secret is approximately USD 0.40 per month plus
API-request charges. The 300-second in-memory cache keeps retrieval calls low.

No Lambda, EventBridge, IAM, Secrets Manager, or S3 resource is created by accepting this ADR;
those resources belong to the later Phase 2.4C runtime/Terraform increment.

## References

- GitHub REST API authentication:
  https://docs.github.com/en/rest/authentication/authenticating-to-the-rest-api
- GitHub REST API best practices:
  https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api
- GitHub REST API rate limits:
  https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api
- AWS Lambda timeout:
  https://docs.aws.amazon.com/lambda/latest/dg/configuration-timeout.html
- AWS Lambda — use Secrets Manager secrets:
  https://docs.aws.amazon.com/lambda/latest/dg/with-secrets-manager.html
- AWS Secrets Manager best practices:
  https://docs.aws.amazon.com/secretsmanager/latest/userguide/best-practices.html
- AWS Secrets Manager pricing:
  https://aws.amazon.com/secrets-manager/pricing/
