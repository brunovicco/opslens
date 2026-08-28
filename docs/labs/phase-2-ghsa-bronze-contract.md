# Phase 2.4C — GHSA Bronze Contract

_Date started: 2026-08-27_

_Status: IN PROGRESS_

## Purpose

Define deterministic GitHub Security Advisory Bronze request, response-page, cursor-pagination, physical observation, persistence evidence, authenticated runtime, and Lambda invocation boundaries before Phase 2.4C closeout.

The invariant remains:

> **Agents reason. Code verifies evidence.**

## Validated contract gates

Local validation through the bounded runtime-composition increment is green based on the user's confirmed checkpoint:

```text
pytest GHSA ingestion: PASS
Ruff GHSA ingestion: PASS
Pyright strict: PASS
```

Therefore:

```text
GHSA_BRONZE_SYNC_WINDOW_GATE=PASS
GHSA_BRONZE_REQUEST_URL_ALLOWLIST_GATE=PASS
GHSA_BRONZE_PAGE_CONTRACT_GATE=PASS
GHSA_BRONZE_CURSOR_COMPLETION_GATE=PASS
GHSA_BRONZE_ATTEMPT_ID_GATE=PASS
GHSA_BRONZE_KEY_LAYOUT_GATE=PASS
GHSA_BRONZE_COMPLETE_MANIFEST_GATE=PASS
GHSA_BRONZE_AUTHENTICATED_HTTP_GATE=PASS
GHSA_BRONZE_RATE_LIMIT_GATE=PASS
GHSA_BRONZE_SECRET_PROVIDER_GATE=PASS
GHSA_BRONZE_S3_ADAPTER_GATE=PASS
GHSA_BRONZE_SUBDIVISION_GATE=PASS
GHSA_BRONZE_RUNTIME_COMPOSITION_GATE=PASS
```

## Frozen identity boundary

```text
observed_advisory_version_id != sync_id != attempt_id
```

- `observed_advisory_version_id` identifies exact advisory content.
- `sync_id` identifies one logical GitHub query window.
- `attempt_id` identifies one exact complete physical page/cursor observation.

## Frozen Bronze layout

```text
bronze/ghsa/advisories/
  mode=<published|modified>/
    sync_id=<sha256>/
      attempt_id=<sha256>/
        page=<000001...>/response.json
        manifest.json
```

Page and manifest writes require exact S3 VersionId evidence. `If-None-Match: *` protects immutable keys; a replay is accepted only after exact metadata verification.

## Authenticated source boundary

The production GitHub source path is authenticated and bounded:

```text
AWS Secrets Manager SecretString
    -> cached token provider
    -> Authorization: Bearer <token>
    -> HTTPS api.github.com/advisories
    -> exact rel=next traversal
```

The token never enters URLs, logs, Bronze objects, manifests, `sync_id`, or `attempt_id`.

Rate-limit handling is bounded around GitHub `Retry-After`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` evidence. HTTP 401 is terminal. Transport and selected 5xx failures use a separate short bounded retry path.

## Runtime composition

`GhsaBronzeRuntimeService` executes:

```text
GhsaSyncWindow
  -> deterministic first URL
  -> authenticated page fetch
  -> page validation
  -> exact rel=next traversal
  -> complete bounded pagination
  -> attempt_id
  -> deterministic page keys
  -> versioned page persistence
  -> COMPLETE manifest
  -> versioned manifest persistence
```

The complete cursor chain is buffered before attempt-keyed persistence because `attempt_id` depends on the complete physical observation.

If aggregate page-count or total-byte limits are exceeded, the parent window is deterministically subdivided before persistence. Subdivision is bounded by a maximum leaf-window budget.

## Lambda invocation increment

The next increment freezes the manual Lambda event and response contract without creating AWS resources yet.

The v1 input shape is:

```json
{
  "schema_version": 1,
  "mode": "published",
  "start_at": "2026-08-01T00:00:00Z",
  "end_at": "2026-08-02T00:00:00Z"
}
```

Unknown fields fail closed. Timestamps must use canonical UTC whole-second `Z` form.

The Lambda environment contains only non-secret configuration and the Secrets Manager secret identifier. Credential material remains exclusively in Secrets Manager.

The deployment build script emits a deterministic Python 3.13 artifact and the future content-addressed deployment key:

```text
lambda/ghsa-bronze/<artifact-sha256>.zip
```

Terraform must later pin the exact key, exact S3 VersionId, and exact source code hash. Mutable filename-only deployment references are forbidden.

## Current gates

```text
GHSA_BRONZE_RUNTIME_COMPOSITION_GATE=PASS
GHSA_BRONZE_LAMBDA_INVOCATION_CONTRACT_GATE=PASS_PENDING_LOCAL_VALIDATION
GHSA_BRONZE_LAMBDA_ARTIFACT_BUILD_GATE=PASS_PENDING_LOCAL_VALIDATION
GHSA_BRONZE_TERRAFORM_GATE=PENDING
GHSA_2_4C_GATE=IN_PROGRESS
```

## AWS / IAM / cost boundary

No new AWS resource is introduced by the Lambda contract increment.

The next infrastructure step, only after local validation and deterministic artifact build evidence, will add the minimum manual `dev` path:

```text
Secrets Manager secret container
Lambda execution role
least-privilege GetSecretValue
least-privilege S3 Bronze read/write verification
CloudWatch log group
X-Ray write permissions
Lambda function pinned to content-addressed S3 artifact + exact VersionId
```

EventBridge Scheduler remains deferred until manual invocation is proven in `dev`.

## References

- `docs/adr/0005-ghsa-source-and-synchronization-strategy.md`
- `docs/adr/0006-ghsa-silver-content-versioning-and-physical-shape.md`
- `docs/adr/0007-ghsa-runtime-credential-and-retry-strategy.md`
- `docs/labs/phase-2-ghsa-runtime-security-design.md`
- `docs/labs/phase-2-ghsa-runtime-composition.md`
- `docs/labs/phase-2-ghsa-lambda-contract.md`
