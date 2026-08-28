# Phase 2.4C — GHSA Bronze Manual Dev Runtime

_Date: 2026-08-28_

_Status: IN PROGRESS_

## Purpose

Introduce the minimum Terraform-managed AWS resources required to prove one manual GHSA Bronze Lambda invocation in `dev`.

EventBridge Scheduler remains intentionally deferred until the synchronous manual path is proven.

## Prerequisite evidence

The local Lambda contract checkpoint is green:

```text
57 passed
Ruff: All checks passed
Pyright strict: 0 errors / 0 warnings / 0 informations
```

The deterministic artifact was built and published with exact immutable evidence:

```text
sha256=9deb08f346cbe7261199568de8a515b26b2865d7f6d2a592d837a0ac0368c928
s3_key=lambda/ghsa-bronze/9deb08f346cbe7261199568de8a515b26b2865d7f6d2a592d837a0ac0368c928.zip
s3_version_id=fYDkvIkv15n.GHoGCgOQbgcuFObO_P3w
checksum_sha256=nesI80bL5yYRmVaN6KUVsmsoZdf20qWS2DegrANoySg=
content_length=17555239
content_type=application/zip
encryption=AES256
checksum_type=FULL_OBJECT
```

Therefore:

```text
GHSA_BRONZE_ARTIFACT_PUBLICATION_GATE=PASS
```

## Terraform resources

This increment adds only:

```text
AWS Secrets Manager secret container
GHSA Lambda execution role + inline least-privilege policy
CloudWatch log group
GHSA Bronze Lambda function
```

The secret container is Terraform-managed, but the GitHub token value is not. No `aws_secretsmanager_secret_version` resource exists, so plaintext credential material does not enter Terraform configuration or Terraform state through this project.

The secret name is:

```text
opslens/dev/ghsa/github-token
```

The Lambda execution role receives only:

```text
secretsmanager:GetSecretValue
  -> exact GHSA secret ARN

s3:GetObject
s3:PutObject
  -> exact data-lake prefix bronze/ghsa/advisories/*

logs:CreateLogStream
logs:PutLogEvents
  -> exact Lambda log group

xray:PutTelemetryRecords
xray:PutTraceSegments
  -> required X-Ray write scope
```

No artifact-bucket read permission is added to the execution role because deployment-package retrieval is a deployment concern, not a runtime application permission.

## Lambda deployment identity

Terraform pins all three immutable artifact coordinates:

```text
S3 key
S3 VersionId
source_code_hash
```

The runtime remains Python 3.13 on x86_64.

The Lambda uses 1024 MiB memory because the application may buffer up to 64 MiB of exact response bytes plus parsed advisory models before persistence. The timeout is 900 seconds for this manual proof path.

## Runtime environment

Only non-secret configuration and the Secrets Manager identifier are exposed as environment variables:

```text
GHSA_DATA_BUCKET
GHSA_GITHUB_TOKEN_SECRET_ID
GHSA_BRONZE_PREFIX
GHSA_HTTP_TIMEOUT_SECONDS
GHSA_HTTP_MAX_ATTEMPTS
GHSA_SECRET_CACHE_TTL_SECONDS
GHSA_MAX_LEAF_WINDOWS
```

The token value remains exclusively in Secrets Manager and is retrieved with `AWSCURRENT` at runtime.

## Security boundary

The initial secret uses the AWS-managed `aws/secretsmanager` KMS key accepted by ADR-0007. Because it is not a customer-managed key, the Lambda execution role does not need an explicit `kms:Decrypt` permission.

The function is intentionally not placed in a VPC because it requires outbound access to the public GitHub API and no private VPC resource. Adding a VPC at this stage would introduce NAT/network cost and complexity without reducing the defined threat surface.

Reserved concurrency remains deferred for the manual-only proof path because the dev account has previously constrained concurrency quota headroom. No scheduler exists in this increment.

## Current gates

```text
GHSA_BRONZE_RUNTIME_COMPOSITION_GATE=PASS
GHSA_BRONZE_LAMBDA_INVOCATION_CONTRACT_GATE=PASS
GHSA_BRONZE_LAMBDA_ARTIFACT_BUILD_GATE=PASS
GHSA_BRONZE_ARTIFACT_PUBLICATION_GATE=PASS
GHSA_BRONZE_TERRAFORM_GATE=PASS_PENDING_LOCAL_VALIDATION
GHSA_BRONZE_MANUAL_DEV_RUNTIME_GATE=PENDING
GHSA_2_4C_GATE=IN_PROGRESS
```

## Required validation before apply

Run:

```text
terraform fmt -check
terraform validate
terraform plan
```

Do not apply until the plan has been reviewed for exactly the intended GHSA resources and no destructive or unrelated changes.

After a clean apply, populate the GitHub token out of band, invoke one explicit bounded window manually, and verify the returned COMPLETE manifest VersionId plus the exact Bronze objects before closing Phase 2.4C.

## References

- `docs/adr/0007-ghsa-runtime-credential-and-retry-strategy.md`
- AWS Lambda Python runtimes:
  https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html
- AWS Lambda FunctionCode:
  https://docs.aws.amazon.com/lambda/latest/api/API_FunctionCode.html
- AWS Secrets Manager GetSecretValue:
  https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
- AWS Secrets Manager IAM examples:
  https://docs.aws.amazon.com/secretsmanager/latest/userguide/auth-and-access_iam-policies.html
- HashiCorp AWS provider `aws_lambda_function`:
  https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lambda_function
- HashiCorp AWS provider `aws_secretsmanager_secret`:
  https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/secretsmanager_secret
