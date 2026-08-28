# Phase 2.4C — GHSA Bronze Lambda Invocation Contract

_Date: 2026-08-28_

_Status: IN PROGRESS_

## Purpose

Freeze the manual AWS Lambda invocation boundary for GHSA Bronze before creating any new AWS resource.

The runtime composition gate is locally green:

```text
51 passed
Ruff: all checks passed
Pyright strict: 0 errors / 0 warnings / 0 informations
```

Therefore:

```text
GHSA_BRONZE_RUNTIME_COMPOSITION_GATE=PASS
```

## Manual invocation contract

The v1 event is intentionally explicit and fail-closed:

```json
{
  "schema_version": 1,
  "mode": "published",
  "start_at": "2026-08-01T00:00:00Z",
  "end_at": "2026-08-02T00:00:00Z"
}
```

Allowed fields are exactly:

```text
schema_version
mode
start_at
end_at
```

Unknown fields fail closed. `schema_version` must equal `1`. `mode` must be `published` or `modified`. Timestamps must use UTC whole-second `YYYY-MM-DDTHH:MM:SSZ` form and still satisfy `GhsaSyncWindow` bounds.

The invocation carries no GitHub token, S3 key, retry count, attempt identifier, AWS request identifier, or scheduler-specific field.

## Response contract

A successful manual invocation returns:

```text
request_id
status=complete
schema_version
mode
root_sync_id
window_start_at
window_end_at
leaf_count
total_items
total_bytes
leaves[]:
  sync_id
  attempt_id
  page_count
  total_items
  total_bytes
  manifest_key
  manifest_version_id
```

The response exposes COMPLETE evidence only. Credentials, Authorization headers, raw source headers, and secret values are never serialized.

## Environment contract

The Lambda composition root reads only non-secret runtime configuration:

```text
GHSA_DATA_BUCKET                    required
GHSA_GITHUB_TOKEN_SECRET_ID         required
GHSA_BRONZE_PREFIX                  default bronze/ghsa/advisories
GHSA_HTTP_TIMEOUT_SECONDS           default 15
GHSA_HTTP_MAX_ATTEMPTS              default 3
GHSA_SECRET_CACHE_TTL_SECONDS       default 300
GHSA_MAX_LEAF_WINDOWS               default 64
```

`GHSA_GITHUB_TOKEN_SECRET_ID` is only the secret identifier. The GitHub token itself remains in AWS Secrets Manager and is retrieved through `GetSecretValue` at runtime.

## Runtime composition

The Lambda path is:

```text
manual event
  -> GhsaBronzeInvocationParserV1
  -> GhsaSyncWindow
  -> lazily initialized runtime
  -> Secrets Manager token provider
  -> authenticated GitHub source
  -> bounded cursor traversal
  -> deterministic attempt_id
  -> immutable versioned S3 pages
  -> COMPLETE manifest
  -> versioned manifest evidence response
```

## Deployment artifact boundary

`scripts/build_ghsa_bronze_lambda_package.py` creates a deterministic Python 3.13/x86_64 ZIP and reports:

```text
artifact path
artifact SHA-256
content-addressed key:
  lambda/ghsa-bronze/<sha256>.zip
```

The next deployment increment must upload that exact artifact to the existing versioned deployment bucket and pin Terraform to:

```text
exact content-addressed S3 key
exact S3 VersionId
exact source_code_hash
```

No mutable filename-only deployment reference is allowed.

## AWS validation before infrastructure

Official AWS documentation was rechecked on 2026-08-28:

- Python 3.13 remains a supported Lambda runtime on Amazon Linux 2023.
- Secrets Manager `GetSecretValue` requires `secretsmanager:GetSecretValue`.
- S3 `If-None-Match: *` prevents overwriting an existing current object and returns `412 Precondition Failed` when the current key exists.
- Custom Lambda log groups require execution-role permissions such as `logs:PutLogEvents`.

References:

- https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html
- https://docs.aws.amazon.com/secretsmanager/latest/userguide/retrieving-secrets.html
- https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html
- https://docs.aws.amazon.com/lambda/latest/dg/monitoring-cloudwatchlogs-loggroups.html

## Current gates

```text
GHSA_BRONZE_RUNTIME_COMPOSITION_GATE=PASS
GHSA_BRONZE_LAMBDA_INVOCATION_CONTRACT_GATE=PASS_PENDING_LOCAL_VALIDATION
GHSA_BRONZE_LAMBDA_ARTIFACT_BUILD_GATE=PASS_PENDING_LOCAL_VALIDATION
GHSA_BRONZE_TERRAFORM_GATE=PENDING
GHSA_2_4C_GATE=IN_PROGRESS
```

## Next step

Run the focused GHSA unit-test, Ruff, and strict Pyright checkpoint. If green, build the deterministic artifact locally and capture its exact SHA-256 before any Terraform Lambda resource is added.
