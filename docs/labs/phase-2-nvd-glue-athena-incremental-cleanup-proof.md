# Phase 2.3G.3 — Incremental Projection Cleanup Proof

## Status

COMPLETE — the temporary direct-Athena table and the exact temporary incremental analytics projection version were removed after the 2.3G.3A/2.3G.3B evidence was captured.

## Scope

This cleanup closes the temporary AWS resources used to prove the incremental exact-version projection path:

```text
exact committed Silver version
    -> exact-version analytics projection
    -> ordinary Athena Parquet table
    -> deterministic PyArrow/Athena cross-check
    -> exact cleanup
```

The authoritative Silver source and watermark were not mutated.

## Temporary Athena table cleanup

Temporary table:

```text
opslens_dev.nvd_cve_versions_projection_spike_65e286bd
```

DROP TABLE QueryExecutionId:

```text
f3ba0ea1-b19e-4ef0-be2b-c6542c550b88
```

Execution:

```text
State: SUCCEEDED
DataScannedInBytes: 0
EngineExecutionTimeInMillis: 499
TotalExecutionTimeInMillis: 728
QueryQueueTimeInMillis: 188
```

A subsequent Glue `GetTable` returned `EntityNotFoundException`.

```text
NVD_2_3G_DIRECT_TABLE_CLEANUP_GATE=PASS
```

## Projection pre-delete evidence

Temporary projected key:

```text
analytics-spike/nvd/cve/exact-projection/schema_version=1/source_kind=incremental/update_id=65e286bda04b0447d71c869e15c31f8ac27621dc86362bcc3bdf79fc0d78bb0e/part-00000.parquet
```

Exact temporary destination VersionId:

```text
A29.Nmc0IQUFAmxsNLAk9hLiG7ETLY42
```

Immediately before deletion, an exact-version `HeadObject` returned the same VersionId, 4,724,916 bytes, and the expected lineage metadata.

```text
NVD_2_3G_PROJECTION_PRE_DELETE_VERSION_GATE=PASS
```

## Exact version deletion

`DeleteObject` was invoked with the exact VersionId rather than deleting the key without a version selector.

Response:

```text
VersionId: A29.Nmc0IQUFAmxsNLAk9hLiG7ETLY42
DeleteMarker: absent
```

Formal gate:

```text
NVD_2_3G_PROJECTION_DELETE_VERSION_GATE=PASS
```

This removed the temporary projected version itself rather than intentionally creating a new delete marker.

## Post-delete exact-version verification

A subsequent `HeadObject` specifying VersionId `A29.Nmc0IQUFAmxsNLAk9hLiG7ETLY42` returned HTTP 404 Not Found.

```text
NVD_2_3G_PROJECTION_EXACT_VERSION_CLEANUP_GATE=PASS
```

## Post-delete current-key verification

A subsequent current-key `HeadObject` without a VersionId returned HTTP 404 Not Found.

```text
NVD_2_3G_PROJECTION_CURRENT_CLEANUP_GATE=PASS
```

No `ListBucket` operation was required to establish cleanup of the deterministic destination identity.

## Cleanup result

All temporary-resource cleanup gates passed:

```text
NVD_2_3G_DIRECT_TABLE_CLEANUP_GATE=PASS
NVD_2_3G_PROJECTION_PRE_DELETE_VERSION_GATE=PASS
NVD_2_3G_PROJECTION_DELETE_VERSION_GATE=PASS
NVD_2_3G_PROJECTION_EXACT_VERSION_CLEANUP_GATE=PASS
NVD_2_3G_PROJECTION_CURRENT_CLEANUP_GATE=PASS
```

The Athena query-result objects are intentionally retained as bounded audit evidence under the existing Athena results lifecycle.

## Architectural implication

The incremental proof now demonstrates the complete temporary lifecycle:

```text
exact source authority
    -> deterministic conditional projection
    -> direct ordinary-Parquet Athena reads
    -> deterministic cross-check
    -> exact cleanup
```

The proof did not require source mutation, prefix discovery, or a permanent analytics runtime.

## Next boundary

Repeat the proven exact-version projection pattern for the independently verified Bootstrap seed before implementing permanent Terraform, Lambda, IAM, Glue, or event-driven analytics projection resources.
