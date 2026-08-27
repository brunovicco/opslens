# Phase 2.3G.4 — Permanent NVD Analytics Path Design

## Status

SELECTED FOR IMPLEMENTATION — all temporary proof/spike work is complete and cleaned up. This document fixes the permanent runtime and Glue/Athena direction before code and Terraform are introduced.

## Decision basis

The AWS proof sequence established all required primitives independently:

```text
exact Silver / watermark authority
    -> exact source VersionId
    -> CopyObject from that exact source version
    -> CopySourceVersionId verification
    -> immutable destination VersionId
    -> destination SHA-256 equality
    -> deterministic lineage metadata
    -> replay rejected by If-None-Match: *
    -> ordinary Parquet Athena table
    -> exact PyArrow/Athena equivalence
    -> bounded scans under the existing 10 MiB workgroup cutoff
```

The temporary incremental and Bootstrap projections and Glue tables were deleted after evidence was captured.

The permanent path must preserve the same properties rather than introduce a different authority model.

## Authority invariant

```text
bronze_complete
    !=
silver_complete
    !=
watermark_committed
    -> analytics_eligible
    -> analytics_projected
```

`analytics_projected` is downstream materialization only.

The analytics runtime must never:

```text
advance the NVD watermark
rewrite Silver evidence
infer authority from an S3 prefix
select an unspecified current Silver version
list a prefix to discover the source of truth
```

## Selected runtime

Introduce one bounded **NVD Analytics Projector Lambda**.

The projector has two explicit invocation modes.

### Incremental mode — event driven

```text
S3 ObjectCreated:Put
control/nvd/cve/incremental/watermark.json
    |
    v
strictly parse bucket + key + event VersionId
    |
    v
GetObject exact watermark VersionId
    |
    v
parse canonical NvdAuthoritativeWatermarkV1
    |
    v
require commit_basis.kind = silver_complete_promotion
    |
    v
load exact Silver COMPLETE VersionId named by watermark
    |
    v
cross-check exact Silver Parquet key + VersionId + SHA-256
    |
    v
analytics_eligible
    |
    v
CopyObject from exact Silver Parquet VersionId
```

The S3 event VersionId is only a coordinate used to load exact persisted authority. Event payload fields do not replace the watermark bytes as source of truth.

At-least-once or out-of-order delivery is safe because every watermark event identifies one exact persisted watermark version and each projection destination is batch-deterministic.

A Bootstrap recovery-seed watermark basis is not an incremental projection request and must be rejected/no-op according to the strict invocation contract.

### Bootstrap mode — explicit seed

Bootstrap is deliberately **not** projected automatically from every Silver Bootstrap COMPLETE event.

The initial permanent Bootstrap projection is a one-time explicit invocation carrying:

```text
mode=bootstrap_seed
silver_complete_key=<exact canonical Bootstrap COMPLETE key>
silver_complete_version_id=<exact VersionId>
```

The runtime independently reads and validates that exact COMPLETE, derives the exact Bootstrap Parquet key/VersionId/SHA-256, and only then establishes `analytics_eligible`.

This keeps the boundary explicit:

```text
silver_complete != analytics_eligible
```

and avoids silently projecting every future Bootstrap revision.

## Exact evidence loading

### Incremental

The existing authoritative watermark already binds:

```text
update_id
silver_manifest.key
silver_manifest.version_id
silver_manifest.sha256
silver_parquet.key
silver_parquet.version_id
silver_parquet.sha256
logical_record_set_sha256
```

The projector must exact-read the watermark version supplied by the S3 event and require the canonical `silver_complete_promotion` basis.

It must then exact-read the Silver COMPLETE version named by the watermark and verify at minimum:

```text
completion_status=complete
schema_version=1
source_kind=incremental
source_batch_id=update_id
silver_object.key == watermark silver_parquet.key
silver_object.version_id == watermark silver_parquet.version_id
silver_object.sha256 == watermark silver_parquet.sha256
row_count is a valid non-negative integer
```

The projector does not need to re-download the source Parquet before CopyObject because the watermark is already the result of exact Silver verification. The destination bytes are verified after materialization against the authoritative Silver SHA-256.

### Bootstrap

The explicit seed path exact-reads the supplied Bootstrap Silver COMPLETE VersionId and requires the canonical Bootstrap Silver v1 contract.

The exact COMPLETE must name one deterministic Bootstrap Parquet key, VersionId, SHA-256, row count, feed year, and feed revision. Those exact values become the Bootstrap projection authority.

## Permanent S3 namespace

The clean analytics root is:

```text
analytics/nvd/cve/schema_version=1/
```

Only schema-compatible Parquet data objects belong below this root.

No JSON COMPLETE, receipt, watermark, symlink, or control object may be written below the Athena table root.

### Partition layout

Use a uniform low-cardinality/date partition layout:

```text
analytics/nvd/cve/schema_version=1/
  source_kind=<bootstrap|incremental>/
  projection_date=YYYY-MM-DD/
    <deterministic-batch-file>.parquet
```

Incremental destination:

```text
source_kind=incremental/
projection_date=<UTC date of committed_through_at>/
update_id=<64-lowercase-hex>.parquet
```

Bootstrap destination:

```text
source_kind=bootstrap/
projection_date=<UTC date encoded by feed revision>/
feed_revision=<exact-feed-revision>.parquet
```

The batch identity remains deterministic in the filename and in object metadata. Multiple incremental commits on the same UTC date can coexist without collisions.

### Why not partition by update_id/source_batch_id

`update_id` and Bootstrap batch identifiers are high-cardinality, non-procedural values. Using them as an `enum` projection would grow table metadata continuously. Using an `injected` partition would force every Athena query to provide explicit batch identifiers, which is useful for exact-batch evidence checks but poor for normal threat-intelligence analytics across a date range.

The selected `source_kind + projection_date` layout instead uses two projection-friendly dimensions:

```text
source_kind     -> enum
projection_date -> date
```

Batch identity remains available in the Parquet rows (`incremental_update_id`, Bootstrap fields, `source_batch_id`) and the deterministic object filename.

## Deterministic destination metadata

Every projected Parquet object must carry:

```text
dataset=nvd_cve_versions
schema_version=1
source_kind=<bootstrap|incremental>
source_batch_id=<exact-batch-id>
row_count=<exact-count>
parquet_sha256=<authoritative-source-sha256>
authority_source_key=<exact-Silver-Parquet-key>
authority_source_version_id=<exact-Silver-Parquet-VersionId>
authority_source_sha256=<exact-Silver-Parquet-SHA256>
authority_state=<watermark_committed|bootstrap_verified_seed>
```

Metadata is bounded lineage evidence. The authoritative incremental source remains the exact watermark + Silver evidence, not the metadata itself.

## Copy contract

The permanent boto3 adapter must use structured CopySource coordinates:

```python
CopySource={
    "Bucket": bucket,
    "Key": source_key,
    "VersionId": source_version_id,
}
```

and:

```text
IfNoneMatch="*"
MetadataDirective="REPLACE"
ContentType="application/vnd.apache.parquet"
```

The adapter must require:

```text
CopySourceVersionId == requested source VersionId
non-empty destination VersionId
```

After CopyObject, the projector exact-reads the new destination VersionId and requires:

```text
destination SHA-256 == authoritative source SHA-256
ContentLength == declared exact Silver size
PAR1 leading/trailing magic
expected lineage metadata
```

The exact destination read is bounded by the existing NVD Silver Parquet envelope rather than by unbounded S3 reads.

## Replay and conflict behavior

A `412 PreconditionFailed` is not automatically success.

Replay handling is:

```text
conditional copy rejected
    -> read current deterministic destination
    -> require non-empty destination VersionId
    -> exact-read that destination VersionId
    -> verify SHA-256 + size + metadata against expected authority
    -> return already_projected only on exact match
```

An incompatible current object is a hard failure.

A `409 ConditionalRequestConflict` is a recoverable concurrency conflict. The invocation may retry within a small bounded policy; after the retry envelope it fails so Lambda asynchronous retry/failure handling remains authoritative.

## No runtime delete or discovery

The permanent projector runtime requires no:

```text
s3:ListBucket
s3:DeleteObject
s3:DeleteObjectVersion
glue:CreatePartition
glue:BatchCreatePartition
```

It projects only coordinates supplied by exact authority contracts.

## Glue table

Create one permanent external table:

```text
opslens_dev.nvd_cve_versions
```

The table uses the explicit application-owned NVD Silver v1 schema and ordinary Parquet input/serde/output formats.

Partition columns are separate from the Parquet data columns:

```text
source_kind_partition string
projection_date       string
```

Table properties:

```text
projection.enabled=true
projection.source_kind_partition.type=enum
projection.source_kind_partition.values=bootstrap,incremental
projection.projection_date.type=date
projection.projection_date.format=yyyy-MM-dd
projection.projection_date.range=2026-01-01,NOW
projection.projection_date.interval=1
projection.projection_date.interval.unit=DAYS
```

Storage template:

```text
s3://<data-bucket>/analytics/nvd/cve/schema_version=1/source_kind=${source_kind_partition}/projection_date=${projection_date}/
```

This avoids a Glue crawler and avoids runtime Glue partition mutation.

The initial `2026-01-01` lower bound is explicit dev-environment configuration matching the current NVD dataset epoch in OpsLens. It is not an immutable domain constant and can be moved earlier by Terraform if historical projections are later introduced.

## Athena cost boundary

Keep the existing workgroup cutoff unchanged:

```text
bytes_scanned_cutoff_per_query = 10485760
```

The Bootstrap proof demonstrated that a physical 36,240,684-byte Parquet object can still support bounded columnar queries below this cutoff.

The permanent design therefore keeps both controls:

```text
partition pruning by source_kind/date
+
10 MiB hard workgroup cutoff
```

No claim is made that every possible NVD query will fit under the cutoff.

## Eventing

The existing S3 bucket notification resource is the single owner of Lambda notifications for the data bucket. The permanent projector must be added to that existing resource; a second `aws_s3_bucket_notification` resource must not be introduced for the same bucket.

Incremental notification:

```text
event: s3:ObjectCreated:Put
prefix: control/nvd/cve/incremental/
suffix: watermark.json
```

The handler additionally requires the exact canonical key:

```text
control/nvd/cve/incremental/watermark.json
```

The S3 ObjectCreated record VersionId is required because the bucket is versioned and the projector must load the exact watermark version that generated the event.

No automatic Bootstrap S3 notification is selected.

## Lambda boundary

Follow the existing NVD runtime pattern:

```text
Powertools Logger
Powertools Metrics
Powertools Tracer
strict inbound parser
composition root
application service
explicit outbound ports/adapters
JSON structured logs
X-Ray active tracing
Lambda asynchronous retry policy
SQS OnFailure destination
```

Suggested service identity:

```text
opslens-nvd-analytics-projector
```

Suggested Lambda name:

```text
opslens-dev-nvd-analytics-projector
```

## Metrics

At minimum emit:

```text
NvdAnalyticsProjectionInvocation
NvdAnalyticsProjectionSuccess
NvdAnalyticsProjectionAlreadyProjected
NvdAnalyticsProjectionFailure
NvdAnalyticsProjectionEvidenceMismatch
NvdAnalyticsProjectionConflict
NvdAnalyticsProjectionBytes
NvdAnalyticsBootstrapSeed
NvdAnalyticsIncrementalProjection
```

Logs must include source/destination keys and VersionIds but never treat log fields as authority.

## IAM

Projector runtime data permissions:

```text
s3:GetObjectVersion
  control/nvd/cve/incremental/watermark.json
  silver/nvd/cve/schema_version=1/source_kind=incremental/*
  silver/nvd/cve/schema_version=1/source_kind=bootstrap/*
  analytics/nvd/cve/schema_version=1/*

s3:PutObject
  analytics/nvd/cve/schema_version=1/*
```

Plus only:

```text
sqs:SendMessage
logs:CreateLogStream
logs:PutLogEvents
xray:PutTraceSegments
xray:PutTelemetryRecords
```

No watermark `PutObject` permission belongs to this role.

No `ListBucket` or delete permission belongs to this role.

## Deployment identity changes

Before dev Terraform can create the permanent table, the GitHub deployment role requires exact Glue permissions for:

```text
opslens_dev.nvd_cve_versions
```

The projector Lambda/IAM/log/SQS/event-invoke resources also require deployment-role permissions following the existing NVD promotion deployment pattern. These permissions should be scoped to the exact new resource names/ARNs rather than broad service wildcards where the AWS API supports resource scoping.

## Failure queue

Create a dedicated queue:

```text
opslens-dev-nvd-analytics-projector-failures
```

The Lambda asynchronous invoke configuration should retain the existing NVD runtime policy:

```text
maximum_event_age_in_seconds = 3600
maximum_retry_attempts       = 2
```

The queue is an operational failure destination, not an analytics authority source.

## Application structure candidate

```text
src/opslens/transformation/nvd/
  analytics_projection_config.py
  analytics_projection_composition.py
  analytics_projection_lambda_handler.py

  application/
    analytics_projection_models.py
    analytics_projection_key_factory.py
    analytics_projection_evidence_loader.py
    analytics_projection_service.py

  adapters/inbound/
    analytics_projection_event.py

  adapters/outbound/
    s3_analytics_projection.py
```

Existing authoritative-watermark parser and evidence-object contracts should be reused rather than reimplemented where their semantics match.

## Implementation sequence

```text
2.3G.4A  freeze application/domain contracts and key factory
2.3G.4B  implement exact evidence loader + S3 projection adapter
2.3G.4C  implement service, inbound parser, composition, Lambda handler
2.3G.4D  unit tests + lint/type/security checks
2.3G.4E  Terraform runtime IAM, SQS, logs, Lambda, eventing
2.3G.4F  permanent Glue nvd_cve_versions table + deployment IAM
2.3G.4G  build/upload immutable Lambda artifact + Terraform plan/apply
2.3G.4H  explicit exact Bootstrap seed proof
2.3G.4I  event-driven exact incremental projection proof
2.3G.4J  permanent Athena query/cost/lineage proof
2.3G.4K  operational failure/replay/observability proof and closeout
```

## Permanent proof gates

The permanent deployment is not complete until evidence demonstrates:

```text
exact watermark event VersionId consumed
exact source VersionId copied
CopySourceVersionId exact match
exact destination VersionId returned
exact destination SHA-256 match
lineage metadata match
replay accepted only after exact destination verification
Bootstrap explicit seed success
incremental event-driven projection success
ordinary Athena table success
partition-pruned query success
10 MiB workgroup cutoff unchanged
no runtime ListBucket/DeleteObject/watermark PutObject
failure destination configured
CloudWatch/X-Ray evidence present
Terraform plan/apply clean
```

## Rejected alternatives

```text
direct Athena LOCATION on Silver mixed Parquet/JSON prefix
SymlinkTextInputFormat as permanent authority layer
Glue crawler
Iceberg for this phase
runtime S3 prefix discovery
runtime Glue partition registration
high-cardinality enum projection for update_id
mandatory injected batch partition for all user queries
automatic projection of every Bootstrap Silver COMPLETE
Athena cutoff increase
```

## Decision

```text
Permanent projection primitive:       exact-VersionId S3 CopyObject
Permanent analytical namespace:       clean Parquet-only analytics/nvd/cve
Incremental eligibility source:       exact authoritative watermark version
Bootstrap eligibility source:         explicit exact verified seed
Permanent Glue access:                ordinary Parquet + source_kind/date partition projection
Runtime Glue partition writes:        none
Runtime watermark mutation:           forbidden
Runtime S3 list/delete:                forbidden
Athena cutoff:                         unchanged at 10 MiB
Permanent implementation:             AUTHORIZED NEXT
```
