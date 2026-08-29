# Phase 2.4C — GHSA Bronze Manual Dev Runtime

_Date: 2026-08-28_

_Status: COMPLETE_

## Purpose

Introduce and prove the minimum Terraform-managed AWS resources required for one manual GHSA Bronze Lambda invocation in `dev`.

EventBridge Scheduler remains intentionally absent from this increment. The manual synchronous path is the runtime proof boundary for Phase 2.4C.

## Validated source checkpoint

After the final pre-apply hardening changes, the focused local checkpoint was green:

```text
61 passed
Ruff: All checks passed
Pyright strict: 0 errors / 0 warnings / 0 informations
```

The Terraform CI static checks and Checkov security scan also passed after documenting the intentional dev-only Secrets Manager rotation exception.

## Deterministic artifact and publication evidence

The validated hardening source revision was packaged twice with identical SHA-256 and conditionally published to the existing versioned deployment-artifacts bucket using the content-addressed key.

```text
sha256=c4291b2adb51e84e2a91525b9a2bee1190579d6b984939032ae0b3f9746ee891
s3_key=lambda/ghsa-bronze/c4291b2adb51e84e2a91525b9a2bee1190579d6b984939032ae0b3f9746ee891.zip
s3_version_id=Jnq06HcNrjHDHibjhnOwboRbk.44grQh
checksum_sha256=xCkbKttR6E4qkVJbmivuEZBXnWuYSTkDKuCz+XRu6JE=
content_length=17555589
content_type=application/zip
encryption=AES256
checksum_type=FULL_OBJECT
metadata.artifact=opslens-ghsa-bronze
metadata.sha256=c4291b2adb51e84e2a91525b9a2bee1190579d6b984939032ae0b3f9746ee891
```

The exact version-specific `HeadObject` verification matched the expected VersionId, full-object checksum, content length, content type, encryption, and deterministic metadata.

The previous `9deb08...` artifact remains historical immutable evidence for its earlier source revision only.

## Terraform plan and apply evidence

Terraform was repinned to the exact current artifact identity and the reviewed plan contained:

```text
Plan: 5 to add, 0 to change, 0 to destroy.
```

The planned resources were limited to:

```text
aws_secretsmanager_secret.ghsa_github_token
aws_iam_role.ghsa_bronze_lambda
aws_iam_role_policy.ghsa_bronze_lambda_runtime
aws_cloudwatch_log_group.ghsa_bronze
aws_lambda_function.ghsa_bronze
```

The live resources were subsequently verified in AWS, proving that the reviewed Terraform path was applied successfully.

## Terraform resources

This increment manages only:

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

## Live Lambda configuration

The deployed function was verified as:

```text
FunctionName=opslens-dev-ghsa-bronze
Runtime=python3.13
Handler=opslens.ingestion.ghsa.lambda_handler.lambda_handler
Architectures=[x86_64]
MemorySize=1024
Timeout=900
CodeSha256=xCkbKttR6E4qkVJbmivuEZBXnWuYSTkDKuCz+XRu6JE=
Role=OpsLensGhsaBronzeLambdaRole
TracingConfig.Mode=Active
LoggingConfig.LogFormat=JSON
LoggingConfig.ApplicationLogLevel=INFO
LoggingConfig.SystemLogLevel=INFO
LogGroup=/aws/lambda/opslens-dev-ghsa-bronze
LogRetention=14 days
```

The Lambda environment contains only the expected non-secret runtime configuration and the Secrets Manager secret identifier.

## Credential provisioning evidence

The Terraform-managed Secrets Manager container was verified before credential insertion. The GitHub fine-grained token was then populated out of band and the resulting secret version was assigned `AWSCURRENT`.

The local temporary token file and shell variable were explicitly removed after provisioning. The token value was never printed, committed, placed in Terraform, or returned through the Lambda response.

Automatic Secrets Manager rotation is intentionally deferred for this dev-only external GitHub credential. The Checkov exception is documented on the Terraform resource, and the token uses a bounded GitHub-side expiration.

## Manual invocation proof

The first bounded invocation used:

```json
{
  "schema_version": 1,
  "mode": "published",
  "start_at": "2026-08-27T00:00:00Z",
  "end_at": "2026-08-28T00:00:00Z"
}
```

The Lambda returned:

```text
StatusCode=200
FunctionError=null
status=complete
root_sync_id=1670a1e4730ba3e5a8214b7278d68b43fd8c929a069bae27099abd370cf9193e
leaf_count=1
total_items=10
total_bytes=48899
```

The single leaf returned:

```text
sync_id=1670a1e4730ba3e5a8214b7278d68b43fd8c929a069bae27099abd370cf9193e
attempt_id=e013864e669cc3b4f92766a94e9f487960bd4b3bf40247d523b8415a0d8aaa40
page_count=1
total_items=10
total_bytes=48899
manifest_version_id=IHt7S5Uvj21ABxWfPAPsXbnQhQW3ErRH
```

## COMPLETE manifest evidence

The exact manifest VersionId returned by the Lambda was independently retrieved from S3.

Its metadata and body proved:

```text
completion_status=complete
manifest_version=1
mode=published
page_count=1
total_items=10
total_bytes=48899
sync_id=1670a1e4730ba3e5a8214b7278d68b43fd8c929a069bae27099abd370cf9193e
attempt_id=e013864e669cc3b4f92766a94e9f487960bd4b3bf40247d523b8415a0d8aaa40
```

The manifest inventory referenced exactly one page:

```text
page=000001/response.json
version_id=k1i1ppmalEBvDN9Dzrby5ocbdB.M8y2s
sha256=6ab59c9c875257d50693f9ce45ed4a24b55ae249abc567a21e34c84604f97470
size_bytes=48899
item_count=10
first_ghsa_id=GHSA-gvrw-qqp5-jgc5
last_ghsa_id=GHSA-vxj7-4xrp-5vr4
next_url=null
```

## Exact page evidence

The page was retrieved using the exact S3 VersionId from the manifest.

Verification produced:

```text
actual_sha256=6ab59c9c875257d50693f9ce45ed4a24b55ae249abc567a21e34c84604f97470
actual_bytes=48899
PAGE_SHA256=PASS
PAGE_SIZE=PASS
json_type=list
item_count=10
first_ghsa_id=GHSA-gvrw-qqp5-jgc5
last_ghsa_id=GHSA-vxj7-4xrp-5vr4
```

## Deterministic replay proof

A second invocation of the same event returned the same:

```text
root_sync_id
sync_id
attempt_id
page_count
total_items
total_bytes
manifest_key
manifest_version_id
```

The new Lambda `request_id` differed, as expected for a separate invocation.

`list-object-versions` under the exact attempt prefix then showed only:

```text
manifest.json
  VersionId=IHt7S5Uvj21ABxWfPAPsXbnQhQW3ErRH
  IsLatest=true
  Size=1189

page=000001/response.json
  VersionId=k1i1ppmalEBvDN9Dzrby5ocbdB.M8y2s
  IsLatest=true
  Size=48899
```

No `DeleteMarkers` existed. Therefore the replay reused the immutable evidence and did not create duplicate physical S3 versions.

## Security boundary

The initial secret uses the AWS-managed `aws/secretsmanager` KMS key accepted by ADR-0007. Because it is not a customer-managed key, the Lambda execution role does not need an explicit `kms:Decrypt` permission.

The function is intentionally not placed in a VPC because it requires outbound access to the public GitHub API and no private VPC resource. Adding a VPC at this stage would introduce NAT/network cost and complexity without reducing the defined threat surface.

Reserved concurrency remains deferred for the manual-only proof path because the dev account has previously constrained concurrency quota headroom.

No EventBridge Scheduler exists in this increment.

## Current gates

```text
GHSA_BRONZE_REQUEST_URL_ALLOWLIST_GATE=PASS
GHSA_BRONZE_AUTHENTICATED_HTTP_GATE=PASS
GHSA_BRONZE_RATE_LIMIT_GATE=PASS
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

Proceed to Phase 2.4D — GHSA Silver Runtime. Do not introduce concrete installed-version applicability logic; vulnerable ranges remain source evidence until the deterministic Phase 3 correlation engine.

## References

- `docs/adr/0007-ghsa-runtime-credential-and-retry-strategy.md`
- AWS Lambda Python runtimes:
  https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html
- AWS Lambda timeout:
  https://docs.aws.amazon.com/lambda/latest/dg/configuration-timeout.html
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
