# Phase 2.4C — GHSA Bronze Contract

_Date started: 2026-08-27_

_Status: COMPLETE_

## Purpose

Define and prove deterministic GitHub Security Advisory Bronze request, response-page, cursor-pagination, physical observation, persistence evidence, authenticated runtime, Lambda invocation, and manual `dev` deployment boundaries before Phase 2.4D.

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

GitHub 403/429 handling follows `Retry-After`, primary reset, and secondary-limit backoff rules. The runtime has a 120-second per-retry wait budget. A required wait above that budget is never shortened: the fetch fails closed so a later invocation can resume after GitHub permits another request.

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

The v1 manual event is explicit and fail-closed:

```json
{
  "schema_version": 1,
  "mode": "published",
  "start_at": "2026-08-27T00:00:00Z",
  "end_at": "2026-08-28T00:00:00Z"
}
```

Unknown fields fail closed. Timestamps must use canonical UTC whole-second `Z` form.

The Lambda environment contains only non-secret configuration and the Secrets Manager secret identifier. Credential material remains exclusively in Secrets Manager.

## Validated source checkpoint

The final pre-apply focused checkpoint supplied on 2026-08-28 was green:

```text
61 passed
Ruff: All checks passed
Pyright strict: 0 errors / 0 warnings / 0 informations
```

The subsequent Terraform CI run also passed its static checks and Checkov security scan after the documented dev-only Secrets Manager rotation exception.

## Current immutable artifact evidence

The validated hardening source revision was packaged twice with identical SHA-256 and conditionally published to the versioned deployment-artifacts bucket:

```text
sha256=c4291b2adb51e84e2a91525b9a2bee1190579d6b984939032ae0b3f9746ee891
s3_key=lambda/ghsa-bronze/c4291b2adb51e84e2a91525b9a2bee1190579d6b984939032ae0b3f9746ee891.zip
s3_version_id=Jnq06HcNrjHDHibjhnOwboRbk.44grQh
source_code_hash=xCkbKttR6E4qkVJbmivuEZBXnWuYSTkDKuCz+XRu6JE=
content_length=17555589
content_type=application/zip
checksum_type=FULL_OBJECT
encryption=AES256
```

The previous `9deb08...` artifact remains immutable historical evidence for its earlier source revision only.

## Terraform and live runtime evidence

Terraform was repinned to the current artifact and a fresh reviewed plan contained exactly five creates and no changes or destroys. The resulting live `dev` runtime was verified with:

```text
Lambda: opslens-dev-ghsa-bronze
runtime: python3.13
architecture: x86_64
memory: 1024 MiB
timeout: 900 seconds
source_code_hash: xCkbKttR6E4qkVJbmivuEZBXnWuYSTkDKuCz+XRu6JE=
X-Ray: Active
logging: JSON / INFO
log retention: 14 days
secret stage: AWSCURRENT
```

The GitHub token value was populated out of band and never entered Terraform configuration or Terraform state.

## Manual runtime proof

The bounded published window `2026-08-27T00:00:00Z` through `2026-08-28T00:00:00Z` completed successfully:

```text
root_sync_id=1670a1e4730ba3e5a8214b7278d68b43fd8c929a069bae27099abd370cf9193e
attempt_id=e013864e669cc3b4f92766a94e9f487960bd4b3bf40247d523b8415a0d8aaa40
leaf_count=1
page_count=1
total_items=10
total_bytes=48899
manifest_version_id=IHt7S5Uvj21ABxWfPAPsXbnQhQW3ErRH
page_version_id=k1i1ppmalEBvDN9Dzrby5ocbdB.M8y2s
page_sha256=6ab59c9c875257d50693f9ce45ed4a24b55ae249abc567a21e34c84604f97470
```

The exact page bytes, size, item count, first GHSA ID, last GHSA ID, and COMPLETE manifest inventory were independently verified against the exact S3 VersionIds.

A second invocation of the same logical window returned the same `sync_id`, `attempt_id`, object keys, page VersionId, and manifest VersionId. `list-object-versions` showed exactly one physical version of `response.json` and one physical version of `manifest.json`, both latest, with no delete markers. The replay therefore created no duplicate S3 versions.

## Current gates

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
GHSA_BRONZE_LAMBDA_INVOCATION_CONTRACT_GATE=PASS
GHSA_BRONZE_PRE_APPLY_HARDENING_GATE=PASS
GHSA_BRONZE_LAMBDA_ARTIFACT_BUILD_GATE=PASS
GHSA_BRONZE_ARTIFACT_PUBLICATION_GATE=PASS
GHSA_BRONZE_TERRAFORM_GATE=PASS
GHSA_BRONZE_MANUAL_DEV_RUNTIME_GATE=PASS
GHSA_2_4C_GATE=PASS
```

## AWS / IAM / cost boundary

The deployed manual `dev` runtime remains intentionally minimal:

```text
Secrets Manager secret container
Lambda execution role
least-privilege GetSecretValue
least-privilege S3 Bronze read/write verification
CloudWatch log group
X-Ray write permissions
Lambda function pinned to content-addressed S3 artifact + exact VersionId
```

EventBridge Scheduler remains intentionally absent from Phase 2.4C. Manual synchronous execution was the required runtime proof; scheduling is not introduced merely to satisfy a platform pattern.

## Next step

Proceed to Phase 2.4D — GHSA Silver Runtime. Preserve the Phase 2.4B rule that vulnerable version ranges are stored as source evidence but concrete installed-version applicability is not evaluated until Phase 3.

## References

- `docs/adr/0005-ghsa-source-and-synchronization-strategy.md`
- `docs/adr/0006-ghsa-silver-content-versioning-and-physical-shape.md`
- `docs/adr/0007-ghsa-runtime-credential-and-retry-strategy.md`
- `docs/labs/phase-2-ghsa-runtime-security-design.md`
- `docs/labs/phase-2-ghsa-runtime-composition.md`
- `docs/labs/phase-2-ghsa-lambda-contract.md`
- `docs/labs/phase-2-ghsa-manual-dev-runtime.md`
