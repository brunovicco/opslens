# Phase 2.3G.4E — Permanent NVD Analytics Runtime Terraform

## Status

IN PROGRESS — runtime Terraform resources are defined and await local static validation before deployment IAM, permanent Glue table, immutable artifact pinning, plan, and apply.

## Precondition

Phase 2.3G.4D is COMPLETE.

The reported local gates passed:

```text
focused analytics pytest: PASS
NVD unit suite: PASS
full pytest suite: PASS
Ruff: PASS
Pyright strict: PASS
Bandit: PASS
pip-audit: No known vulnerabilities found
```

The initial `pip-audit` resolver attempt failed while creating a temporary virtual environment. Re-running against the already-resolved, hash-pinned runtime requirements with `--disable-pip --require-hashes` completed successfully with no known vulnerabilities.

## Runtime resources

The permanent runtime Terraform now defines:

- Lambda function `opslens-dev-nvd-analytics-projector`;
- execution role `OpsLensNvdAnalyticsProjectorLambdaRole`;
- least-privilege inline runtime policy;
- CloudWatch log group with 14-day retention;
- X-Ray active tracing;
- SQS OnFailure queue `opslens-dev-nvd-analytics-projector-failures`;
- asynchronous retry policy with 3600-second maximum event age and two retries;
- S3 invoke permission;
- one additional notification entry inside the existing single data-bucket `aws_s3_bucket_notification` resource.

No second bucket-notification owner is introduced.

## Runtime authority and IAM boundary

The runtime can read exact object versions only for:

```text
control/nvd/cve/incremental/watermark.json
silver/nvd/cve/schema_version=1/source_kind=bootstrap/*
silver/nvd/cve/schema_version=1/source_kind=incremental/*
analytics/nvd/cve/schema_version=1/*
```

The analytics destination prefix additionally permits current-object `GetObject` for replay pinning and `PutObject` for deterministic projection.

The runtime policy intentionally does not grant:

```text
s3:ListBucket
s3:DeleteObject
s3:DeleteObjectVersion
PutObject on the authoritative watermark
glue:CreatePartition
glue:BatchCreatePartition
```

## Eventing

Incremental analytics projection is triggered by:

```text
s3:ObjectCreated:Put
prefix: control/nvd/cve/incremental/
suffix: watermark.json
```

The application inbound parser still requires the exact canonical object key and exact event VersionId, so the Terraform filter is only an event-routing boundary and not an authority decision.

Bootstrap remains explicit and receives no S3 notification.

## Artifact gate

The Lambda resource currently requires three explicit root input variables:

```text
nvd_analytics_projector_artifact_sha256
nvd_analytics_projector_artifact_sha256_base64
nvd_analytics_projector_artifact_version
```

They intentionally have no defaults. This keeps `terraform validate` available while making `terraform plan/apply` fail closed until Phase 2.3G.4G creates and verifies the immutable deployment package.

At artifact closeout these temporary inputs will be replaced by exact committed immutable pins, matching the existing NVD runtime release pattern.

## Next gates

Before proceeding to Phase 2.3G.4F, validate:

```text
terraform fmt -check -recursive infra
terraform validate for infra/bootstrap
terraform validate for infra/environments/dev
TFLint for dev
Checkov for Terraform
```

No AWS mutation is authorized by this checkpoint.
