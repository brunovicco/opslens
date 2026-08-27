# Phase 2.3G.3C — Bootstrap Projection Cleanup Proof

## Status

COMPLETE — the temporary Bootstrap Athena table and exact temporary projected S3 object version were removed after all Bootstrap projection and Athena proof evidence had been recorded.

## Purpose

Close the Bootstrap proof without leaving temporary analytical state behind, while preserving the evidence that the exact-version projection and ordinary-Parquet Athena path worked under the existing 10 MiB workgroup cutoff.

The cleanup does not touch the verified Bootstrap Silver COMPLETE or Silver Parquet source evidence.

## Temporary resources removed

Temporary Athena/Glue table:

```text
opslens_dev.nvd_cve_versions_bootstrap_projection_spike_2026
```

Temporary projected object:

```text
analytics-spike/nvd/cve/exact-projection/schema_version=1/source_kind=bootstrap/feed_year=2026/feed_revision=20260822T070013Z-f10b8dc5388f72172740b476be73ca9e24ab6834aa502ff9cbb3a733973d6d68/part-00000.parquet
```

Exact temporary destination VersionId:

```text
3MQ4Yx_EfGR01vYOt1dxoQtAn746VID5
```

## Athena table cleanup

The temporary table was dropped through Athena.

QueryExecutionId:

```text
1c91825e-4bab-4348-9b75-4d7b53d7d495
```

Execution:

```text
State: SUCCEEDED
DataScannedInBytes: 0
EngineExecutionTimeInMillis: 568
TotalExecutionTimeInMillis: 786
QueryQueueTimeInMillis: 175
```

A subsequent Glue `GetTable` returned `EntityNotFoundException`:

```text
NVD_2_3G_BOOTSTRAP_TABLE_CLEANUP_GATE=PASS
```

## Exact object pre-delete verification

Immediately before deletion, the projected object was re-opened using exact VersionId:

```text
3MQ4Yx_EfGR01vYOt1dxoQtAn746VID5
```

The final pre-delete checks confirmed:

- exact destination VersionId
- physical size `36,240,684` bytes
- `parquet_sha256` metadata reference equal to the verified Bootstrap source/destination SHA-256
- `authority_state=bootstrap_verified_seed`

Formal gates:

```text
NVD_2_3G_BOOTSTRAP_PRE_DELETE_VERSION_GATE=PASS
NVD_2_3G_BOOTSTRAP_PRE_DELETE_SIZE_GATE=PASS
NVD_2_3G_BOOTSTRAP_PRE_DELETE_SHA_REFERENCE_GATE=PASS
NVD_2_3G_BOOTSTRAP_PRE_DELETE_AUTHORITY_GATE=PASS
```

## Exact VersionId deletion

Deletion explicitly targeted only the temporary projected VersionId:

```text
3MQ4Yx_EfGR01vYOt1dxoQtAn746VID5
```

S3 returned the same requested VersionId. No delete marker was reported by the command response.

```text
NVD_2_3G_BOOTSTRAP_DELETE_VERSION_GATE=PASS
```

## Post-delete verification

An exact-version `HeadObject` for the deleted VersionId returned 404:

```text
NVD_2_3G_BOOTSTRAP_EXACT_VERSION_CLEANUP_GATE=PASS
```

A current-key `HeadObject` also returned 404:

```text
NVD_2_3G_BOOTSTRAP_CURRENT_CLEANUP_GATE=PASS
```

No prefix listing was required for the cleanup proof.

## Final cleanup gates

```text
NVD_2_3G_BOOTSTRAP_TABLE_CLEANUP_GATE=PASS
NVD_2_3G_BOOTSTRAP_PRE_DELETE_VERSION_GATE=PASS
NVD_2_3G_BOOTSTRAP_PRE_DELETE_SIZE_GATE=PASS
NVD_2_3G_BOOTSTRAP_PRE_DELETE_SHA_REFERENCE_GATE=PASS
NVD_2_3G_BOOTSTRAP_PRE_DELETE_AUTHORITY_GATE=PASS
NVD_2_3G_BOOTSTRAP_DELETE_VERSION_GATE=PASS
NVD_2_3G_BOOTSTRAP_EXACT_VERSION_CLEANUP_GATE=PASS
NVD_2_3G_BOOTSTRAP_CURRENT_CLEANUP_GATE=PASS
```

## Proof-phase result

The temporary spike lifecycle is now fully closed:

```text
exact verified Bootstrap Silver evidence
    -> exact-VersionId analytics projection
    -> ordinary Athena Parquet table
    -> bounded queries under unchanged 10 MiB cutoff
    -> exact PyArrow/Athena equivalence
    -> drop temporary table
    -> delete exact temporary projected VersionId
    -> verify exact version absent
    -> verify current key absent
```

The proof establishes the permanent design direction without leaving temporary analytics data or Glue metadata behind.

## Next boundary

Phase 2.3G can now move from proof/spike work to the permanent AWS analytics path.

The permanent path must preserve the authority boundary:

```text
bronze_complete
    !=
silver_complete
    !=
watermark_committed
    -> analytics_eligible
    -> analytics_projected
```

The analytical projector must remain downstream-only and must not mutate or advance the authoritative NVD watermark.
