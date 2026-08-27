# Legacy Lambda artifact lifecycle migration

Status: **COMPLETE**

## Objective

Remove the remaining local-build artifact lifecycle drift for the legacy OpsLens ingestion Lambdas without changing their data-plane behavior.

The affected functions were:

```text
opslens-dev-epss-ingestion
opslens-dev-kev-ingestion
opslens-dev-nvd-bootstrap-ingestion
```

They now use the immutable deployment pattern already proven by the newer OpsLens runtimes:

```text
deterministic build
    -> SHA-256
    -> content-addressed S3 key
    -> exact S3 VersionId
    -> Terraform immutable pin
```

## Why this migration existed

The final Phase 2.3G convergence review found a clean Bootstrap Terraform plan but a non-zero dev plan caused by the legacy ingestion Lambda code hashes.

Those functions still used local build outputs directly:

```hcl
filename         = <local dist ZIP>
source_code_hash = filebase64sha256(<local dist ZIP>)
```

That meant rebuilding a ZIP locally could redefine Terraform's view of deployed infrastructure even when no intended deployment change existed.

The permanent model now binds Terraform to an exact artifact already stored in the versioned deployment bucket:

```hcl
s3_bucket         = <deployment artifact bucket>
s3_key            = "lambda/<runtime>/<sha256>.zip"
s3_object_version = <exact S3 VersionId>
source_code_hash  = <base64 SHA-256>
```

## NVD Bootstrap package-boundary correction

The NVD Bootstrap builder historically copied the complete `opslens.ingestion.nvd` package. Later incremental-ingestion and authoritative-watermark code was added under that package, so unrelated source changes could alter the Bootstrap ZIP hash.

The Bootstrap artifact is now built from an explicit runtime source set containing only:

- Bootstrap Lambda handler and configuration;
- Bootstrap composition root;
- yearly-feed HTTP and S3 Bronze adapters;
- Bootstrap application contracts and service;
- yearly-feed domain models, META parsing, integrity verification, and source identity;
- shared observability required by the runtime.

Incremental and authoritative-watermark modules remain outside the Bootstrap artifact.

## Deployment-bucket retention correction

The shared deployment bucket previously expired current objects under `lambda/` after 90 days and noncurrent versions after 30 days.

That lifecycle was incompatible with Terraform resources that pin a content-addressed key and exact S3 VersionId because a valid deployment coordinate could disappear merely due to age.

The deployed lifecycle contract is now:

```text
current content-addressed Lambda object -> retained
noncurrent Lambda object version         -> eligible for cleanup after 30 days
incomplete multipart upload              -> abort after 7 days
```

Content-addressed uploads are write-once and use conditional creation so the same hash key is not intentionally overwritten.

## Scope

In scope:

```text
scripts/build_nvd_lambda_package.py
infra/environments/dev/artifacts.tf
infra/environments/dev/lambda.tf
infra/environments/dev/kev_lambda.tf
infra/environments/dev/nvd_bootstrap_lambda.tf
content-addressed uploads for the three legacy ingestion artifacts
exact Terraform artifact pins
AWS readback
full Terraform convergence proof
```

Out of scope:

```text
application behavior changes
runtime IAM widening
scheduler behavior changes
data-model changes
EPSS Silver artifact migration
KEV Silver artifact migration
NVD Silver / Incremental / Promotion / Analytics code-artifact migration
GHSA ingestion
Phase 3
```

## Gate A — package boundary — COMPLETE

NVD Bootstrap was built with the explicit runtime source set and checked against required and forbidden members.

Proof:

```text
LEGACY_ARTIFACT_NVD_BOOTSTRAP_BOUNDARY=PASS
```

Examples confirmed absent from the Bootstrap ZIP included:

```text
opslens/ingestion/nvd/incremental_lambda_handler.py
opslens/ingestion/nvd/incremental_runtime_composition.py
opslens/ingestion/nvd/incremental_runtime_config.py
opslens/ingestion/nvd/application/authoritative_watermark.py
opslens/ingestion/nvd/application/incremental_service.py
opslens/ingestion/nvd/domain/api_page.py
opslens/ingestion/nvd/domain/incremental.py
opslens/ingestion/nvd/adapters/outbound/nvd_cve_api.py
opslens/ingestion/nvd/adapters/outbound/s3_authoritative_watermark.py
opslens/ingestion/nvd/adapters/outbound/s3_incremental_bronze.py
```

## Gate B — deterministic artifacts — COMPLETE

Each affected package was built twice from the same repository state and compared by SHA-256, size, and byte equality.

EPSS ingestion:

```text
sha256=6eee3ca9297b4f393afed6d15c28de39a684c05b64bdbb02d8916edb2f04d348
sha256_base64=bu48qSl7Tzk6/tbRXCjeOaaEwFtkvbsC2JFu2y8E00g=
bytes=17538328
LEGACY_ARTIFACT_EPSS_DETERMINISTIC=PASS
```

KEV ingestion:

```text
sha256=8c443677bfe292b6d8b99520b473e7318836dfad65e4a014c1b86cfce3044ef6
sha256_base64=jEQ2d7/ikrbYuZUgtHPnMYg2361l5KAUwbhs/OMETvY=
bytes=17538806
LEGACY_ARTIFACT_KEV_DETERMINISTIC=PASS
```

NVD Bootstrap ingestion:

```text
sha256=4baa4ddc3a3d841eb9c0ca77fe10a8796dcd9bd1a444df8b06ad5a55f23db74e
sha256_base64=S6pN3Do9hB65wMp3/hCoeW3Nm9GkRN+LBq1aVfI9t04=
bytes=17546498
LEGACY_ARTIFACT_NVD_BOOTSTRAP_DETERMINISTIC=PASS
```

## Gate C0 — durable deployment-artifact retention — COMPLETE

The targeted Terraform plan proposed exactly one in-place lifecycle change:

```text
Plan: 0 to add, 1 to change, 0 to destroy.
```

The exact saved plan was applied:

```text
Apply complete! Resources: 0 added, 1 changed, 0 destroyed.
```

AWS lifecycle readback proved:

```text
abort-incomplete-multipart-uploads:
  status=Enabled
  DaysAfterInitiation=7

cleanup-noncurrent-lambda-deployment-artifacts:
  status=Enabled
  prefix=lambda/
  NoncurrentDays=30
  Expiration=<absent>
```

Proof:

```text
LEGACY_ARTIFACT_DEPLOYMENT_RETENTION=PASS
```

## Gate C — immutable exact-version uploads — COMPLETE

All three exact ZIPs were proven absent at their content-addressed keys before upload. They were then written with `If-None-Match: *`, SHA-256 object checksums, `application/zip`, SHA-256 metadata, and S3 versioning enabled.

EPSS ingestion:

```text
bucket=opslens-dev-artifacts-487757851499-us-east-1
key=lambda/epss-ingestion/6eee3ca9297b4f393afed6d15c28de39a684c05b64bdbb02d8916edb2f04d348.zip
VersionId=dlTZxO6udUaRhUQMT1YytkOKrETL.1EC
ETag="be60f94e97288fb4f2f9b2bbbdec453e"
ContentLength=17538328
ChecksumSHA256=bu48qSl7Tzk6/tbRXCjeOaaEwFtkvbsC2JFu2y8E00g=
metadata.sha256=6eee3ca9297b4f393afed6d15c28de39a684c05b64bdbb02d8916edb2f04d348
```

KEV ingestion:

```text
bucket=opslens-dev-artifacts-487757851499-us-east-1
key=lambda/kev-ingestion/8c443677bfe292b6d8b99520b473e7318836dfad65e4a014c1b86cfce3044ef6.zip
VersionId=uF7iiWwWgv6l7XeDyeC6LwU4rUXvB_GY
ETag="9fbe8a44fa67f41b3416a43942016e47"
ContentLength=17538806
ChecksumSHA256=jEQ2d7/ikrbYuZUgtHPnMYg2361l5KAUwbhs/OMETvY=
metadata.sha256=8c443677bfe292b6d8b99520b473e7318836dfad65e4a014c1b86cfce3044ef6
```

NVD Bootstrap ingestion:

```text
bucket=opslens-dev-artifacts-487757851499-us-east-1
key=lambda/nvd-bootstrap-ingestion/4baa4ddc3a3d841eb9c0ca77fe10a8796dcd9bd1a444df8b06ad5a55f23db74e.zip
VersionId=kHiC2lB3vu2c2Ta5mgRFmO85BuoUYz7D
ETag="49593778d698901ba4e94205c1c5f88d"
ContentLength=17546498
ChecksumSHA256=S6pN3Do9hB65wMp3/hCoeW3Nm9GkRN+LBq1aVfI9t04=
metadata.sha256=4baa4ddc3a3d841eb9c0ca77fe10a8796dcd9bd1a444df8b06ad5a55f23db74e
```

Exact-version `HeadObject` and `GetObject` readback verified VersionId, checksum, metadata, size, content type, AES256 encryption, SHA-256, and byte equality with the deterministic local artifacts.

Proof:

```text
LEGACY_ARTIFACT_EPSS_EXACT_VERSION=PASS
LEGACY_ARTIFACT_KEV_EXACT_VERSION=PASS
LEGACY_ARTIFACT_NVD_BOOTSTRAP_EXACT_VERSION=PASS
LEGACY_ARTIFACT_EXACT_VERSION_UPLOAD=PASS
EPSS_BYTES_EXACT=PASS
KEV_BYTES_EXACT=PASS
NVD_BOOTSTRAP_BYTES_EXACT=PASS
```

## Gate D — Terraform immutable pinning — COMPLETE

The three Lambda resources were migrated from local `filename` inputs to immutable S3 coordinates and static Lambda-compatible SHA-256 values.

The full non-targeted dev plan showed:

```text
Plan: 0 to add, 5 to change, 0 to destroy.
```

The five proposed mutations were:

```text
aws_lambda_function.epss_ingestion
aws_lambda_function.kev_ingestion
aws_lambda_function.nvd_bootstrap_ingestion
aws_iam_role_policy.epss_scheduler_runtime
aws_iam_role_policy.kev_scheduler_runtime
```

Two related IAM policy-document data sources were read-only plan dependencies:

```text
data.aws_iam_policy_document.epss_scheduler_runtime
data.aws_iam_policy_document.kev_scheduler_runtime
```

The Lambda diffs were limited to moving from local ZIP deployment coordinates to the exact S3 bucket/key/VersionId pins, updating `source_code_hash`, and provider-managed `last_modified` readback.

The exact saved plan was applied. The provider re-evaluated the scheduler policy documents and determined that no persisted scheduler IAM changes were required, so the successful apply changed only the three Lambda functions:

```text
Apply complete! Resources: 0 added, 3 changed, 0 destroyed.
```

No Lambda replacement, IAM widening, scheduler semantic change, data resource change, Glue change, or analytics change occurred.

Proof:

```text
LEGACY_ARTIFACT_TERRAFORM_PIN=PASS
```

## Gate E — deployed Lambda readback — COMPLETE

All three functions reached a stable successful state:

```text
LEGACY_ARTIFACT_LAMBDAS_STABLE=PASS
```

AWS `GetFunctionConfiguration` returned:

EPSS:

```text
FunctionName=opslens-dev-epss-ingestion
CodeSha256=bu48qSl7Tzk6/tbRXCjeOaaEwFtkvbsC2JFu2y8E00g=
CodeSize=17538328
State=Active
LastUpdateStatus=Successful
```

KEV:

```text
FunctionName=opslens-dev-kev-ingestion
CodeSha256=jEQ2d7/ikrbYuZUgtHPnMYg2361l5KAUwbhs/OMETvY=
CodeSize=17538806
State=Active
LastUpdateStatus=Successful
```

NVD Bootstrap:

```text
FunctionName=opslens-dev-nvd-bootstrap-ingestion
CodeSha256=S6pN3Do9hB65wMp3/hCoeW3Nm9GkRN+LBq1aVfI9t04=
CodeSize=17546498
State=Active
LastUpdateStatus=Successful
```

The Terraform state independently retained the exact expected `s3_bucket`, `s3_key`, `s3_object_version`, and `source_code_hash` values for all three resources.

Proof:

```text
LEGACY_ARTIFACT_LAMBDA_READBACK=PASS
```

## Gate F — global dev convergence — COMPLETE

A fresh full dev plan after deployment returned:

```text
No changes. Your infrastructure matches the configuration.
POST_APPLY_PLAN_RC=0
```

This removes the global dev convergence exception first identified during the Phase 2.3G closeout.

Repository quality checks also passed at closeout:

```text
terraform -chdir=infra/environments/dev fmt -check -> PASS
terraform -chdir=infra/environments/dev validate  -> PASS
uv run ruff check .                                -> PASS
uv run pyright                                     -> 0 errors, 0 warnings, 0 informations
uv run pytest -q                                   -> PASS, 100%
git diff --check                                   -> PASS
git status --short                                 -> clean
```

Proof:

```text
LEGACY_ARTIFACT_NO_DRIFT=PASS
```

## Final gate state

```text
LEGACY_ARTIFACT_NVD_BOOTSTRAP_BOUNDARY=PASS
LEGACY_ARTIFACT_EPSS_DETERMINISTIC=PASS
LEGACY_ARTIFACT_KEV_DETERMINISTIC=PASS
LEGACY_ARTIFACT_NVD_BOOTSTRAP_DETERMINISTIC=PASS
LEGACY_ARTIFACT_DEPLOYMENT_RETENTION=PASS
LEGACY_ARTIFACT_EXACT_VERSION_UPLOAD=PASS
LEGACY_ARTIFACT_TERRAFORM_PIN=PASS
LEGACY_ARTIFACT_LAMBDA_READBACK=PASS
LEGACY_ARTIFACT_NO_DRIFT=PASS
LEGACY_ARTIFACT_MIGRATION=COMPLETE
```

## Architectural result

All deployed OpsLens Lambda runtimes now follow the same artifact lifecycle principle:

```text
build output is evidence
artifact identity is cryptographic
content-addressed current artifacts remain durable
S3 object version is exact deployment provenance
Terraform consumes immutable coordinates
rebuilding locally does not redefine deployed infrastructure
```

This migration was an infrastructure/deployment-lifecycle correction only. It did not change the project invariant:

> **Agents reason. Code verifies evidence.**
