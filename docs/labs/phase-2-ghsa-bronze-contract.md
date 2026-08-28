# Phase 2.4C — GHSA Bronze Contract

_Date started: 2026-08-27_

_Status: IN PROGRESS_

## Purpose

Define deterministic GitHub Security Advisory Bronze request, response-page, cursor-pagination, physical observation, persistence evidence, authenticated runtime, Lambda invocation, and manual `dev` deployment boundaries before Phase 2.4C closeout.

The invariant remains:

> **Agents reason. Code verifies evidence.**

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

HTTP 401 is terminal. Transport and selected 5xx failures use a separate short bounded retry path.

GitHub 403/429 handling follows `Retry-After`, primary reset, and secondary-limit backoff rules. The runtime now has a 120-second per-retry wait budget. A required wait above that budget is never shortened: the fetch fails closed so a later invocation can resume after GitHub permits another request.

Strict continuation-query parsing is also inside the GHSA request-URL domain boundary. Malformed `parse_qsl(..., strict_parsing=True)` input becomes `InvalidGhsaRequestUrlError` rather than a bare `ValueError`.

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

## Lambda invocation contract

The v1 manual event remains:

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

## Prior validated checkpoint and immutable artifact evidence

Before the final pre-apply hardening changes, the focused local checkpoint was green:

```text
57 passed
Ruff: All checks passed
Pyright strict: 0 errors / 0 warnings / 0 informations
```

That exact source revision produced and published:

```text
sha256=9deb08f346cbe7261199568de8a515b26b2865d7f6d2a592d837a0ac0368c928
s3_key=lambda/ghsa-bronze/9deb08f346cbe7261199568de8a515b26b2865d7f6d2a592d837a0ac0368c928.zip
s3_version_id=fYDkvIkv15n.GHoGCgOQbgcuFObO_P3w
checksum_sha256=nesI80bL5yYRmVaN6KUVsmsoZdf20qWS2DegrANoySg=
content_length=17555239
content_type=application/zip
checksum_type=FULL_OBJECT
encryption=AES256
```

The object remains valid immutable evidence for that revision. It is no longer the deployable representation of the current branch because the pre-apply hardening changed runtime source code.

The previously reviewed Terraform plan was:

```text
Plan: 5 to add, 0 to change, 0 to destroy.
```

That saved plan must not be applied after the source changes. The current Terraform artifact pin must be replaced with the next exact artifact SHA-256 and S3 VersionId before a new reviewed plan.

## Pre-apply hardening checkpoint

Implemented changes:

```text
GHSA retry wait budget: 120 seconds
server-required waits above budget: fail closed, never clamp downward
strict query parse ValueError: wrapped as InvalidGhsaRequestUrlError
```

These changes are implemented in the branch but are not promoted until the fresh local test/lint/type checkpoint is supplied.

## Current gates

```text
GHSA_BRONZE_SYNC_WINDOW_GATE=PASS
GHSA_BRONZE_PAGE_CONTRACT_GATE=PASS
GHSA_BRONZE_CURSOR_COMPLETION_GATE=PASS
GHSA_BRONZE_ATTEMPT_ID_GATE=PASS
GHSA_BRONZE_KEY_LAYOUT_GATE=PASS
GHSA_BRONZE_COMPLETE_MANIFEST_GATE=PASS
GHSA_BRONZE_SECRET_PROVIDER_GATE=PASS
GHSA_BRONZE_S3_ADAPTER_GATE=PASS
GHSA_BRONZE_SUBDIVISION_GATE=PASS

GHSA_BRONZE_REQUEST_URL_ALLOWLIST_GATE=PASS_PENDING_REVALIDATION
GHSA_BRONZE_AUTHENTICATED_HTTP_GATE=PASS_PENDING_REVALIDATION
GHSA_BRONZE_RATE_LIMIT_GATE=PASS_PENDING_REVALIDATION
GHSA_BRONZE_RUNTIME_COMPOSITION_GATE=PASS_PENDING_REVALIDATION
GHSA_BRONZE_LAMBDA_INVOCATION_CONTRACT_GATE=PASS_PENDING_REVALIDATION
GHSA_BRONZE_PRE_APPLY_HARDENING_GATE=PASS_PENDING_LOCAL_VALIDATION

GHSA_BRONZE_LAMBDA_ARTIFACT_BUILD_GATE=STALE_REBUILD_REQUIRED
GHSA_BRONZE_ARTIFACT_PUBLICATION_GATE=STALE_REPUBLISH_REQUIRED
GHSA_BRONZE_TERRAFORM_GATE=STALE_REPIN_AND_REPLAN_REQUIRED
GHSA_BRONZE_MANUAL_DEV_RUNTIME_GATE=PENDING
GHSA_2_4C_GATE=IN_PROGRESS
```

## AWS / IAM / cost boundary

The planned manual `dev` runtime remains intentionally minimal:

```text
Secrets Manager secret container
Lambda execution role
least-privilege GetSecretValue
least-privilege S3 Bronze read/write verification
CloudWatch log group
X-Ray write permissions
Lambda function pinned to content-addressed S3 artifact + exact VersionId
```

No GHSA AWS runtime resources have been applied yet. EventBridge Scheduler remains deferred until manual invocation is proven in `dev`.

## Next step

Run the focused GHSA ingestion tests, Ruff, and strict Pyright on the hardening head. If green, build and publish a new deterministic artifact, capture its exact SHA-256 and S3 VersionId, repin Terraform, and generate a fresh reviewed plan before apply.

## References

- `docs/adr/0005-ghsa-source-and-synchronization-strategy.md`
- `docs/adr/0006-ghsa-silver-content-versioning-and-physical-shape.md`
- `docs/adr/0007-ghsa-runtime-credential-and-retry-strategy.md`
- `docs/labs/phase-2-ghsa-runtime-security-design.md`
- `docs/labs/phase-2-ghsa-runtime-composition.md`
- `docs/labs/phase-2-ghsa-lambda-contract.md`
- `docs/labs/phase-2-ghsa-manual-dev-runtime.md`
