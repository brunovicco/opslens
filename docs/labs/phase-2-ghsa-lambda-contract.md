# Phase 2.4C — GHSA Bronze Lambda Invocation Contract

_Date: 2026-08-28_

_Status: COMPLETE_

## Purpose

Freeze and prove the manual AWS Lambda invocation boundary for GHSA Bronze while preserving the exact deployment identity required for the manual `dev` proof.

## Manual invocation contract

The v1 event is intentionally explicit and fail-closed:

```json
{
  "schema_version": 1,
  "mode": "published",
  "start_at": "2026-08-27T00:00:00Z",
  "end_at": "2026-08-28T00:00:00Z"
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

The authenticated source enforces a 120-second maximum per-retry wait budget. If GitHub requires a longer `Retry-After`, primary reset wait, or calculated secondary-limit backoff, the current fetch fails closed rather than sleeping into the Lambda timeout or retrying earlier than GitHub permits.

Strict continuation-query parsing failures are normalized to `InvalidGhsaRequestUrlError`, preserving the outbound domain boundary.

## Validated source checkpoint

After the pre-apply hardening changes, the focused local checkpoint was green:

```text
61 passed
Ruff: All checks passed
Pyright strict: 0 errors / 0 warnings / 0 informations
```

The Terraform CI security scan and static checks also passed after the explicit dev-only Secrets Manager rotation exception was documented.

## Current deployment artifact evidence

The deployable source revision was packaged deterministically twice and published under its content-addressed key:

```text
sha256=c4291b2adb51e84e2a91525b9a2bee1190579d6b984939032ae0b3f9746ee891
s3_key=lambda/ghsa-bronze/c4291b2adb51e84e2a91525b9a2bee1190579d6b984939032ae0b3f9746ee891.zip
s3_version_id=Jnq06HcNrjHDHibjhnOwboRbk.44grQh
source_code_hash=xCkbKttR6E4qkVJbmivuEZBXnWuYSTkDKuCz+XRu6JE=
content_length=17555589
```

The earlier `9deb08...` artifact remains immutable historical evidence for its previous source revision only.

## Deployment artifact boundary

`scripts/build_ghsa_bronze_lambda_package.py` creates a deterministic Python 3.13/x86_64 ZIP and reports:

```text
artifact path
artifact SHA-256
content-addressed key:
  lambda/ghsa-bronze/<sha256>.zip
```

Every deployable source revision must be pinned to:

```text
exact content-addressed S3 key
exact S3 VersionId
exact source_code_hash
```

No mutable filename-only deployment reference is allowed.

## Live Lambda evidence

The deployed function configuration was verified after apply:

```text
FunctionName=opslens-dev-ghsa-bronze
Runtime=python3.13
Handler=opslens.ingestion.ghsa.lambda_handler.lambda_handler
Architectures=[x86_64]
MemorySize=1024
Timeout=900
CodeSha256=xCkbKttR6E4qkVJbmivuEZBXnWuYSTkDKuCz+XRu6JE=
TracingConfig.Mode=Active
LoggingConfig.LogFormat=JSON
LoggingConfig.ApplicationLogLevel=INFO
LoggingConfig.SystemLogLevel=INFO
```

The runtime secret identifier points to the Terraform-managed Secrets Manager container. The secret value itself was populated out of band and is available under `AWSCURRENT`.

## Manual invocation proof

The bounded published window `2026-08-27T00:00:00Z` through `2026-08-28T00:00:00Z` returned:

```text
StatusCode=200
FunctionError=null
status=complete
root_sync_id=1670a1e4730ba3e5a8214b7278d68b43fd8c929a069bae27099abd370cf9193e
attempt_id=e013864e669cc3b4f92766a94e9f487960bd4b3bf40247d523b8415a0d8aaa40
leaf_count=1
page_count=1
total_items=10
total_bytes=48899
manifest_version_id=IHt7S5Uvj21ABxWfPAPsXbnQhQW3ErRH
```

The page referenced by the COMPLETE manifest was verified at exact S3 VersionId `k1i1ppmalEBvDN9Dzrby5ocbdB.M8y2s` with SHA-256 `6ab59c9c875257d50693f9ce45ed4a24b55ae249abc567a21e34c84604f97470` and size 48,899 bytes.

A second invocation of the same event returned the same logical and physical identities and the same manifest VersionId. S3 version listing proved that no additional page or manifest versions were created.

## Current gates

```text
GHSA_BRONZE_RUNTIME_COMPOSITION_GATE=PASS
GHSA_BRONZE_LAMBDA_INVOCATION_CONTRACT_GATE=PASS
GHSA_BRONZE_PRE_APPLY_HARDENING_GATE=PASS
GHSA_BRONZE_LAMBDA_ARTIFACT_BUILD_GATE=PASS
GHSA_BRONZE_ARTIFACT_PUBLICATION_GATE=PASS
GHSA_BRONZE_TERRAFORM_GATE=PASS
GHSA_BRONZE_MANUAL_DEV_RUNTIME_GATE=PASS
GHSA_2_4C_GATE=PASS
```

## Next step

Proceed to Phase 2.4D — GHSA Silver Runtime. The Lambda invocation contract remains frozen unless a later requirement explicitly changes the bounded runtime interface.

## References

- `docs/adr/0007-ghsa-runtime-credential-and-retry-strategy.md`
- `docs/labs/phase-2-ghsa-runtime-security-design.md`
- `docs/labs/phase-2-ghsa-manual-dev-runtime.md`
- AWS Lambda Python runtimes:
  https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html
- AWS Lambda timeout:
  https://docs.aws.amazon.com/lambda/latest/dg/configuration-timeout.html
- AWS Secrets Manager `GetSecretValue`:
  https://docs.aws.amazon.com/secretsmanager/latest/userguide/retrieving-secrets.html
- Amazon S3 conditional writes:
  https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html
- Lambda custom log groups:
  https://docs.aws.amazon.com/lambda/latest/dg/monitoring-cloudwatchlogs-loggroups.html
