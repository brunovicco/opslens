# Phase 2.3G — Permanent NVD Analytics Artifact Build

Status: **COMPLETE**

This checkpoint implements and proves Phase 2.3G.4G: one immutable permanent NVD analytics projector artifact, exact S3 version pinning, bounded deployment authority, permanent dev runtime deployment, independent AWS read-back, zero-work smoke execution, and post-apply no-drift verification.

## Objective

Produce one immutable Lambda deployment package for the permanent NVD analytics projector, prove the package is deterministic, upload it under a content-addressed S3 key, pin the exact S3 VersionId and SHA-256 in Terraform, deploy only the reviewed runtime/catalog blast radius, and independently prove the deployed runtime matches the repository contract.

The deployment package is built by:

```text
scripts/build_nvd_analytics_projector_lambda_package.py
```

The generated artifact is:

```text
dist/opslens-nvd-analytics-projector.zip
```

Its permanent deployment key is content-addressed:

```text
lambda/nvd-analytics-projector/<artifact-sha256>.zip
```

## Build contract

The builder follows the same deterministic ZIP strategy used by the existing NVD runtimes:

- clean staging directory on every run;
- locked `uv` dependency export;
- Linux x86_64 Python 3.13 wheels;
- stable ZIP ordering;
- fixed ZIP timestamp;
- normalized POSIX permissions;
- removal of unrelated Lambda entrypoints;
- required runtime-file validation;
- Lambda uncompressed-size guard;
- SHA-256 in hexadecimal and Lambda-compatible base64 forms.

The analytics runtime currently imports the frozen NVD Silver schema and writer-contract modules while validating COMPLETE evidence. Those modules import PyArrow at module load time, so the package intentionally reuses the locked `nvd-silver-runtime` dependency group until those constants are separated into a lightweight contract module.

## Determinism gate — COMPLETE

Two consecutive builds from commit `c2b41f3` produced byte-identical deployment evidence:

```text
artifact_s3_key=lambda/nvd-analytics-projector/6ae0bf3909744d6bb5e61390885fc469c18b93ef383bd4c2380fdc874de159cf.zip
sha256=6ae0bf3909744d6bb5e61390885fc469c18b93ef383bd4c2380fdc874de159cf
sha256_base64=auC/OQl0TWu15hOQiF/EacGLk+84O9TCOA/ch03hWc8=
files=3515
compressed_bytes=67502125
uncompressed_bytes=184846905
compressed_mib=64.38
uncompressed_mib=176.28
unzipped_limit_percent=70.51
requires_s3_upload=true
```

The selected determinism fields produced an empty `diff`, and an independent local `shasum -a 256` over `dist/opslens-nvd-analytics-projector.zip` returned the same SHA-256:

```text
6ae0bf3909744d6bb5e61390885fc469c18b93ef383bd4c2380fdc874de159cf
```

`git status --short` remained empty after both builds because local build artifacts are ignored.

## Exact versioned S3 upload proof — COMPLETE

Bucket versioning was verified as enabled before upload. The content-addressed object did not exist before the write (`HeadObject` returned `404 Not Found`), so the upload created the first immutable version at that key.

Exact persisted coordinates:

```text
bucket=opslens-dev-artifacts-487757851499-us-east-1
key=lambda/nvd-analytics-projector/6ae0bf3909744d6bb5e61390885fc469c18b93ef383bd4c2380fdc874de159cf.zip
VersionId=rmQLrC.FQamigSqqAsYt1gOKuMyCjdle
ETag="4dc8f4f37a2dd295c01774946c1ddfd6"
ContentLength=67502125
ContentType=application/zip
ServerSideEncryption=AES256
ChecksumSHA256=auC/OQl0TWu15hOQiF/EacGLk+84O9TCOA/ch03hWc8=
metadata.sha256=6ae0bf3909744d6bb5e61390885fc469c18b93ef383bd4c2380fdc874de159cf
```

An exact-version `GetObject` using that VersionId returned the same checksum, content length, ETag, encryption mode, content type, and metadata. The downloaded exact version was independently checked with `shasum -a 256`, which returned the same SHA-256, and `cmp` against the local deterministic artifact returned `0`.

Therefore:

```text
local deterministic ZIP
  == SHA-256 6ae0bf3909744d6bb5e61390885fc469c18b93ef383bd4c2380fdc874de159cf
  == exact S3 VersionId rmQLrC.FQamigSqqAsYt1gOKuMyCjdle
  == exact downloaded bytes
```

## Terraform pinning gate — COMPLETE

The exact artifact identity is pinned directly in repository-controlled Terraform locals:

```text
sha256=6ae0bf3909744d6bb5e61390885fc469c18b93ef383bd4c2380fdc874de159cf
sha256_base64=auC/OQl0TWu15hOQiF/EacGLk+84O9TCOA/ch03hWc8=
VersionId=rmQLrC.FQamigSqqAsYt1gOKuMyCjdle
```

The temporary operator-supplied artifact variables and example tfvars file were removed after exact upload proof, so routine Terraform plan/apply cannot silently select a different current object through an external variable override.

## Bootstrap deployment authority — COMPLETE

After repository formatting was corrected, the bootstrap plan was regenerated from the current branch and reviewed before apply.

```text
Plan: 2 to add, 1 to change, 0 to destroy.
```

The existing `OpsLensAnalyticsDevAccess` policy was updated in place to add management of the exact Glue table `opslens_dev.nvd_cve_versions`. A dedicated `OpsLensGitHubNvdAnalyticsProjectorDeploy` policy was created and attached to `OpsLensGitHubDeployRole` for the projector's exact Lambda, execution role, SQS failure queue, and log group resources.

The exact saved bootstrap plan was applied successfully:

```text
Apply complete! Resources: 2 added, 1 changed, 0 destroyed.
```

No bootstrap resource was destroyed.

## Dev runtime deployment — COMPLETE

The reviewed dev plan contained only the selected permanent analytics runtime resources:

```text
Plan: 8 to add, 1 to change, 0 to destroy.
```

The plan created the projector CloudWatch log group, Glue `nvd_cve_versions` table, Lambda execution role and inline runtime policy, Lambda function, asynchronous invoke configuration, S3 invoke permission, and SQS OnFailure queue. The existing single data-bucket notification resource was updated in place only to add the NVD watermark trigger while preserving the existing notifications.

The exact saved dev plan was applied successfully:

```text
Apply complete! Resources: 8 added, 1 changed, 0 destroyed.
```

Terraform outputs exposed:

```text
nvd_analytics_projector_lambda_execution_role_arn=arn:aws:iam::487757851499:role/OpsLensNvdAnalyticsProjectorLambdaRole
nvd_analytics_projector_lambda_function_arn=arn:aws:lambda:us-east-1:487757851499:function:opslens-dev-nvd-analytics-projector
```

No dev resource was destroyed.

## Independent deployed AWS verification — COMPLETE

### Lambda configuration and exact artifact identity

AWS read-back returned:

```text
FunctionName=opslens-dev-nvd-analytics-projector
Runtime=python3.13
Handler=opslens.transformation.nvd.analytics_projection_lambda_handler.lambda_handler
CodeSha256=auC/OQl0TWu15hOQiF/EacGLk+84O9TCOA/ch03hWc8=
CodeSize=67502125
MemorySize=1024
Timeout=120
Role=arn:aws:iam::487757851499:role/OpsLensNvdAnalyticsProjectorLambdaRole
Architectures=[x86_64]
Tracing=Active
LogFormat=JSON
LogGroup=/aws/lambda/opslens-dev-nvd-analytics-projector
NvdDataBucket=opslens-dev-data-487757851499-us-east-1
State=Active
LastUpdateStatus=Successful
```

Terraform state independently retained the exact immutable deployment coordinates:

```text
s3_bucket=opslens-dev-artifacts-487757851499-us-east-1
s3_key=lambda/nvd-analytics-projector/6ae0bf3909744d6bb5e61390885fc469c18b93ef383bd4c2380fdc874de159cf.zip
s3_object_version=rmQLrC.FQamigSqqAsYt1gOKuMyCjdle
source_code_hash=auC/OQl0TWu15hOQiF/EacGLk+84O9TCOA/ch03hWc8=
```

### Runtime IAM

The deployed inline runtime policy exposed only:

```text
logs:CreateLogStream
logs:PutLogEvents
s3:GetObject
s3:GetObjectVersion
s3:PutObject
sqs:SendMessage
xray:PutTelemetryRecords
xray:PutTraceSegments
```

The explicit forbidden-action check returned:

```text
forbidden_present: []
```

Therefore the runtime still excludes `s3:ListBucket`, S3 delete operations, and Glue partition mutation.

### Failure handling and eventing

The deployed asynchronous invoke configuration returned:

```text
MaximumEventAgeInSeconds=3600
MaximumRetryAttempts=2
OnFailure=arn:aws:sqs:us-east-1:487757851499:opslens-dev-nvd-analytics-projector-failures
```

The data bucket notification read-back contained exactly six Lambda configurations. The new projector notification was:

```text
Id=nvd-analytics-projector-watermark-created
LambdaFunctionArn=arn:aws:lambda:us-east-1:487757851499:function:opslens-dev-nvd-analytics-projector
Event=s3:ObjectCreated:Put
Prefix=control/nvd/cve/incremental/
Suffix=watermark.json
```

The existing five Lambda notification blocks remained present.

### Permanent Glue catalog

Glue read-back returned:

```text
Name=nvd_cve_versions
Type=EXTERNAL_TABLE
Location=s3://opslens-dev-data-487757851499-us-east-1/analytics/nvd/cve/schema_version=1/
ColumnCount=32
PartitionKeys=[source_kind_partition, projection_date]
projection.enabled=true
projection.source_kind_partition.type=enum
projection.source_kind_partition.values=bootstrap,incremental
projection.projection_date.type=date
projection.projection_date.range=2026-01-01,NOW
```

No crawler or runtime Glue partition registration is required.

### CloudWatch and zero-work smoke

The projector log group exists with 14-day retention:

```text
/aws/lambda/opslens-dev-nvd-analytics-projector
Retention=14
```

An initial smoke attempt from a restored shell failed locally before reaching AWS because `AWS_REGION` was empty, yielding `Invalid endpoint: https://lambda..amazonaws.com`. After restoring the explicit region/profile environment, the exact same S3 test invocation succeeded:

```text
StatusCode=200
ExecutedVersion=$LATEST
```

Lambda response:

```json
{"status":"s3_test_event","processed_records":0,"bucket":"opslens-dev-data-487757851499-us-east-1","s3_request_id":"opslens-2.3G.4G-smoke"}
```

This S3 test path returns before projection runtime initialization, so it proved package import, handler wiring, Powertools integration, and Lambda execution without reading authoritative watermark evidence or writing analytics Parquet.

### Post-apply no-drift proof

A fresh remote-state Terraform plan after the independent AWS read-backs returned:

```text
No changes. Your infrastructure matches the configuration.
```

The deployed infrastructure therefore matches the repository configuration after the permanent runtime deployment.

## 2.3G.4G gate state

```text
NVD_2_3G_4G_DETERMINISTIC_BUILD=PASS
NVD_2_3G_4G_ARTIFACT_EXACT_VERSION=PASS
NVD_2_3G_4G_ARTIFACT_PIN=PASS
NVD_2_3G_4G_BOOTSTRAP_DEPLOY_AUTHORITY=PASS
NVD_2_3G_4G_DEV_PLAN=PASS
NVD_2_3G_4G_DEV_APPLY=PASS
NVD_2_3G_4G_LAMBDA_READBACK=PASS
NVD_2_3G_4G_RUNTIME_IAM=PASS
NVD_2_3G_4G_FAILURE_DESTINATION=PASS
NVD_2_3G_4G_S3_EVENTING=PASS
NVD_2_3G_4G_GLUE_CATALOG=PASS
NVD_2_3G_4G_SMOKE=PASS
NVD_2_3G_4G_NO_DRIFT=PASS
NVD_2_3G_4G=COMPLETE
```

## Next boundary

Phase 2.3G.4H may now perform the explicit historical Bootstrap seed using only the already-proven exact Silver COMPLETE key and VersionId. No prefix discovery is required or authorized.

```text
exact Bootstrap COMPLETE key + VersionId
    -> explicit bootstrap_seed Lambda invocation
    -> exact COMPLETE validation
    -> exact source Parquet VersionId/SHA validation
    -> deterministic append-only analytics destination
    -> exact destination VersionId/SHA/metadata verification
    -> replay invocation must return already_projected only after exact current-destination verification
```
