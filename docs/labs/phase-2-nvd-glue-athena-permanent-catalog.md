# Phase 2.3G.4F — Permanent NVD analytics catalog

## Status

IMPLEMENTED — local Terraform quality/security gates pending.

## Purpose

Define the permanent Glue catalog surface for exact-authority NVD analytics projections and the deployment IAM required to reconcile both the catalog table and projector runtime.

This checkpoint does not deploy AWS resources and does not materialize Bootstrap or incremental analytics objects.

## Permanent Glue table

The permanent table is:

```text
opslens_dev.nvd_cve_versions
```

It is an ordinary external Parquet table over the clean analytics-only namespace:

```text
s3://<data-bucket>/analytics/nvd/cve/schema_version=1/
```

The table keeps the complete 32-column NVD Silver v1 schema and adds only two Glue partition coordinates:

```text
source_kind_partition
projection_date
```

These partition coordinates are path metadata and are intentionally distinct from the in-record `source_kind` field.

## Partition projection

No crawler and no runtime Glue partition mutation are used.

```text
projection.enabled = true

source_kind_partition:
  type   = enum
  values = bootstrap,incremental

projection_date:
  type          = date
  range         = 2026-01-01,NOW
  format        = yyyy-MM-dd
  interval      = 1
  interval.unit = DAYS
```

The storage template is deterministic:

```text
s3://<data-bucket>/analytics/nvd/cve/schema_version=1/source_kind=${source_kind_partition}/projection_date=${projection_date}/
```

The lower date bound is deliberately fixed to 2026 for the current dev environment. It is not a general historical claim about NVD.

## Schema authority

The Glue table mirrors NVD Silver v1 rather than defining a new analytics record schema.

This preserves the boundary:

```text
Silver record contract
  -> exact authorized projection bytes
  -> Glue interpretation
```

The analytics projector does not rewrite records to fit Glue.

## Deployment IAM

`infra/bootstrap/github_analytics_permissions.tf` now grants GitHub deployment automation exact Glue table permissions for:

```text
opslens_dev.nvd_cve_versions
```

The policy does not broaden the EPSS or KEV table ARNs.

A separate deployment policy now scopes projector infrastructure reconciliation to:

```text
Lambda: opslens-dev-nvd-analytics-projector
IAM role: OpsLensNvdAnalyticsProjectorLambdaRole
SQS: opslens-dev-nvd-analytics-projector-failures
CloudWatch Logs: /aws/lambda/opslens-dev-nvd-analytics-projector
```

`iam:PassRole` is constrained to `lambda.amazonaws.com`, and `lambda:AddPermission` is constrained to the S3 principal.

## Runtime boundary remains unchanged

This deployment IAM does not change runtime authority.

The projector execution role still excludes:

```text
s3:ListBucket
s3:DeleteObject
s3:DeleteObjectVersion
watermark s3:PutObject
glue:CreatePartition
glue:BatchCreatePartition
```

The Glue table itself does not authorize analytics eligibility. It only makes already projected Parquet addressable to Athena.

## Gate before artifact/deploy

Before Phase 2.3G.4G begins, the following must be green locally:

```text
terraform fmt -check -recursive infra
terraform validate for bootstrap and dev with backend disabled
TFLint for bootstrap and dev
Checkov for infra
```

No `terraform plan` or `apply` belongs to this checkpoint.
