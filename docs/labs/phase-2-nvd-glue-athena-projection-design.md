# Phase 2.3G.3 — Exact-Version NVD Analytics Projection Design

## Status

IN PROGRESS — selected after the SymlinkTextInputFormat compatibility proof.

## Decision context

Phase 2.3G.2 proved that Athena can read NVD Silver v1 through `SymlinkTextInputFormat`, including nested Parquet types, while staying below the current 10 MiB query cutoff for the bounded incremental source.

That mechanism is not selected for permanent authority preservation because the symlink contains a key-oriented S3 URI while OpsLens authority is bound to an exact source `VersionId` and SHA-256.

The next candidate deliberately materializes the exact authorized source version into a clean Parquet-only analytics namespace.

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

`analytics_projected` must never authorize or advance the NVD watermark. It is a downstream materialization state only.

## Candidate flow

```text
exact authoritative watermark event
    |
    v
load exact watermark VersionId
    |
    v
validate canonical committed state
    |
    v
require silver_complete_promotion
    |
    v
verify exact Silver Parquet
    key + VersionId + SHA-256
    |
    v
S3 CopyObject from exact source VersionId
    |
    +--> deterministic analytics destination key
    +--> If-None-Match: *
    |
    v
verify CopySourceVersionId
    |
    v
verify destination VersionId + SHA-256 + metadata
    |
    v
normal Athena Parquet table over clean analytics prefix
```

## Why CopyObject

Amazon S3 supports selecting a specific source version by appending `versionId` to the copy source. The successful response returns the `CopySourceVersionId` and, in a versioned destination bucket, a new destination `VersionId`.

`CopyObject` also supports `If-None-Match: *` for destination conditional creation.

This provides a direct AWS primitive for transforming exact-version evidence into an append-only analytical object without downloading and re-uploading the Parquet bytes through Lambda memory.

Official references:

- <https://docs.aws.amazon.com/AmazonS3/latest/API/API_CopyObject.html>
- <https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html>
- <https://docs.aws.amazon.com/AmazonS3/latest/userguide/RetrievingObjectVersions.html>

## Destination contract candidate

Temporary proof prefix:

```text
analytics-spike/nvd/cve/exact-projection/
  schema_version=1/
  source_kind=incremental/
  update_id=<sha256>/
    part-00000.parquet
```

Permanent candidate prefix after proof:

```text
analytics/nvd/cve/
  schema_version=1/
  source_kind=bootstrap/
  source_batch_id=<deterministic-id>/
    part-00000.parquet

analytics/nvd/cve/
  schema_version=1/
  source_kind=incremental/
  update_id=<sha256>/
    part-00000.parquet
```

Only Parquet data objects belong under the analytical table prefix. COMPLETE manifests and control objects remain outside it.

## Destination metadata candidate

The projected object should retain enough bounded metadata to prove lineage without requiring prefix discovery:

```text
dataset=nvd_cve_versions
schema_version=1
source_kind=<bootstrap|incremental>
source_batch_id=<batch-id>
row_count=<count>
parquet_sha256=<source-and-destination-hash>
authority_source_key=<exact-source-key>
authority_source_version_id=<exact-source-VersionId>
authority_source_sha256=<exact-source-sha256>
authority_state=watermark_committed|bootstrap_verified_seed
```

The manifest/controller remains the richer proof. Object metadata is informational and bounded.

## Idempotency

Destination identity is deterministic from the authorized source batch.

The first projection attempt conditionally creates the destination object.

Replay behavior:

```text
first exact source observation
    -> CopyObject If-None-Match: *
    -> created

same exact source observation replay
    -> destination exists
    -> conditional copy rejected
    -> exact destination evidence must be verified
    -> accepted only if key/version/hash/metadata match expected projection
```

A conditional conflict is not automatically success.

## Runtime IAM candidate

The future projection runtime should require only the demonstrated data-plane actions:

```text
s3:GetObjectVersion
    exact authoritative watermark and Silver source scopes

s3:PutObject
    analytics/nvd/cve/* destination scope
```

S3 documents `s3:GetObjectVersion` as the source permission needed when CopyObject specifies a source `versionId`, and `s3:PutObject` for the destination.

No `s3:ListBucket` or `s3:DeleteObject` requirement is demonstrated for the permanent runtime.

## Athena table candidate

A normal Parquet external table can point at the clean analytical root because the destination namespace contains only schema-compatible Parquet objects.

This removes the `SymlinkTextInputFormat` indirection and aligns with AWS guidance to prefer better file organization when available.

The explicit Silver v1 schema remains application-owned. No Glue crawler is required.

## Cost trade-off

The projection duplicates Parquet bytes once per analytically authorized batch.

Measured source sizes available before this proof:

```text
verified Bootstrap Parquet:
36,240,684 bytes

verified committed incremental Parquet:
4,724,916 bytes
```

The duplication is accepted only if the exact-version proof passes and the resulting cleaner authority/query boundary is demonstrated.

No permanent storage-cost estimate is claimed yet.

## Phase 2.3G.3 proof sequence

```text
1. Re-read the exact committed incremental source VersionId and SHA-256.
2. Prove the temporary projection destination key is absent.
3. Copy from the exact source VersionId with If-None-Match: *.
4. Require CopySourceVersionId == authoritative source VersionId.
5. Require non-empty destination VersionId.
6. Download the exact destination VersionId and verify SHA-256 equality.
7. Verify bounded provenance metadata.
8. Replay the same conditional copy and require fail-closed collision behavior.
9. Create a temporary normal Parquet Athena table over the clean projection prefix.
10. Re-run cardinality and nested-type cross-checks.
11. Measure scan bytes and latency.
12. Delete the temporary table and exact temporary projection version.
13. Only after the incremental proof passes, repeat the projection pattern for the verified Bootstrap seed.
```

## Proof gates

```text
NVD_2_3G_PROJECTION_SOURCE_VERSION_GATE
NVD_2_3G_PROJECTION_SOURCE_SHA256_GATE
NVD_2_3G_PROJECTION_DESTINATION_ABSENT_GATE
NVD_2_3G_COPY_SOURCE_VERSION_GATE
NVD_2_3G_PROJECTION_DESTINATION_VERSION_GATE
NVD_2_3G_PROJECTION_DESTINATION_SHA256_GATE
NVD_2_3G_PROJECTION_METADATA_GATE
NVD_2_3G_PROJECTION_REPLAY_GATE
NVD_2_3G_DIRECT_PARQUET_READ_GATE
NVD_2_3G_DIRECT_PARQUET_CROSSCHECK_GATE
NVD_2_3G_PROJECTION_SCAN_LIMIT_GATE
NVD_2_3G_PROJECTION_CLEANUP_GATE
```

## Out of scope

```text
Permanent Lambda/index runtime before proof
Permanent Glue table before proof
Bootstrap projection before incremental proof
Scan-cutoff increase
Iceberg
Glue crawler
RAG
Bedrock
agents
MCP
A2A
Phase 3
```

## Current decision

```text
SymlinkTextInputFormat compatibility: PROVEN
SymlinkTextInputFormat permanent authority layer: REJECTED
Exact-version CopyObject projection: SELECTED FOR AWS PROOF
Permanent analytics infrastructure: DEFERRED UNTIL PROOF
```
